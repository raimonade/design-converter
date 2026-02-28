"""
Paper Writer  —  Universal Node Tree → Paper Design
===================================================
Converts a ``UNNode`` tree into an HTML string with inline styles,
then writes it to Paper Design via ``PaperClient.write_html()``.

Pipeline
--------
1. ``PaperWriter.write_node(node, parent_id, replace_id)``
2. ``_HtmlEmitter.emit(node)``  →  HTML string with inline styles
3. ``PaperClient.write_html(target_node_id, html, mode="replace")``
4. Return the Paper node ID that was created / replaced

Supported UNNode types
----------------------
  FRAME      → <div> with flexbox layout, fills, border-radius, shadows
  TEXT       → <span> with font, color, text-shadow
  RECTANGLE  → <div> with background, border-radius
  ELLIPSE    → <div> with border-radius: 50%
  PATH       → <svg><path d="..." /></svg>
  IMAGE      → <img src="..." /> or <div style="background-image:...">
  GROUP      → <div> (no background)

Usage
-----
    from adapters.paper import PaperWriter
    from ir.nodes import UNNode

    with PaperWriter() as writer:
        # Write to an existing artboard
        new_id = writer.write_node(tree, parent_id="TO-0")

        # Replace an existing node
        new_id = writer.write_node(tree, replace_id="old-node-id")
"""

from __future__ import annotations

import logging
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Sys-path bootstrap (allow running from repo root directly)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CONV_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _CONV_ROOT not in sys.path:
    sys.path.insert(0, _CONV_ROOT)

from adapters.base import BaseWriter, WriteError
from adapters.paper.client import PaperClient, PaperConnectionError, PaperToolError
from ir.nodes import (
    AlignItems,
    BlendMode,
    GradientType,
    ImageFillMode,
    JustifyContent,
    LayoutMode,
    NodeType,
    SizingMode,
    TextAlign,
    TextAutoResize,
    TextTransform,
    UNBlur,
    UNColor,
    UNCornerRadius,
    UNDropShadow,
    UNGradientFill,
    UNGradientStop,
    UNImageFill,
    UNNode,
    UNPadding,
    UNSize,
    UNSolidFill,
    UNStroke,
    UNTextStyle,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers: value formatting
# ---------------------------------------------------------------------------


def _px(v: float) -> str:
    """Format a pixel value: integers emit without decimal, floats with 2dp."""
    if v == int(v):
        return f"{int(v)}px"
    return f"{v:.2f}px"


def _pct(v: float) -> str:
    """Format a 0–1 float as a CSS percentage string."""
    pct = v * 100.0
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct:.3f}%"


def _round2(v: float) -> float:
    return round(v, 2)


def _css_color(color: UNColor) -> str:
    """
    Convert a UNColor to a CSS color string.
    Uses rgba() when alpha < 1, otherwise #rrggbb hex.
    """
    r = max(0, min(255, round(color.r * 255)))
    g = max(0, min(255, round(color.g * 255)))
    b = max(0, min(255, round(color.b * 255)))
    a = max(0.0, min(1.0, color.a))
    if a >= 1.0:
        return f"#{r:02x}{g:02x}{b:02x}"
    return f"rgba({r},{g},{b},{_round2(a)})"


def _blend_mode_css(mode: BlendMode) -> str:
    """Map BlendMode enum to CSS mix-blend-mode value."""
    _MAP = {
        BlendMode.NORMAL: "normal",
        BlendMode.MULTIPLY: "multiply",
        BlendMode.SCREEN: "screen",
        BlendMode.OVERLAY: "overlay",
        BlendMode.DARKEN: "darken",
        BlendMode.LIGHTEN: "lighten",
        BlendMode.DODGE: "color-dodge",
        BlendMode.BURN: "color-burn",
        BlendMode.HARD_LIGHT: "hard-light",
        BlendMode.SOFT_LIGHT: "soft-light",
        BlendMode.DIFFERENCE: "difference",
        BlendMode.EXCLUSION: "exclusion",
        BlendMode.HUE: "hue",
        BlendMode.SATURATION: "saturation",
        BlendMode.COLOR: "color",
        BlendMode.LUMINOSITY: "luminosity",
    }
    return _MAP.get(mode, "normal")


# ---------------------------------------------------------------------------
# Fill → CSS  (background / fill property)
# ---------------------------------------------------------------------------


