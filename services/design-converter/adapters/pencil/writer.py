"""
Pencil Writer  —  Universal Node Tree → Pencil.dev
====================================================
Converts a ``UNNode`` tree into a sequence of Pencil MCP tool calls,
executed in a single ``batch_design`` round-trip wherever possible.

Architecture
------------
::

    UNNode tree
        │
        ▼
    _build_ops(node, parent_ref)
        │  recursively emits one op-dict per node
        ▼
    List[op-dict]   ← [{op, args, ref}, ...]
        │
        ▼
    PencilClient.batch_design(ops)
        │  native batch or sequential fallback
        ▼
    root node ID  (str)

Fill strategy
-------------
* The first fill is set via the ``create_*`` tool's ``fill_color`` kwarg
  (solid only) **or** via a follow-up ``set_fill`` op (gradients / images).
* Additional fills are appended with ``add_fill``.
* Strokes are applied via ``set_stroke``.
* Drop shadows and blurs are appended via ``add_shadow`` / ``add_blur``.

Ref system
----------
Each node gets a local ref string (``"ref-0001"``) that is stored in the
``batch_design`` op.  Subsequent child ops reference their parent via
``"$ref-0001"``.  The Pencil client resolves these before dispatch.

Usage
-----
::

    from adapters.pencil import PencilWriter
    from ir import make_frame, make_text, UNSolidFill, UNColor

    frame = make_frame("Card", 390, 200, fill_color="#1A1A2E")
    frame.add_child(make_text("Title", "Hello", font_size=24, color="#FFFFFF"))

    with PencilWriter() as writer:
        node_id = writer.write_node(frame)
        print("Created:", node_id)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Sys-path bootstrap
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CONV_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _CONV_ROOT not in sys.path:
    sys.path.insert(0, _CONV_ROOT)

from adapters.base import BaseWriter, WriteError
from adapters.pencil.client import PencilClient, PencilConnectionError, PencilToolError
from ir.nodes import (
    GradientType,
    ImageFillMode,
    LayoutMode,
    NodeType,
    SizingMode,
    StrokeAlign,
    TextAlign,
    TextTransform,
    UNBlur,
    UNColor,
    UNCornerRadius,
    UNDropShadow,
    UNGradientFill,
    UNGradientStop,
    UNImageFill,
    UNNode,
    UNSolidFill,
    UNStroke,
    UNVariableBinding,
)

log = logging.getLogger(__name__)

# ===========================================================================
# Constants / mappings
# ===========================================================================

# UNNode LayoutMode → Pencil layout string
_LAYOUT_MAP: Dict[LayoutMode, str] = {
    LayoutMode.HORIZONTAL: "flex",
    LayoutMode.VERTICAL: "flex",
    LayoutMode.NONE: "none",
}

# UNNode LayoutMode → Pencil layoutDirection
_DIRECTION_MAP: Dict[LayoutMode, str] = {
    LayoutMode.HORIZONTAL: "horizontal",
    LayoutMode.VERTICAL: "vertical",
    LayoutMode.NONE: "vertical",  # irrelevant when layout=none
}

# TextAlign → Pencil textAlign string
_TEXT_ALIGN_MAP: Dict[TextAlign, str] = {
    TextAlign.LEFT: "left",
    TextAlign.CENTER: "center",
    TextAlign.RIGHT: "right",
    TextAlign.JUSTIFY: "justify",
}

# TextTransform → Pencil textTransform string
_TEXT_TRANSFORM_MAP: Dict[TextTransform, str] = {
    TextTransform.NONE: "none",
    TextTransform.UPPERCASE: "uppercase",
    TextTransform.LOWERCASE: "lowercase",
    TextTransform.CAPITALIZE: "capitalize",
}

# GradientType → Pencil gradientType string
_GRADIENT_TYPE_MAP: Dict[GradientType, str] = {
    GradientType.LINEAR: "linear",
    GradientType.RADIAL: "radial",
    GradientType.ANGULAR: "angular",
    GradientType.DIAMOND: "radial",  # Pencil has no diamond; fall back
}

# ImageFillMode → Pencil imageMode string
_IMAGE_MODE_MAP: Dict[ImageFillMode, str] = {
    ImageFillMode.FILL: "fill",
    ImageFillMode.FIT: "fit",
    ImageFillMode.STRETCH: "stretch",
    ImageFillMode.TILE: "tile",
    ImageFillMode.CROP: "fill",  # closest approximation
}

# StrokeAlign → Pencil strokeAlign string
_STROKE_ALIGN_MAP: Dict[StrokeAlign, str] = {
    StrokeAlign.CENTER: "center",
    StrokeAlign.INSIDE: "inside",
    StrokeAlign.OUTSIDE: "outside",
}

# ===========================================================================
# Ref-name generator
# ===========================================================================

_ref_counter = 0


def _new_ref() -> str:
    global _ref_counter
    _ref_counter += 1
    return f"ref-{_ref_counter:04d}"


def reset_ref_counter() -> None:
    """Reset the ref counter — useful in tests."""
    global _ref_counter
    _ref_counter = 0


# ===========================================================================
# Fill / stroke / effect helpers
# ===========================================================================


def _color_hex(color: UNColor) -> str:
    """Return a 6- or 8-character hex string for a UNColor."""
    return color.to_hex(include_alpha=(color.a < 1.0))


def _gradient_stops(stops: List[UNGradientStop]) -> List[Dict[str, Any]]:
    """Convert UNGradientStop list → Pencil gradientStops list."""
    return [
        {"color": _color_hex(s.color), "position": round(s.position, 4)} for s in stops
    ]


def _primary_fill_color(node: UNNode) -> Optional[str]:
    """
    Return the hex color of the first enabled solid fill, or None.
    Used to pass ``fill_color`` directly to create_* ops so Pencil
    sets the background in the same call (saves a round-trip op).
    """
    for fill in node.fills:
        if isinstance(fill, UNSolidFill) and fill.enabled:
            c = fill.color
            # Apply fill-level opacity
            if fill.opacity < 1.0 and c.a >= 1.0:
                c = UNColor(r=c.r, g=c.g, b=c.b, a=fill.opacity)
            return _color_hex(c)
    return None


def _primary_stroke_color(node: UNNode) -> Tuple[Optional[str], float]:
    """Return (hex_color, width) of the first enabled stroke, or (None, 1)."""
    for stroke in node.strokes:
        if stroke.enabled and isinstance(stroke.fill, UNSolidFill):
            t = stroke.thickness
            width = t.all if t.all is not None else t.max_value()
            return _color_hex(stroke.fill.color), width
    return None, 1.0


def _fill_ops(node_ref: str, node: UNNode) -> List[Dict[str, Any]]:
    """
    Generate ``set_fill`` / ``add_fill`` ops for all fills on a node.

    The *first* solid fill is usually handled by ``fill_color`` in the
    create op, so we only emit fill ops for:
    - Non-solid (gradient / image) first fills
    - Any second or later fill (multi-fill layers)
    """
    ops: List[Dict[str, Any]] = []

    for i, fill in enumerate(node.fills):
        if not fill.enabled:
            continue

        tool = "set_fill" if i == 0 else "add_fill"

        if isinstance(fill, UNSolidFill):
            # The first solid fill is already handled by fill_color kwarg
            # in the create op — skip to avoid duplicating it.
            if i == 0:
                continue
            ops.append(
                {
                    "op": tool,
                    "args": {
                        "nodeId": f"${node_ref}",
                        "fillType": "solid",
                        "color": _color_hex(fill.color),
                        "opacity": round(fill.opacity, 3),
                    },
                }
            )

        elif isinstance(fill, UNGradientFill):
            gtype = _GRADIENT_TYPE_MAP.get(fill.gradient_type, "linear")
            ops.append(
                {
                    "op": tool,
                    "args": {
                        "nodeId": f"${node_ref}",
                        "fillType": f"{gtype}-gradient",
                        "gradientStops": _gradient_stops(fill.stops),
                        "gradientAngle": round(fill.rotation, 2),
                        "gradientType": gtype,
                        "opacity": round(fill.opacity, 3),
                    },
                }
            )

        elif isinstance(fill, UNImageFill):
            if fill.image_url:
                mode = _IMAGE_MODE_MAP.get(fill.image_mode, "fill")
                ops.append(
                    {
                        "op": tool,
                        "args": {
                            "nodeId": f"${node_ref}",
                            "fillType": "image",
                            "imageUrl": fill.image_url,
                            "imageMode": mode,
                            "opacity": round(fill.opacity, 3),
                        },
                    }
                )

    return ops


def _stroke_ops(node_ref: str, node: UNNode) -> List[Dict[str, Any]]:
    """Generate ``set_stroke`` ops for all enabled strokes."""
    ops: List[Dict[str, Any]] = []
    for stroke in node.strokes:
        if not stroke.enabled:
            continue
        if not isinstance(stroke.fill, UNSolidFill):
            continue  # Pencil only supports solid strokes currently
        t = stroke.thickness
        width = t.all if t.all is not None else t.max_value()
        align = _STROKE_ALIGN_MAP.get(stroke.align, "center")
        ops.append(
            {
                "op": "set_stroke",
                "args": {
                    "nodeId": f"${node_ref}",
                    "color": _color_hex(stroke.fill.color),
                    "width": round(width, 2),
                    "align": align,
                    "cap": stroke.cap or "none",
                    "join": stroke.join or "miter",
                    "opacity": round(stroke.opacity, 3),
                },
            }
        )
        break  # Pencil supports one stroke per node
    return ops


def _effect_ops(node_ref: str, node: UNNode) -> List[Dict[str, Any]]:
    """Generate ``add_shadow`` / ``add_blur`` ops for all enabled effects."""
    ops: List[Dict[str, Any]] = []
    for effect in node.effects:
        if not effect.enabled:
            continue
        if isinstance(effect, UNDropShadow):
            ops.append(
                {
                    "op": "add_shadow",
                    "args": {
                        "nodeId": f"${node_ref}",
                        "color": _color_hex(effect.color),
                        "offsetX": round(effect.offset_x, 2),
                        "offsetY": round(effect.offset_y, 2),
                        "blur": round(effect.blur, 2),
                        "spread": round(effect.spread, 2),
                        "inner": effect.inner,
                    },
                }
            )
        elif isinstance(effect, UNBlur):
            ops.append(
                {
                    "op": "add_blur",
                    "args": {
                        "nodeId": f"${node_ref}",
                        "radius": round(effect.radius, 2),
                        "background": effect.background,
                    },
                }
            )
    return ops


# ===========================================================================
# Variable binding helpers
# ===========================================================================

# NOTE: Pencil.dev's MCP batch_design operations do not currently expose a
# first-class API for attaching variable/token references to nodes.  The
# batch_design tool accepts: op, args (tool-specific kwargs), and ref.
# There is no "variableId", "styleId", or "bindVariable" op in the
# documented tool set.  Until Pencil adds such an operation, we cannot
# round-trip design-token bindings through batch_design calls.
#
# What we do instead:
#   1. Log a WARNING for each node that has variable_bindings so the caller
#      knows bindings were dropped rather than silently losing them.
#   2. Return an empty list (no ops emitted) so the literal color value set
#      by the create_* op remains in effect.
#
# When Pencil adds a "bind_variable" or "set_style" op, replace this
# function with one that emits the appropriate op per binding.


def _variable_binding_ops(node_ref: str, node: UNNode) -> List[Dict[str, Any]]:
    """
    Emit ops to attach variable/token bindings to a node.

    Pencil's batch_design API does not currently support variable references
    in design operations.  This function logs a warning for any bindings
    present on the node and returns an empty list.

    When Pencil introduces a native variable-binding op (e.g. "bind_variable"
    or "set_style_id"), implement it here and remove this warning.
    """
    if not node.variable_bindings:
        return []

    for prop, binding in node.variable_bindings.items():
        log.warning(
            "PencilWriter: node '%s' has variable binding '%s' → '%s' "
            "(tool_id=%r) on property '%s', but Pencil's batch_design API "
            "does not support variable references — binding dropped, "
            "literal value retained.",
            node.name,
            binding.variable,
            binding.variable,
            binding.tool_id,
            prop,
        )

    # Future implementation when Pencil supports it:
    # ops = []
    # for prop, binding in node.variable_bindings.items():
    #     ops.append({
    #         "op": "bind_variable",
    #         "args": {
    #             "nodeId": f"${node_ref}",
    #             "property": prop,
    #             "variableId": binding.tool_id or binding.variable,
    #         },
    #     })
    # return ops

    return []


# ===========================================================================
# Dimension helpers
# ===========================================================================


def _resolve_size(size) -> Optional[float]:
    """
    Return a numeric pixel value if the size mode is FIXED, else None.
    Pencil's create_* methods accept explicit width/height when given.
    """
    if size.mode == SizingMode.FIXED:
        return round(size.value, 2)
    return None


# ===========================================================================
# Op builders per node type
# ===========================================================================


def _ops_for_frame(
    node: UNNode,
    parent_ref: str,
    node_ref: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """Emit create_frame / create_artboard + fill/stroke/effect ops."""
    ops: List[Dict[str, Any]] = []

    w = _resolve_size(node.width) or 100.0
    h = _resolve_size(node.height) or 100.0
    fill_color = _primary_fill_color(node)

    # Corner radius
    cr = node.corner_radius
    corner = cr.tl if cr.is_uniform() else 0.0

    # Layout args
    layout = _LAYOUT_MAP.get(node.layout, "none")
    direction = _DIRECTION_MAP.get(node.layout, "vertical")
    pad = node.padding
    padding_list = (
        [pad.top, pad.right, pad.bottom, pad.left] if not pad.is_zero() else None
    )

    # justify-content / align-items
    from ir.nodes import AlignItems, JustifyContent

    _jc_map = {
        JustifyContent.START: "start",
        JustifyContent.CENTER: "center",
        JustifyContent.END: "end",
        JustifyContent.SPACE_BETWEEN: "space-between",
        JustifyContent.SPACE_AROUND: "space-around",
    }
    _ai_map = {
        AlignItems.START: "start",
        AlignItems.CENTER: "center",
        AlignItems.END: "end",
        AlignItems.STRETCH: "stretch",
    }

    args: Dict[str, Any] = {
        "name": node.name,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": w,
        "height": h,
        "cornerRadius": round(corner, 2),
        "clipContent": node.clip_content,
        "opacity": round(node.opacity, 3),
        "visible": node.visible,
    }
    if fill_color:
        args["backgroundColor"] = fill_color
    if parent_ref:
        args["parentId"] = f"${parent_ref}"
    if layout != "none":
        args["layout"] = layout
        args["layoutDirection"] = direction
        args["gap"] = round(node.gap, 2)
        args["alignItems"] = _ai_map.get(node.align_items, "start")
        args["justifyContent"] = _jc_map.get(node.justify_content, "start")
    if padding_list:
        args["padding"] = [round(v, 2) for v in padding_list]

    ops.append({"op": "create_frame", "args": args, "ref": node_ref})
    ops.extend(_fill_ops(node_ref, node))
    ops.extend(_stroke_ops(node_ref, node))
    ops.extend(_effect_ops(node_ref, node))
    ops.extend(_variable_binding_ops(node_ref, node))
    return ops


def _ops_for_text(
    node: UNNode,
    parent_ref: str,
    node_ref: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """Emit create_text op + effect ops."""
    ops: List[Dict[str, Any]] = []

    ts = node.text_style
    fill_color = _primary_fill_color(node) or "#000000"
    w = _resolve_size(node.width)
    h = _resolve_size(node.height)

    args: Dict[str, Any] = {
        "name": node.name,
        "content": node.text_content,
        "x": round(x, 2),
        "y": round(y, 2),
        "fontFamily": ts.font_family,
        "fontSize": round(ts.font_size, 2),
        "fontWeight": ts.font_weight,
        "fontStyle": "italic" if ts.italic else "normal",
        "color": fill_color,
        "textAlign": _TEXT_ALIGN_MAP.get(ts.text_align, "left"),
        "letterSpacing": round(ts.letter_spacing, 3),
        "textTransform": _TEXT_TRANSFORM_MAP.get(ts.text_transform, "none"),
        "opacity": round(node.opacity, 3),
        "visible": node.visible,
    }
    if parent_ref:
        args["parentId"] = f"${parent_ref}"
    if ts.line_height is not None:
        args["lineHeight"] = round(ts.line_height, 3)
    if w is not None:
        args["width"] = w
    if h is not None:
        args["height"] = h

    ops.append({"op": "create_text", "args": args, "ref": node_ref})
    ops.extend(_effect_ops(node_ref, node))
    ops.extend(_variable_binding_ops(node_ref, node))
    return ops


def _ops_for_rectangle(
    node: UNNode,
    parent_ref: str,
    node_ref: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """Emit create_rectangle op + fill/stroke/effect ops."""
    ops: List[Dict[str, Any]] = []

    w = _resolve_size(node.width) or 100.0
    h = _resolve_size(node.height) or 100.0
    fill_color = _primary_fill_color(node)
    stroke_color, stroke_width = _primary_stroke_color(node)
    cr = node.corner_radius
    corner = cr.tl if cr.is_uniform() else 0.0

    args: Dict[str, Any] = {
        "name": node.name,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": w,
        "height": h,
        "cornerRadius": round(corner, 2),
        "opacity": round(node.opacity, 3),
    }
    if parent_ref:
        args["parentId"] = f"${parent_ref}"
    if fill_color:
        args["fillColor"] = fill_color
    if stroke_color:
        args["strokeColor"] = stroke_color
        args["strokeWidth"] = round(stroke_width, 2)

    ops.append({"op": "create_rectangle", "args": args, "ref": node_ref})
    ops.extend(_fill_ops(node_ref, node))
    # Strokes already partially handled above (first stroke only);
    # still emit if first fill was non-solid (no fill_color kwarg)
    if not stroke_color:
        ops.extend(_stroke_ops(node_ref, node))
    ops.extend(_effect_ops(node_ref, node))
    ops.extend(_variable_binding_ops(node_ref, node))
    return ops


def _ops_for_ellipse(
    node: UNNode,
    parent_ref: str,
    node_ref: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """Emit create_ellipse op + fill/stroke/effect ops."""
    ops: List[Dict[str, Any]] = []

    w = _resolve_size(node.width) or 100.0
    h = _resolve_size(node.height) or 100.0
    fill_color = _primary_fill_color(node)
    stroke_color, stroke_width = _primary_stroke_color(node)

    args: Dict[str, Any] = {
        "name": node.name,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": w,
        "height": h,
        "opacity": round(node.opacity, 3),
    }
    if parent_ref:
        args["parentId"] = f"${parent_ref}"
    if fill_color:
        args["fillColor"] = fill_color
    if stroke_color:
        args["strokeColor"] = stroke_color
        args["strokeWidth"] = round(stroke_width, 2)

    ops.append({"op": "create_ellipse", "args": args, "ref": node_ref})
    ops.extend(_fill_ops(node_ref, node))
    if not stroke_color:
        ops.extend(_stroke_ops(node_ref, node))
    ops.extend(_effect_ops(node_ref, node))
    ops.extend(_variable_binding_ops(node_ref, node))
    return ops


def _ops_for_path(
    node: UNNode,
    parent_ref: str,
    node_ref: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """Emit create_path op + fill/stroke/effect ops."""
    ops: List[Dict[str, Any]] = []

    if not node.geometry:
        log.debug("Skipping PATH node '%s' — no geometry.", node.name)
        return ops

    w = _resolve_size(node.width)
    h = _resolve_size(node.height)
    fill_color = _primary_fill_color(node)
    stroke_color, stroke_width = _primary_stroke_color(node)

    args: Dict[str, Any] = {
        "name": node.name,
        "pathData": node.geometry,
        "x": round(x, 2),
        "y": round(y, 2),
        "fillRule": node.fill_rule,
        "opacity": round(node.opacity, 3),
    }
    if parent_ref:
        args["parentId"] = f"${parent_ref}"
    if w is not None:
        args["width"] = w
    if h is not None:
        args["height"] = h
    if fill_color:
        args["fillColor"] = fill_color
    if stroke_color:
        args["strokeColor"] = stroke_color
        args["strokeWidth"] = round(stroke_width, 2)

    ops.append({"op": "create_path", "args": args, "ref": node_ref})
    ops.extend(_fill_ops(node_ref, node))
    if not stroke_color:
        ops.extend(_stroke_ops(node_ref, node))
    ops.extend(_effect_ops(node_ref, node))
    ops.extend(_variable_binding_ops(node_ref, node))
    return ops


def _ops_for_image(
    node: UNNode,
    parent_ref: str,
    node_ref: str,
    x: float,
    y: float,
) -> List[Dict[str, Any]]:
    """Emit create_frame with an image fill op."""
    ops: List[Dict[str, Any]] = []

    w = _resolve_size(node.width) or 100.0
    h = _resolve_size(node.height) or 100.0
    mode = _IMAGE_MODE_MAP.get(node.image_mode, "fill")

    args: Dict[str, Any] = {
        "name": node.name,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": w,
        "height": h,
        "opacity": round(node.opacity, 3),
    }
    if parent_ref:
        args["parentId"] = f"${parent_ref}"

    ops.append({"op": "create_frame", "args": args, "ref": node_ref})

    # Set the image fill
    if node.image_url:
        ops.append(
            {
                "op": "set_fill",
                "args": {
                    "nodeId": f"${node_ref}",
                    "fillType": "image",
                    "imageUrl": node.image_url,
                    "imageMode": mode,
                },
            }
        )

    ops.extend(_stroke_ops(node_ref, node))
    ops.extend(_effect_ops(node_ref, node))
    ops.extend(_variable_binding_ops(node_ref, node))
    return ops


# ===========================================================================
# Recursive op builder
# ===========================================================================


def _build_ops(
    node: UNNode,
    parent_ref: str = "",
    parent_x: float = 0.0,
    parent_y: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Recursively build the full list of ``batch_design`` operations for
    ``node`` and all its descendants.

    Parameters
    ----------
    node       : UNNode to convert.
    parent_ref : Local ref of the parent node (empty = top-level).
    parent_x   : Accumulated x offset from ancestor absolute positions.
    parent_y   : Accumulated y offset from ancestor absolute positions.

    Returns
    -------
    List of op-dicts ready for ``PencilClient.batch_design``.
    """
    if not node.visible:
        return []

    ops: List[Dict[str, Any]] = []
    node_ref = _new_ref()

    # Compute effective position
    # When the node lives in an auto-layout parent its x/y are controlled
    # by the layout engine; we still pass them in case the parent is NONE.
    x = round(node.x, 2)
    y = round(node.y, 2)

    ntype = node.type

    if ntype in (NodeType.FRAME, NodeType.GROUP, NodeType.COMPONENT, NodeType.INSTANCE):
        ops.extend(_ops_for_frame(node, parent_ref, node_ref, x, y))

    elif ntype == NodeType.TEXT:
        ops.extend(_ops_for_text(node, parent_ref, node_ref, x, y))

    elif ntype == NodeType.RECTANGLE:
        ops.extend(_ops_for_rectangle(node, parent_ref, node_ref, x, y))

    elif ntype == NodeType.ELLIPSE:
        ops.extend(_ops_for_ellipse(node, parent_ref, node_ref, x, y))

    elif ntype == NodeType.PATH:
        ops.extend(_ops_for_path(node, parent_ref, node_ref, x, y))

    elif ntype == NodeType.IMAGE:
        ops.extend(_ops_for_image(node, parent_ref, node_ref, x, y))

    else:
        # Unknown type — fall back to frame
        log.debug("Unknown NodeType %s — treating as FRAME.", ntype)
        ops.extend(_ops_for_frame(node, parent_ref, node_ref, x, y))

    # Apply non-uniform corner radius as a follow-up op
    cr = node.corner_radius
    if not cr.is_uniform() and ntype not in (NodeType.TEXT,):
        ops.append(
            {
                "op": "set_corner_radius",
                "args": {
                    "nodeId": f"${node_ref}",
                    "topLeft": round(cr.tl, 2),
                    "topRight": round(cr.tr, 2),
                    "bottomRight": round(cr.br, 2),
                    "bottomLeft": round(cr.bl, 2),
                },
            }
        )

    # Recurse into children (only for container types)
    if ntype in (NodeType.FRAME, NodeType.GROUP, NodeType.COMPONENT, NodeType.INSTANCE):
        for child in node.children:
            ops.extend(_build_ops(child, parent_ref=node_ref))

    return ops