def _gradient_css(fill: UNGradientFill) -> str:
    """
    Convert a UNGradientFill to a CSS gradient function string.

    Examples
    --------
    ``linear-gradient(180deg, #7c3aed 0%, #050508 100%)``
    ``radial-gradient(circle at 50% 50%, #7c3aed 0%, transparent 100%)``
    """
    stops = sorted(fill.stops, key=lambda s: s.position)
    stop_strs: List[str] = []
    for stop in stops:
        color_str = _css_color(stop.color)
        pos_str = _pct(stop.position)
        stop_strs.append(f"{color_str} {pos_str}")

    stops_css = ", ".join(stop_strs)

    if fill.gradient_type == GradientType.LINEAR:
        # CSS gradient angle: 0deg = top→bottom in CSS, but Figma/Paper use
        # rotation where 0 = top→bottom too. Direct mapping works.
        angle = fill.rotation
        return f"linear-gradient({angle:.0f}deg, {stops_css})"

    if fill.gradient_type == GradientType.RADIAL:
        cx = int(fill.center_x * 100) if hasattr(fill, "center_x") else 50
        cy = int(fill.center_y * 100) if hasattr(fill, "center_y") else 50
        return f"radial-gradient(circle at {cx}% {cy}%, {stops_css})"

    # Angular → approximated as conic
    return f"conic-gradient(from {fill.rotation:.0f}deg, {stops_css})"


def _fills_to_css_background(node: UNNode) -> Optional[str]:
    """
    Build a CSS background value from node.fills.

    Multiple fills are layered using comma-separated background values
    (last fill in the list = bottom layer in CSS — we reverse to match
    Figma's top-to-bottom ordering where fills[0] is the topmost).
    """
    if not node.fills:
        return None

    # Filter enabled fills
    enabled = [f for f in node.fills if getattr(f, "enabled", True)]
    if not enabled:
        return None

    parts: List[str] = []
    for fill in reversed(enabled):  # CSS layers: first = topmost
        if isinstance(fill, UNSolidFill):
            parts.append(_css_color(fill.color))
        elif isinstance(fill, UNGradientFill):
            grad = _gradient_css(fill)
            if fill.opacity < 1.0:
                # Wrap in a semi-transparent overlay using a gradient trick
                # is not straightforward; just apply opacity on the element level
                pass
            parts.append(grad)
        elif isinstance(fill, UNImageFill):
            url = fill.url
            mode_map = {
                ImageFillMode.FILL: "cover",
                ImageFillMode.FIT: "contain",
                ImageFillMode.STRETCH: "100% 100%",
                ImageFillMode.TILE: "auto",
            }
            size = mode_map.get(fill.mode, "cover")
            parts.append(f"url('{url}')")
            # We'll need background-size separate; just store fill type info
            # For simplicity, add as a separate layer note in the outer code

    if not parts:
        return None
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Effects → CSS  (box-shadow, filter, backdrop-filter)
# ---------------------------------------------------------------------------


def _shadow_css(shadow: UNDropShadow) -> str:
    """Convert a UNDropShadow to a CSS box-shadow string."""
    color = _css_color(shadow.color)
    ox = _px(shadow.offset_x)
    oy = _px(shadow.offset_y)
    blur = _px(shadow.blur)
    spread = _px(shadow.spread) if shadow.spread else "0px"
    inset = "inset " if shadow.inner else ""
    return f"{inset}{ox} {oy} {blur} {spread} {color}"


def _effects_to_css(node: UNNode) -> Dict[str, str]:
    """
    Build CSS property dict for node.effects.

    Returns dict with keys from: box-shadow, filter, backdrop-filter
    """
    result: Dict[str, str] = {}
    shadows: List[str] = []
    blurs: List[str] = []
    bg_blurs: List[str] = []

    for eff in node.effects:
        if not getattr(eff, "enabled", True):
            continue
        if isinstance(eff, UNDropShadow):
            shadows.append(_shadow_css(eff))
        elif isinstance(eff, UNBlur):
            if eff.background:
                bg_blurs.append(f"blur({_px(eff.radius)})")
            else:
                blurs.append(f"blur({_px(eff.radius)})")

    if shadows:
        result["box-shadow"] = ", ".join(shadows)
    if blurs:
        result["filter"] = " ".join(blurs)
    if bg_blurs:
        result["backdrop-filter"] = " ".join(bg_blurs)
    return result


# ---------------------------------------------------------------------------
# Stroke → CSS border / outline
# ---------------------------------------------------------------------------


def _stroke_to_css(stroke: UNStroke) -> Dict[str, str]:
    """Convert a UNStroke to CSS border properties."""
    if not getattr(stroke, "enabled", True):
        return {}

    thickness = stroke.thickness.to_pencil() if stroke.thickness else 1.0
    fill = stroke.fill
    if isinstance(fill, UNSolidFill):
        color = _css_color(fill.color)
    else:
        color = "#000000"

    style = "solid"
    if stroke.dash_pattern:
        style = "dashed"

    return {"border": f"{_px(thickness)} {style} {color}"}


# ---------------------------------------------------------------------------
# Corner radius → CSS border-radius
# ---------------------------------------------------------------------------


def _corner_radius_css(cr: UNCornerRadius) -> Optional[str]:
    """Build a CSS border-radius value from a UNCornerRadius."""
    if cr.is_uniform():
        v = cr.value()
        if v == 0:
            return None
        # Paper uses "9999px" style for pills/circles
        return _px(v)

    # Per-corner (top-left top-right bottom-right bottom-left)
    tl = _px(cr.tl)
    tr = _px(cr.tr)
    br = _px(cr.br)
    bl = _px(cr.bl)
    if tl == tr == br == bl:
        return tl
    return f"{tl} {tr} {br} {bl}"


# ---------------------------------------------------------------------------
# Size → CSS width / height
# ---------------------------------------------------------------------------


def _size_css(size: UNSize, prop: str) -> Optional[str]:
    """
    Convert a UNSize to a CSS width or height value.

    SizingMode.FIXED  → "390px"
    SizingMode.HUG    → "fit-content"   (auto for height)
    SizingMode.FILL   → "100%"
    """
    if size.mode == SizingMode.FIXED:
        return _px(size.value)
    if size.mode == SizingMode.HUG:
        return "fit-content"
    if size.mode == SizingMode.FILL:
        return "100%"
    return None


# ---------------------------------------------------------------------------
# Layout → CSS flexbox
# ---------------------------------------------------------------------------


def _layout_css(node: UNNode) -> Dict[str, str]:
    """Build CSS flexbox properties from a UNNode's layout settings."""
    if node.layout == LayoutMode.NONE:
        return {}

    result: Dict[str, str] = {"display": "flex"}

    result["flex-direction"] = (
        "row" if node.layout == LayoutMode.HORIZONTAL else "column"
    )

    # Gap
    if node.gap:
        result["gap"] = _px(node.gap)

    # justify-content
    jc_map = {
        JustifyContent.START: "flex-start",
        JustifyContent.CENTER: "center",
        JustifyContent.END: "flex-end",
        JustifyContent.SPACE_BETWEEN: "space-between",
        JustifyContent.SPACE_AROUND: "space-around",
    }
    jc = jc_map.get(node.justify_content, "flex-start")
    if jc != "flex-start":
        result["justify-content"] = jc

    # align-items
    ai_map = {
        AlignItems.START: "flex-start",
        AlignItems.CENTER: "center",
        AlignItems.END: "flex-end",
        AlignItems.STRETCH: "stretch",
    }
    ai = ai_map.get(node.align_items, "flex-start")
    if ai != "flex-start":
        result["align-items"] = ai

    # flex-wrap
    if node.layout_wrap:
        result["flex-wrap"] = "wrap"

    # Padding
    p = node.padding
    if not p.is_zero():
        if p.top == p.right == p.bottom == p.left:
            result["padding"] = _px(p.top)
        else:
            result["padding"] = (
                f"{_px(p.top)} {_px(p.right)} {_px(p.bottom)} {_px(p.left)}"
            )

    return result


# ---------------------------------------------------------------------------
# Typography → CSS
# ---------------------------------------------------------------------------