# ===========================================================================
# PencilWriter
# ===========================================================================


class PencilWriter(BaseWriter):
    """
    Write a UNNode tree to Pencil.dev via its local MCP server.

    Parameters
    ----------
    host        : Pencil MCP server host (default ``'127.0.0.1'``).
    port        : Pencil MCP server port.  Pass ``None`` to auto-detect.
    auto_detect : Whether to scan for the Pencil port when port=None.
    client      : Pre-constructed ``PencilClient`` (overrides host/port).

    Example
    -------
    ::

        with PencilWriter() as writer:
            node_id = writer.write_node(tree)

        # Explicit port
        writer = PencilWriter(port=19002)
        writer.connect()
        node_id = writer.write_node(tree, parent_id="artboard-abc")
        writer.disconnect()
    """

    tool_name = "pencil"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        auto_detect: bool = True,
        client: Optional[PencilClient] = None,
    ) -> None:
        self._client = client or PencilClient(
            host=host, port=port, auto_detect=auto_detect
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open connection to the Pencil MCP server."""
        self._client.connect()

    def disconnect(self) -> None:
        """Close connection to the Pencil MCP server."""
        self._client.disconnect()

    # ── BaseWriter interface ───────────────────────────────────────────────

    def write_node(
        self,
        node: UNNode,
        parent_id: str = "",
        replace_id: str = "",
    ) -> str:
        """
        Write ``node`` (and its full subtree) to Pencil.

        Parameters
        ----------
        node       : UNNode tree to create.
        parent_id  : Pencil node ID to insert into.
                     Empty string → create a new top-level artboard.
        replace_id : If set, delete this existing node before writing.
                     Useful for replacing a previously written subtree.

        Returns
        -------
        str  — Pencil node ID of the newly created root node.

        Raises
        ------
        WriteError  if Pencil rejects the operations.
        """
        from adapters.pencil.ops import build_batch_script, build_batch_script_with_parent

        if not self._client._connected:
            self._client.connect()

        # Optional: delete the node we are replacing
        if replace_id:
            try:
                self._client.delete_node(replace_id)
                log.debug("PencilWriter: deleted replace target '%s'.", replace_id)
            except PencilToolError as exc:
                log.warning("PencilWriter: could not delete '%s': %s", replace_id, exc)

        # Top-level node without a parent → create an artboard first
        if not parent_id and node.type in (
            NodeType.FRAME,
            NodeType.GROUP,
            NodeType.COMPONENT,
        ):
            root_id = self._write_as_artboard(node)
            return root_id

        # Build the batch_design script with parent
        if parent_id:
            script = build_batch_script_with_parent(node, parent_id)
        else:
            script = build_batch_script(node)

        # Execute the script
        return self._dispatch_script(script)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _write_as_artboard(self, node: UNNode) -> str:
        """
        Create a top-level Pencil artboard for the given FRAME node,
        then populate it with all children via batch_design.

        Returns the artboard's Pencil node ID.
        """
        from adapters.pencil.ops import build_artboard_script

        # Build the batch_design script
        script, binding = build_artboard_script(node)

        log.debug("PencilWriter: running batch_design script for '%s' (%d chars)",
                  node.name, len(script))

        # Execute the script
        try:
            results = self._client.run_batch_script(script)
            log.debug("PencilWriter: batch_design results: %s", results)
        except (PencilToolError, PencilConnectionError) as exc:
            raise WriteError("pencil", str(exc)) from exc

        # Extract the artboard ID from results
        if results and isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    node_id = result.get("id") or result.get("nodeId")
                    if node_id:
                        log.debug("PencilWriter: created artboard '%s' → id=%s",
                                  node.name, node_id)
                        return node_id

        raise WriteError("pencil", "batch_design returned no node ID")

    def _dispatch_script(self, script: str) -> str:
        """
        Send a batch_design script string to Pencil and return the first node ID.

        Parameters
        ----------
        script : batch_design script in I/C/R/U/D/M/G syntax
        """
        if not script:
            return ""

        try:
            results = self._client.run_batch_script(script)
        except (PencilToolError, PencilConnectionError) as exc:
            raise WriteError("pencil", str(exc)) from exc

        # Extract the ID from the first result that has one
        if results and isinstance(results, list):
            for result in results:
                if isinstance(result, dict):
                    node_id = result.get("id") or ""
                    if node_id:
                        return node_id

        return ""

    def _dispatch(
        self,
        ops: List[Dict[str, Any]],
        pre_resolved: bool = False,
    ) -> str:
        """
        Send ``ops`` to Pencil via ``batch_design`` and return the ID of
        the first created node.

        Parameters
        ----------
        ops          : List of op-dicts.
        pre_resolved : If True, skip the $ref resolution pass inside the
                       client (used when we have already resolved refs).
        """
        if not ops:
            return ""

        try:
            results = self._client.batch_design(ops)
        except (PencilToolError, PencilConnectionError) as exc:
            raise WriteError("pencil", str(exc)) from exc

        # Extract the ID from the first result that has one
        for result in results:
            node_id = result.get("id") or ""
            if node_id:
                return node_id

        return ""

    # ── Optional BaseWriter overrides ──────────────────────────────────────

    def delete_node(self, node_id: str) -> None:
        """Delete a node by its Pencil ID."""
        try:
            self._client.delete_node(node_id)
        except PencilToolError as exc:
            log.warning("PencilWriter.delete_node('%s') failed: %s", node_id, exc)

    def move_node(self, node_id: str, new_parent_id: str, index: int = -1) -> None:
        """Move a node to a different parent."""
        try:
            self._client.move_node(node_id, new_parent_id, index=index)
        except PencilToolError as exc:
            log.warning("PencilWriter.move_node failed: %s", exc)

    def screenshot(self, node_id: str, scale: float = 1.0) -> Optional[bytes]:
        """Export a PNG screenshot of the written node."""
        return self._client.export_node(node_id, format="png", scale=scale)

    def __repr__(self) -> str:
        return f"<PencilWriter client={self._client!r}>"