def _text_style_css(ts: UNTextStyle) -> Dict[str, str]:
    """Build CSS typography properties from a UNTextStyle."""
    result: Dict[str, str] = {}

    if ts.font_family:
        result["font-family"] = f"'{ts.font_family}', sans-serif"
    if ts.font_size:
        result["font-size"] = _px(ts.font_size)
    if ts.font_weight and ts.font_weight != "400":
        result["font-weight"] = str(ts.font_weight)
    if ts.font_style and ts.font_style != "normal":
        result["font-style"] = ts.font_style
    if ts.line_height is not None:
        result["line-height"] = _px(ts.line_height)
    if ts.letter_spacing and ts.letter_spacing != 0.0:
        result["letter-spacing"] = _px(ts.letter_spacing)

    ta_map = {
        TextAlign.LEFT: "left",
        TextAlign.CENTER: "center",
        TextAlign.RIGHT: "right",
        TextAlign.JUSTIFY: "justify",
    }
    ta = ta_map.get(ts.text_align, "left")
    if ta != "left":
        result["text-align"] = ta

    tt_map = {
        TextTransform.UPPERCASE: "uppercase",
        TextTransform.LOWERCASE: "lowercase",
        TextTransform.CAPITALIZE: "capitalize",
        TextTransform.NONE: "none",
    }
    tt = tt_map.get(ts.text_transform, "none")
    if tt != "none":
        result["text-transform"] = tt

    if ts.text_decoration and ts.text_decoration not in ("none", ""):
        result["text-decoration"] = ts.text_decoration

    return result


# ---------------------------------------------------------------------------
# CSS dict → inline style string
# ---------------------------------------------------------------------------


def _style_str(props: Dict[str, str]) -> str:
    """Serialize a dict of CSS properties to an inline style string."""
    parts = [f"{k}: {v}" for k, v in props.items() if v is not None]
    return "; ".join(parts)


# ===========================================================================
# HTML emitter
# ===========================================================================


class _HtmlEmitter:
    """
    Recursively emit a UNNode tree as an HTML string with inline styles.

    The output is designed to be accepted by Paper Design's ``write_html``
    tool:
      - Uses only inline styles (no class names)
      - All dimensions in px
      - Position: absolute for NONE layout, relative/flex for auto-layout
      - Text rendered as <span> or <p> elements
      - SVG paths rendered as <svg><path .../></svg>
      - Image fills rendered as background-image on <div>
    """

    def __init__(self, indent_size: int = 2) -> None:
        self._indent = indent_size
        self._parts: List[str] = []

    # ── Public entry-point ─────────────────────────────────────────────────

    def emit(self, node: UNNode) -> str:
        """
        Convert a UNNode tree to an HTML string.
        Returns the complete HTML markup ready for write_html.
        """
        self._parts = []
        self._emit_node(node, depth=0)
        return "".join(self._parts)

    # ── Internal emitters ─────────────────────────────────────────────────

    def _emit_node(self, node: UNNode, depth: int) -> None:
        """Dispatch to the correct emitter based on node type."""
        if not node.visible:
            return  # Skip hidden nodes

        if node.type == NodeType.TEXT:
            self._emit_text(node, depth)
        elif node.type == NodeType.PATH:
            self._emit_path(node, depth)
        elif node.type == NodeType.ELLIPSE:
            self._emit_ellipse(node, depth)
        elif node.type in (NodeType.RECTANGLE,):
            self._emit_rect(node, depth)
        elif node.type == NodeType.IMAGE:
            self._emit_image(node, depth)
        else:
            # FRAME, GROUP, COMPONENT, INSTANCE → <div>
            self._emit_frame(node, depth)

    def _indent_str(self, depth: int) -> str:
        return " " * (self._indent * depth)

    def _write(self, text: str) -> None:
        self._parts.append(text)

    # ── Frame / container ─────────────────────────────────────────────────

    def _emit_frame(self, node: UNNode, depth: int) -> None:
        indent = self._indent_str(depth)
        css = self._frame_css(node)
        style = _style_str(css)

        tag = "div"
        attrs = f' style="{style}"'
        if node.id:
            attrs += f' data-id="{_esc_attr(node.id)}"'
        if node.name and node.name not in ("div", "frame", "group"):
            attrs += f' data-name="{_esc_attr(node.name)}"'

        if not node.children:
            self._write(f"{indent}<{tag}{attrs}></{tag}>\n")
            return

        self._write(f"{indent}<{tag}{attrs}>\n")
        for child in node.children:
            self._emit_node(child, depth + 1)
        self._write(f"{indent}</{tag}>\n")

    def _frame_css(self, node: UNNode) -> Dict[str, str]:
        """Build CSS dict for a frame/container node."""
        css: Dict[str, str] = {}

        # Sizing
        w = _size_css(node.width, "width")
        h = _size_css(node.height, "height")
        if w:
            css["width"] = w
        if h:
            css["height"] = h

        # Position
        if node.layout == LayoutMode.NONE:
            # Absolute positioning within a fixed parent
            css["position"] = "relative"
        else:
            css["position"] = "relative"

        # Explicit position for absolute children
        if node.x or node.y:
            # Only emit left/top when they are meaningful
            # (parent uses absolute layout or we're the root)
            pass  # Let the parent handle child positioning

        # Background fills
        self._apply_fills_to_css(node, css)

        # Border
        for stroke in node.strokes:
            if getattr(stroke, "enabled", True):
                css.update(_stroke_to_css(stroke))
                break  # Paper only supports one border

        # Corner radius
        cr_css = _corner_radius_css(node.corner_radius)
        if cr_css:
            css["border-radius"] = cr_css

        # Clip content
        if node.clip_content:
            css["overflow"] = "hidden"

        # Opacity
        if node.opacity < 1.0:
            css["opacity"] = str(_round2(node.opacity))

        # Blend mode
        if node.blend_mode != BlendMode.NORMAL:
            css["mix-blend-mode"] = _blend_mode_css(node.blend_mode)

        # Layout (flex)
        css.update(_layout_css(node))

        # Effects
        css.update(_effects_to_css(node))

        # Rotation
        if node.rotation:
            css["transform"] = f"rotate({-node.rotation:.2f}deg)"

        return css

    # ── Text ──────────────────────────────────────────────────────────────

    def _emit_text(self, node: UNNode, depth: int) -> None:
        indent = self._indent_str(depth)
        css = self._text_css(node)
        style = _style_str(css)

        content = _esc_html(node.text_content)
        tag = "span"

        attrs = f' style="{style}"'
        if node.id:
            attrs += f' data-id="{_esc_attr(node.id)}"'
        if node.name and node.name not in ("span", "text"):
            attrs += f' data-name="{_esc_attr(node.name)}"'

        self._write(f"{indent}<{tag}{attrs}>{content}</{tag}>\n")

    def _text_css(self, node: UNNode) -> Dict[str, str]:
        """Build CSS dict for a text node."""
        css: Dict[str, str] = {}
        ts = node.text_style

        # Font properties
        css.update(_text_style_css(ts))

        # Text color from fills
        for fill in node.fills:
            if isinstance(fill, UNSolidFill) and getattr(fill, "enabled", True):
                css["color"] = _css_color(fill.color)
                break
            elif isinstance(fill, UNGradientFill) and getattr(fill, "enabled", True):
                css["background"] = _gradient_css(fill)
                css["-webkit-background-clip"] = "text"
                css["-webkit-text-fill-color"] = "transparent"
                break

        # Sizing
        w = _size_css(node.width, "width")
        h = _size_css(node.height, "height")
        if w and w != "fit-content":
            css["width"] = w
        if h and h != "fit-content":
            css["height"] = h

        # Opacity
        if node.opacity < 1.0:
            css["opacity"] = str(_round2(node.opacity))

        # Effects (text-shadow)
        eff_css = _effects_to_css(node)
        if "box-shadow" in eff_css:
            css["text-shadow"] = eff_css["box-shadow"]

        # Blend mode
        if node.blend_mode != BlendMode.NORMAL:
            css["mix-blend-mode"] = _blend_mode_css(node.blend_mode)

        return css

    # ── Rectangle ─────────────────────────────────────────────────────────

    def _emit_rect(self, node: UNNode, depth: int) -> None:
        indent = self._indent_str(depth)
        css: Dict[str, str] = {}

        w = _size_css(node.width, "width")
        h = _size_css(node.height, "height")
        if w:
            css["width"] = w
        if h:
            css["height"] = h

        self._apply_fills_to_css(node, css)

        cr = _corner_radius_css(node.corner_radius)
        if cr:
            css["border-radius"] = cr

        for stroke in node.strokes:
            if getattr(stroke, "enabled", True):
                css.update(_stroke_to_css(stroke))
                break

        if node.opacity < 1.0:
            css["opacity"] = str(_round2(node.opacity))

        css.update(_effects_to_css(node))

        if node.blend_mode != BlendMode.NORMAL:
            css["mix-blend-mode"] = _blend_mode_css(node.blend_mode)

        style = _style_str(css)
        attrs = f' style="{style}"'
        if node.id:
            attrs += f' data-id="{_esc_attr(node.id)}"'
        if node.name and node.name not in ("rect", "rectangle"):
            attrs += f' data-name="{_esc_attr(node.name)}"'

        # Children (rare for rects, but allowed)
        if node.children:
            self._write(f"{self._indent_str(depth)}<div{attrs}>\n")
            for child in node.children:
                self._emit_node(child, depth + 1)
            self._write(f"{self._indent_str(depth)}</div>\n")
        else:
            self._write(f"{self._indent_str(depth)}<div{attrs}></div>\n")

    # ── Ellipse ───────────────────────────────────────────────────────────

    def _emit_ellipse(self, node: UNNode, depth: int) -> None:
        indent = self._indent_str(depth)
        css: Dict[str, str] = {}

        w = _size_css(node.width, "width")
        h = _size_css(node.height, "height")
        if w:
            css["width"] = w
        if h:
            css["height"] = h

        css["border-radius"] = "50%"

        self._apply_fills_to_css(node, css)

        for stroke in node.strokes:
            if getattr(stroke, "enabled", True):
                css.update(_stroke_to_css(stroke))
                break

        if node.opacity < 1.0:
            css["opacity"] = str(_round2(node.opacity))

        css.update(_effects_to_css(node))

        if node.blend_mode != BlendMode.NORMAL:
            css["mix-blend-mode"] = _blend_mode_css(node.blend_mode)

        style = _style_str(css)
        attrs = f' style="{style}"'
        if node.id:
            attrs += f' data-id="{_esc_attr(node.id)}"'
        if node.name and node.name not in ("ellipse", "circle"):
            attrs += f' data-name="{_esc_attr(node.name)}"'

        self._write(f"{indent}<div{attrs}></div>\n")

    # ── Path / Vector (SVG) ───────────────────────────────────────────────

    def _emit_path(self, node: UNNode, depth: int) -> None:
        indent = self._indent_str(depth)

        w = node.width.value if node.width.mode == SizingMode.FIXED else 24.0
        h = node.height.value if node.height.mode == SizingMode.FIXED else 24.0

        # SVG container styles
        svg_css: Dict[str, str] = {
            "width": _px(w),
            "height": _px(h),
            "overflow": "visible",
        }
        if node.opacity < 1.0:
            svg_css["opacity"] = str(_round2(node.opacity))
        if node.blend_mode != BlendMode.NORMAL:
            svg_css["mix-blend-mode"] = _blend_mode_css(node.blend_mode)
        svg_style = _style_str(svg_css)

        # Path fill
        fill_color = "none"
        for fill in node.fills:
            if isinstance(fill, UNSolidFill) and getattr(fill, "enabled", True):
                fill_color = _css_color(fill.color)
                break
            elif isinstance(fill, UNGradientFill) and getattr(fill, "enabled", True):
                fill_color = "url(#grad0)"
                break

        # Path stroke
        stroke_attrs = ""
        for stroke in node.strokes:
            if getattr(stroke, "enabled", True):
                thickness = stroke.thickness.to_pencil() if stroke.thickness else 1.0
                if isinstance(stroke.fill, UNSolidFill):
                    sc = _css_color(stroke.fill.color)
                else:
                    sc = "currentColor"
                cap = getattr(stroke, "cap", "round")
                join = getattr(stroke, "join", "round")
                stroke_attrs = (
                    f' stroke="{sc}" stroke-width="{thickness:.1f}"'
                    f' stroke-linecap="{cap}" stroke-linejoin="{join}"'
                )
                break

        geometry = node.geometry or ""
        fill_rule = node.fill_rule or "nonzero"

        svg_data_attrs = ""
        if node.id:
            svg_data_attrs += f' data-id="{_esc_attr(node.id)}"'
        if node.name and node.name not in ("path", "svg"):
            svg_data_attrs += f' data-name="{_esc_attr(node.name)}"'

        self._write(
            f'{indent}<svg{svg_data_attrs} style="{svg_style}" '
            f'viewBox="0 0 {w:.0f} {h:.0f}" '
            f'xmlns="http://www.w3.org/2000/svg">\n'
        )
        self._write(
            f'{indent}  <path d="{_esc_attr(geometry)}" '
            f'fill="{fill_color}" fill-rule="{fill_rule}"'
            f"{stroke_attrs}/>\n"
        )
        self._write(f"{indent}</svg>\n")

    # ── Image ─────────────────────────────────────────────────────────────

    def _emit_image(self, node: UNNode, depth: int) -> None:
        indent = self._indent_str(depth)
        css: Dict[str, str] = {}

        w = _size_css(node.width, "width")
        h = _size_css(node.height, "height")
        if w:
            css["width"] = w
        if h:
            css["height"] = h

        if node.opacity < 1.0:
            css["opacity"] = str(_round2(node.opacity))

        cr = _corner_radius_css(node.corner_radius)
        if cr:
            css["border-radius"] = cr

        style = _style_str(css)
        src = node.image_url or ""
        attrs = f' src="{_esc_attr(src)}" style="{style}"'
        if node.id:
            attrs += f' data-id="{_esc_attr(node.id)}"'
        if node.name and node.name not in ("img", "image"):
            attrs += f' alt="{_esc_attr(node.name)}"'

        self._write(f"{indent}<img{attrs} />\n")

    # ── Shared fill helper ─────────────────────────────────────────────────

    def _apply_fills_to_css(self, node: UNNode, css: Dict[str, str]) -> None:
        """
        Apply node.fills to a CSS dict.

        For image fills we emit ``background-image`` + ``background-size``.
        For solid / gradient fills we emit ``background``.
        Multiple fills are layered as comma-separated background layers.
        """
        if not node.fills:
            return

        enabled = [f for f in node.fills if getattr(f, "enabled", True)]
        if not enabled:
            return

        bg_layers: List[str] = []
        has_image = False

        for fill in reversed(enabled):
            if isinstance(fill, UNSolidFill):
                bg_layers.append(_css_color(fill.color))
            elif isinstance(fill, UNGradientFill):
                bg_layers.append(_gradient_css(fill))
            elif isinstance(fill, UNImageFill):
                has_image = True
                bg_layers.append(f"url('{fill.url}')")

        if bg_layers:
            css["background"] = ", ".join(bg_layers)

        if has_image:
            # Map image mode to background-size / background-repeat
            # Use the last image fill's mode (topmost image layer)
            for fill in reversed(enabled):
                if isinstance(fill, UNImageFill):
                    size_map = {
                        ImageFillMode.FILL: "cover",
                        ImageFillMode.FIT: "contain",
                        ImageFillMode.STRETCH: "100% 100%",
                        ImageFillMode.TILE: "auto",
                    }
                    css["background-size"] = size_map.get(fill.mode, "cover")
                    css["background-position"] = "center"
                    if fill.mode == ImageFillMode.TILE:
                        css["background-repeat"] = "repeat"
                    else:
                        css["background-repeat"] = "no-repeat"
                    break


# ===========================================================================
# HTML / attribute escaping
# ===========================================================================


def _esc_html(text: str) -> str:
    """Escape HTML special characters in text content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_attr(text: str) -> str:
    """Escape HTML special characters in attribute values."""
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ===========================================================================
# PaperWriter — BaseWriter implementation
# ===========================================================================


class PaperWriter(BaseWriter):
    """
    Write a UNNode tree to Paper Design via the ``write_html`` MCP tool.

    The writer converts the UNNode tree to an HTML string with inline styles
    and sends it to the specified Paper artboard using ``write_html``.

    Parameters
    ----------
    host        : Paper Desktop host (default '127.0.0.1')
    port        : Paper Desktop MCP port (default 29979)
    indent_size : HTML indentation size (default 2)
    mode        : write_html mode — "replace" (default) or "append"

    Example
    -------
    ::

        from adapters.paper import PaperWriter

        with PaperWriter() as writer:
            # Write a UNNode tree into the artboard "TO-0"
            new_id = writer.write_node(tree, parent_id="TO-0")

            # Replace an existing node
            new_id = writer.write_node(tree, replace_id="old-node-id")
    """

    tool_name = "paper"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 29979,
        indent_size: int = 2,
        mode: str = "replace",
    ) -> None:
        self._client = PaperClient(host=host, port=port)
        self._indent_size = indent_size
        self._mode = mode

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._client.connect()

    def disconnect(self) -> None:
        self._client.disconnect()

    # ── BaseWriter interface ───────────────────────────────────────────────

    def write_node(
        self,
        node: UNNode,
        parent_id: str = "",
        replace_id: str = "",
    ) -> str:
        """
        Write ``node`` (and its children) to Paper Design.

        Strategy
        --------
        1. Convert the UNNode tree to an HTML string.
        2. Determine the target artboard / parent:
           - If ``replace_id`` is set, find its parent artboard and write
             there (with mode="replace"), then delete the old node.
           - If ``parent_id`` is set, write directly into that node.
           - Otherwise, create a new artboard sized to the root node.
        3. Call ``PaperClient.write_html(target_id, html, mode)``
        4. Return the Paper node ID of the result.

        Parameters
        ----------
        node       : UNNode tree to write.
        parent_id  : Target Paper node ID to write into (artboard or frame).
        replace_id : Existing Paper node ID to replace.

        Returns
        -------
        str — Paper node ID of the written node (parent_id or new artboard id).

        Raises
        ------
        WriteError  if write_html reports failure.
        PaperConnectionError if Paper Desktop is not reachable.
        """
        # 1. Emit HTML
        emitter = _HtmlEmitter(indent_size=self._indent_size)
        html = emitter.emit(node)

        log.debug(
            "PaperWriter: emitted %d chars of HTML for node '%s'",
            len(html),
            node.name,
        )

        # 2. Determine target
        target_id: str

        if replace_id:
            # Write into the same parent with replace mode
            target_id = replace_id
            write_mode = "replace"
        elif parent_id:
            target_id = parent_id
            write_mode = self._mode
        else:
            # Create a new artboard for the node
            w = int(node.width.value) if node.width.mode.value == "fixed" else 390
            h = int(node.height.value) if node.height.mode.value == "fixed" else 844
            bg_color = "#050508"
            # Try to read background color from node's first solid fill
            for fill in node.fills:
                if isinstance(fill, UNSolidFill) and getattr(fill, "enabled", True):
                    bg_color = _css_color(fill.color)
                    break
            artboard_name = node.name or "Converted"
            target_id = self._client.create_artboard(
                artboard_name,
                {
                    "width": f"{w}px",
                    "height": f"{h}px",
                    "backgroundColor": bg_color,
                },
            )
            write_mode = "replace"
            log.info(
                "PaperWriter: created artboard '%s' (id=%s)", artboard_name, target_id
            )

        # 3. Write
        result = self._client.write_html(target_id, html, mode=write_mode)

        if isinstance(result, dict) and result.get("success") is False:
            raise WriteError(
                "paper",
                f"write_html reported failure: {result}",
            )

        log.info(
            "PaperWriter: wrote %d HTML chars to Paper node '%s'",
            len(html),
            target_id,
        )
        return target_id

    def delete_node(self, node_id: str) -> None:
        """Delete a Paper node by ID."""
        try:
            self._client.delete_nodes([node_id])
        except Exception as exc:
            log.warning("PaperWriter.delete_node failed for '%s': %s", node_id, exc)

    def move_node(self, node_id: str, new_parent_id: str, index: int = -1) -> None:
        """Move a Paper node to a different parent."""
        try:
            self._client.move_node(node_id, new_parent_id, index=index)
        except Exception as exc:
            log.warning("PaperWriter.move_node failed: %s", exc)

    def screenshot(self, node_id: str, scale: float = 1.0) -> Optional[bytes]:
        """Capture a PNG screenshot of a written node."""
        return self._client.screenshot(node_id, scale=scale)

    # ── Convenience helpers ────────────────────────────────────────────────

    def write_to_artboard(
        self,
        node: UNNode,
        artboard_name: str,
        *,
        create_if_missing: bool = True,
        width: int = 390,
        height: int = 844,
        background: str = "#050508",
    ) -> str:
        """
        Write ``node`` to a named artboard, creating it if it doesn't exist.

        Parameters
        ----------
        node              : UNNode tree to write.
        artboard_name     : Display name of the target artboard.
        create_if_missing : Whether to create the artboard if not found.
        width, height     : Dimensions if artboard needs to be created.
        background        : Background color for new artboard.

        Returns
        -------
        str — Paper artboard node ID.
        """
        existing = self._client.get_artboard_by_name(artboard_name)
        if existing:
            target_id = existing["id"]
        elif create_if_missing:
            target_id = self._client.create_artboard(
                artboard_name,
                {
                    "width": f"{width}px",
                    "height": f"{height}px",
                    "backgroundColor": background,
                },
            )
            log.info(
                "PaperWriter: created artboard '%s' id=%s", artboard_name, target_id
            )
        else:
            raise WriteError("paper", f"Artboard '{artboard_name}' not found.")

        return self.write_node(node, parent_id=target_id)

    def generate_html(self, node: UNNode) -> str:
        """
        Generate the HTML string for a UNNode tree without writing to Paper.
        Useful for previewing or debugging the output.
        """
        emitter = _HtmlEmitter(indent_size=self._indent_size)
        return emitter.emit(node)

    def __repr__(self) -> str:
        return f"<PaperWriter client={self._client!r} mode={self._mode!r}>"
