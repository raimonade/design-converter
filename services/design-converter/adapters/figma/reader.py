"""
Figma Reader  —  Figma API → Universal Node Tree
=====================================================
Reads from Figma via the REST API and converts the node tree to UNNode.

Pipeline
---------
1. FigmaClient.get_file(file_key) → Figma document JSON
2. FigmaClient.get_file_nodes(file_key, [node_ids]) → specific nodes
3. _figma_node_to_unnode() → recursive conversion to UNNode
4. Return the full UNNode tree

Figma Node Types Mapping
-----------------------
  DOCUMENT     → FRAME (root container)
  CANVAS      → FRAME (artboard/page)
  FRAME       → FRAME (group/frame)
  GROUP       → GROUP
  TEXT        → TEXT
  RECTANGLE   → RECTANGLE
  ELLIPSE     → ELLIPSE
  LINE        → LINE
  VECTOR      → PATH
  BOOLEAN_OPERATION → PATH (compound path)
  COMPONENT   → COMPONENT
  COMPONENT_SET → FRAME (variant group)
  INSTANCE    → INSTANCE

Usage
-----
    from adapters.figma import FigmaReader

    with FigmaReader() as reader:
        tree = reader.read_node("ABC123", node_id="1:2")  # specific node
        print(tree)

    # Or without context manager
    reader = FigmaReader()
    reader.connect()
    tree = reader.read_node("ABC123")  # entire file
    reader.disconnect()
"""

from __future__ import annotations

import logging
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Sys-path bootstrap
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CONV_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _CONV_ROOT not in sys.path:
    sys.path.insert(0, _CONV_ROOT)

from adapters.base import BaseReader, NodeNotFoundError
from adapters.figma.client import (
    FigmaAPIError,
    FigmaAuthError,
    FigmaClient,
    FigmaNotFoundError,
)
from ir.nodes import (
    AlignItems,
    BlendMode,
    GradientType,
    ImageFillMode,
    JustifyContent,
    LayoutMode,
    NodeType,
    SizingMode,
    StrokeAlign,
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
    UNStrokeThickness,
    UNTextRun,
    UNTextStyle,
    UNFill,
    UNEffect,
)


# ---------------------------------------------------------------------------
# Variable binding — local dataclass (dict-keyed, richer than ir.UNVariableBinding)
# ---------------------------------------------------------------------------

@dataclass
class UNVariableBinding:
    """
    Represents a Figma design variable bound to a node property.
    Stored as a dict keyed by property name on un_node.variable_bindings.
    """
    variable_id: str = ""
    variable_name: str = ""
    collection_name: str = ""
    resolved_type: str = "COLOR"

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Figma → UNNode mapping helpers
# ---------------------------------------------------------------------------

# Figma node type → NodeType
_FIGMA_TYPE_MAP = {
    "DOCUMENT": NodeType.FRAME,
    "CANVAS": NodeType.FRAME,
    "FRAME": NodeType.FRAME,
    "GROUP": NodeType.GROUP,
    "TEXT": NodeType.TEXT,
    "RECTANGLE": NodeType.RECTANGLE,
    "ELLIPSE": NodeType.ELLIPSE,
    "LINE": NodeType.LINE,
    "VECTOR": NodeType.PATH,
    "BOOLEAN_OPERATION": NodeType.PATH,
    "COMPONENT": NodeType.COMPONENT,
    "COMPONENT_SET": NodeType.FRAME,
    "INSTANCE": NodeType.INSTANCE,
    "STAR": NodeType.PATH,
    "POLYGON": NodeType.PATH,
    "REGULAR_POLYGON": NodeType.PATH,
    "SLICE": None,  # Skip slice nodes
    "SECTION": NodeType.FRAME,
}

# Blend mode mapping
_BLEND_MODE_MAP = {
    "PASS_THROUGH": BlendMode.NORMAL,
    "NORMAL": BlendMode.NORMAL,
    "MULTIPLY": BlendMode.MULTIPLY,
    "SCREEN": BlendMode.SCREEN,
    "OVERLAY": BlendMode.OVERLAY,
    "DARKEN": BlendMode.DARKEN,
    "LIGHTEN": BlendMode.LIGHTEN,
    "COLOR_DODGE": BlendMode.DODGE,
    "COLOR_BURN": BlendMode.BURN,
    "HARD_LIGHT": BlendMode.HARD_LIGHT,
    "SOFT_LIGHT": BlendMode.SOFT_LIGHT,
    "DIFFERENCE": BlendMode.DIFFERENCE,
    "EXCLUSION": BlendMode.EXCLUSION,
    "HUE": BlendMode.HUE,
    "SATURATION": BlendMode.SATURATION,
    "COLOR": BlendMode.COLOR,
    "LUMINOSITY": BlendMode.LUMINOSITY,
}

# Text align mapping
_TEXT_ALIGN_MAP = {
    "LEFT": TextAlign.LEFT,
    "CENTER": TextAlign.CENTER,
    "RIGHT": TextAlign.RIGHT,
    "JUSTIFIED": TextAlign.JUSTIFY,
}

# Justify content mapping
_JUSTIFY_MAP = {
    "MIN": JustifyContent.START,
    "MAX": JustifyContent.END,
    "CENTER": JustifyContent.CENTER,
    "SPACE_BETWEEN": JustifyContent.SPACE_BETWEEN,
    "SPACE_AROUND": JustifyContent.SPACE_AROUND,
}

# Align items mapping
_ALIGN_MAP = {
    "MIN": AlignItems.START,
    "MAX": AlignItems.END,
    "CENTER": AlignItems.CENTER,
    "STRETCH": AlignItems.STRETCH,
    # AlignItems.BASELINE does not exist in the IR enum; fall back to START.
    # Figma BASELINE aligns items on their text baselines, closest IR analog is START.
    "BASELINE": AlignItems.START,
}
# Alias for external access (used in verification scripts and tests)
_ALIGN_ITEMS_MAP = _ALIGN_MAP


# ---------------------------------------------------------------------------
# Color conversion
# ---------------------------------------------------------------------------

def _figma_color_to_un(color: Dict[str, float], opacity: float = 1.0) -> UNColor:
    """Convert Figma {r, g, b, a?} to UNColor (0-1 floats)."""
    r = color.get("r", 0)
    g = color.get("g", 0)
    b = color.get("b", 0)
    a = color.get("a", 1.0) * opacity
    return UNColor(r=round(r, 4), g=round(g, 4), b=round(b, 4), a=round(a, 4))


# ---------------------------------------------------------------------------
# Fill conversion
# ---------------------------------------------------------------------------

def _convert_fills(fills: Optional[List[Dict]], node_name: str = "") -> List[UNFill]:
    """Convert Figma fills to UNFill list."""
    if not fills:
        return []

    result = []
    for fill in fills:
        if not fill.get("visible", True):
            continue

        fill_type = fill.get("type")
        opacity = fill.get("opacity", 1.0)
        blend_mode = _BLEND_MODE_MAP.get(fill.get("blendMode", "NORMAL"), BlendMode.NORMAL)

        if fill_type == "SOLID":
            color = _figma_color_to_un(fill.get("color", {}), opacity)
            result.append(UNSolidFill(
                color=color,
                opacity=opacity,
                blend_mode=blend_mode,
                enabled=fill.get("visible", True),
            ))
        elif fill_type == "GRADIENT_LINEAR":
            stops = []
            for stop in fill.get("gradientStops", []):
                pos = stop.get("position", 0)
                color = _figma_color_to_un(stop.get("color", {}), opacity)
                stops.append(UNGradientStop(color=color, position=pos))

            # Figma gradient handles to rotation
            handles = fill.get("gradientHandles", [])
            rotation = 180.0  # default
            if len(handles) >= 2:
                h0 = handles[0].get("position", {"x": 0, "y": 0})
                h1 = handles[1].get("position", {"x": 1, "y": 1})
                dx = h1["x"] - h0["x"]
                dy = h1["y"] - h0["y"]
                rotation = (math.degrees(math.atan2(dy, dx)) + 180) % 360

            result.append(UNGradientFill(
                gradient_type=GradientType.LINEAR,
                rotation=rotation,
                stops=stops,
                opacity=opacity,
                blend_mode=blend_mode,
                enabled=fill.get("visible", True),
            ))
        elif fill_type == "GRADIENT_RADIAL":
            stops = []
            for stop in fill.get("gradientStops", []):
                pos = stop.get("position", 0)
                color = _figma_color_to_un(stop.get("color", {}), opacity)
                stops.append(UNGradientStop(color=color, position=pos))

            result.append(UNGradientFill(
                gradient_type=GradientType.RADIAL,
                rotation=0,
                stops=stops,
                opacity=opacity,
                blend_mode=blend_mode,
                enabled=fill.get("visible", True),
            ))
        elif fill_type == "IMAGE":
            scale_mode = fill.get("scaleMode", "FILL")
            mode_map = {
                "FILL": ImageFillMode.FILL,
                "FIT": ImageFillMode.FIT,
                "TILE": ImageFillMode.TILE,
                "STRETCH": ImageFillMode.STRETCH,
            }
            image_ref = fill.get("imageRef", "")
            if image_ref:
                log.warning(
                    "Image fill URL for node '%s' is a temporary Figma CDN URL "
                    "that expires in ~24h. Consider downloading and caching it.",
                    node_name,
                )
            result.append(UNImageFill(
                url=image_ref,
                mode=mode_map.get(scale_mode, ImageFillMode.FILL),
                opacity=opacity,
                blend_mode=blend_mode,
                enabled=fill.get("visible", True),
            ))

    return result


# ---------------------------------------------------------------------------
# Stroke conversion
# ---------------------------------------------------------------------------

def _convert_strokes(strokes: Optional[List[Dict]]) -> List[UNStroke]:
    """Convert Figma strokes to UNStroke list."""
    if not strokes:
        return []

    result = []
    for stroke in strokes:
        if not stroke.get("visible", True):
            continue

        stroke_type = stroke.get("type")
        if stroke_type != "SOLID":
            continue  # Skip non-solid strokes for now

        color = _figma_color_to_un(stroke.get("color", {}))
        opacity = stroke.get("opacity", 1.0)
        blend_mode = _BLEND_MODE_MAP.get(stroke.get("blendMode", "NORMAL"), BlendMode.NORMAL)

        # Stroke weights
        weights = stroke.get("strokeWeight", 1)
        if isinstance(weights, (int, float)):
            thickness = UNStrokeThickness.uniform(float(weights))
        else:
            thickness = UNStrokeThickness(
                top=weights.get("top", 1),
                right=weights.get("right", 1),
                bottom=weights.get("bottom", 1),
                left=weights.get("left", 1),
            )

        # Stroke align
        align_map = {"INSIDE": StrokeAlign.INSIDE, "CENTER": StrokeAlign.CENTER, "OUTSIDE": StrokeAlign.OUTSIDE}
        align = align_map.get(stroke.get("strokeAlign", "CENTER"), StrokeAlign.CENTER)

        cap = stroke.get("strokeCap", "NONE").lower()
        join = stroke.get("strokeJoin", "MITER").lower()
        dash = stroke.get("dashPattern", [])

        result.append(UNStroke(
            fill=UNSolidFill(color=color, opacity=opacity, blend_mode=blend_mode),
            thickness=thickness,
            align=align,
            cap=cap,
            join=join,
            dash_pattern=list(dash) if dash else [],
            enabled=stroke.get("visible", True),
        ))

    return result


# ---------------------------------------------------------------------------
# Effects conversion
# ---------------------------------------------------------------------------

def _convert_effects(effects: Optional[List[Dict]]) -> List[UNEffect]:
    """Convert Figma effects to UNEffect list."""
    if not effects:
        return []

    result = []
    for effect in effects:
        if not effect.get("visible", True):
            continue

        effect_type = effect.get("type")
        opacity = effect.get("opacity", 1.0)
        blend_mode = _BLEND_MODE_MAP.get(effect.get("blendMode", "NORMAL"), BlendMode.NORMAL)

        if effect_type == "DROP_SHADOW":
            color = _figma_color_to_un(effect.get("color", {}), opacity)
            offset = effect.get("offset", {})
            result.append(UNDropShadow(
                color=color,
                offset_x=offset.get("x", 0),
                offset_y=offset.get("y", 4),
                blur=effect.get("radius", 8),
                spread=effect.get("spread", 0),
                inner=False,
                blend_mode=blend_mode,
                enabled=effect.get("visible", True),
            ))
        elif effect_type == "INNER_SHADOW":
            color = _figma_color_to_un(effect.get("color", {}), opacity)
            offset = effect.get("offset", {})
            result.append(UNDropShadow(
                color=color,
                offset_x=offset.get("x", 0),
                offset_y=offset.get("y", 4),
                blur=effect.get("radius", 8),
                spread=effect.get("spread", 0),
                inner=True,
                blend_mode=blend_mode,
                enabled=effect.get("visible", True),
            ))
        elif effect_type == "LAYER_BLUR":
            result.append(UNBlur(
                radius=effect.get("radius", 8),
                background=False,
                enabled=effect.get("visible", True),
            ))
        elif effect_type == "BACKGROUND_BLUR":
            result.append(UNBlur(
                radius=effect.get("radius", 8),
                background=True,
                enabled=effect.get("visible", True),
            ))

    return result


# ---------------------------------------------------------------------------
# Corner radius conversion
# ---------------------------------------------------------------------------

def _convert_corner_radius(corner_radius: Any, rectangle_corner_radius: Any = None) -> UNCornerRadius:
    """Convert Figma corner radius to UNCornerRadius."""
    if isinstance(corner_radius, (int, float)):
        return UNCornerRadius.all(float(corner_radius))

    if isinstance(corner_radius, dict):
        return UNCornerRadius(
            tl=corner_radius.get("topLeft", 0),
            tr=corner_radius.get("topRight", 0),
            br=corner_radius.get("bottomRight", 0),
            bl=corner_radius.get("bottomLeft", 0),
        )

    # Also check rectangleCornerRadius
    if rectangle_corner_radius:
        if isinstance(rectangle_corner_radius, (int, float)):
            return UNCornerRadius.all(float(rectangle_corner_radius))
        if isinstance(rectangle_corner_radius, dict):
            return UNCornerRadius(
                tl=rectangle_corner_radius.get("topLeft", 0),
                tr=rectangle_corner_radius.get("topRight", 0),
                br=rectangle_corner_radius.get("bottomRight", 0),
                bl=rectangle_corner_radius.get("bottomLeft", 0),
            )

    return UNCornerRadius()


# ---------------------------------------------------------------------------
# Layout conversion
# ---------------------------------------------------------------------------

def _convert_layout(node: Dict[str, Any]) -> tuple:
    """Convert Figma auto-layout to UNNode layout properties."""
    layout_mode = node.get("layoutMode", "NONE")

    if layout_mode == "HORIZONTAL":
        layout = LayoutMode.HORIZONTAL
    elif layout_mode == "VERTICAL":
        layout = LayoutMode.VERTICAL
    else:
        layout = LayoutMode.NONE

    gap = node.get("itemSpacing", 0) or node.get("gap", 0)

    # Padding
    pt = node.get("paddingTop", 0)
    pr = node.get("paddingRight", 0)
    pb = node.get("paddingBottom", 0)
    pl = node.get("paddingLeft", 0)
    if pt and pr and pb and pl and pt == pr == pb == pl:
        un_padding = UNPadding.all(pt)
    else:
        un_padding = UNPadding(top=pt or 0, right=pr or 0, bottom=pb or 0, left=pl or 0)

    # Justify content
    primary_axis_align = node.get("primaryAxisAlignItems", "MIN")
    justify = _JUSTIFY_MAP.get(primary_axis_align, JustifyContent.START)

    # Align items
    counter_axis_align = node.get("counterAxisAlignItems", "MIN")
    align = _ALIGN_MAP.get(counter_axis_align, AlignItems.START)

    return layout, gap, un_padding, justify, align


# ---------------------------------------------------------------------------
# Text style conversion
# ---------------------------------------------------------------------------

def _convert_text_style(style: Dict[str, Any]) -> UNTextStyle:
    """Convert Figma text style to UNTextStyle."""
    font_family = style.get("fontFamily", "Inter")

    # Font weight from style name
    font_style_name = style.get("fontStyle", "Regular")
    if "Bold" in font_style_name:
        font_weight = "700"
    elif "SemiBold" in font_style_name or "Demi" in font_style_name:
        font_weight = "600"
    elif "Medium" in font_style_name:
        font_weight = "500"
    elif "Light" in font_style_name:
        font_weight = "300"
    elif "Thin" in font_style_name:
        font_weight = "100"
    else:
        font_weight = "400"

    font_style = "italic" if "Italic" in font_style_name else "normal"
    font_size = style.get("fontSize", 14)

    # Line height
    line_height = None
    line_height_raw = style.get("lineHeightPx")
    if line_height_raw:
        line_height = line_height_raw

    # Letter spacing
    letter_spacing = style.get("letterSpacing", 0)
    if isinstance(letter_spacing, dict):
        letter_spacing = letter_spacing.get("value", 0)

    # Text align
    text_align_raw = style.get("textAlignHorizontal", "LEFT")
    text_align = _TEXT_ALIGN_MAP.get(text_align_raw, TextAlign.LEFT)

    # Text auto-resize
    auto_resize = style.get("textAutoResize", "WIDTH_AND_HEIGHT")
    if auto_resize == "NONE":
        text_auto_resize = TextAutoResize.NONE
    elif auto_resize == "WIDTH_AND_HEIGHT":
        text_auto_resize = TextAutoResize.WIDTH_HEIGHT
    elif auto_resize == "HEIGHT":
        text_auto_resize = TextAutoResize.HEIGHT
    else:
        text_auto_resize = TextAutoResize.WIDTH_HEIGHT

    return UNTextStyle(
        font_family=font_family,
        font_size=font_size,
        font_weight=font_weight,
        font_style=font_style,
        line_height=line_height,
        letter_spacing=letter_spacing or 0,
        text_align=text_align,
        text_transform=TextTransform.NONE,
        text_auto_resize=text_auto_resize,
    )


# ---------------------------------------------------------------------------
# Rich text run extraction
# ---------------------------------------------------------------------------

def _extract_text_runs(node: Dict[str, Any], base_style: UNTextStyle) -> List[UNTextRun]:
    """
    Extract per-character style runs from Figma rich text fields.

    Figma stores rich text via two parallel structures:
      characterStyleOverrides  — List[int], one index per character (0 = base style)
      styleOverrideTable       — Dict[str, {...fontProps...}], index → style override dict

    We group consecutive characters that share the same style index into runs,
    then map each override dict to a UNTextRun, skipping runs that have no
    overrides (index == 0, meaning they use the base style already on UNNode).
    """
    chars: str = node.get("characters", "")
    overrides: List[int] = node.get("characterStyleOverrides", [])
    table: Dict[str, Any] = node.get("styleOverrideTable", {})

    if not chars or not overrides or not table:
        return []

    # Normalise override list length to match chars
    if len(overrides) < len(chars):
        overrides = overrides + [0] * (len(chars) - len(overrides))

    runs: List[UNTextRun] = []
    i = 0
    while i < len(chars):
        idx = overrides[i]
        # Collect span of identical style index
        j = i + 1
        while j < len(chars) and overrides[j] == idx:
            j += 1

        # Only emit a run when there IS a style override (idx != 0)
        if idx != 0:
            ov = table.get(str(idx), {})

            # Fill color
            fill_color: Optional[UNColor] = None
            ov_fills = ov.get("fills", [])
            if ov_fills and ov_fills[0].get("type") == "SOLID":
                fill_color = _figma_color_to_un(ov_fills[0].get("color", {}))

            # Font weight from style name (mirrors _convert_text_style)
            font_style_name: str = ov.get("fontStyle", "")
            font_weight: Optional[str] = None
            if font_style_name:
                if "Bold" in font_style_name:
                    font_weight = "700"
                elif "SemiBold" in font_style_name or "Demi" in font_style_name:
                    font_weight = "600"
                elif "Medium" in font_style_name:
                    font_weight = "500"
                elif "Light" in font_style_name:
                    font_weight = "300"
                elif "Thin" in font_style_name:
                    font_weight = "100"
                else:
                    font_weight = "400"

            italic = "Italic" in font_style_name if font_style_name else False

            # Text decoration
            decoration: str = ov.get("textDecoration", "")
            underline = decoration == "UNDERLINE"
            strikethrough = decoration == "STRIKETHROUGH"

            # Letter spacing
            ls = ov.get("letterSpacing", None)
            letter_spacing: Optional[float] = None
            if ls is not None:
                letter_spacing = float(ls) if not isinstance(ls, dict) else float(ls.get("value", 0))

            # Text transform
            tt_raw: str = ov.get("textCase", "")
            from ir.nodes import TextTransform as TT
            text_transform: Optional[TextTransform] = None
            if tt_raw == "UPPER":
                text_transform = TT.UPPERCASE
            elif tt_raw == "LOWER":
                text_transform = TT.LOWERCASE
            elif tt_raw == "TITLE":
                text_transform = TT.CAPITALIZE

            runs.append(UNTextRun(
                content=chars[i:j],
                start=i,
                end=j,
                fill=fill_color,
                font_family=ov.get("fontFamily") or None,
                font_size=ov.get("fontSize") or None,
                font_weight=font_weight,
                italic=italic,
                underline=underline,
                strikethrough=strikethrough,
                letter_spacing=letter_spacing,
                text_transform=text_transform,
            ))
        i = j

    return runs


# ---------------------------------------------------------------------------
# Main conversion function
# ---------------------------------------------------------------------------

def _figma_node_to_unnode(node: Dict[str, Any], depth: int = 0) -> Optional[UNNode]:
    """Recursively convert a Figma node dict to UNNode."""
    node_type = node.get("type")

    if node_type == "SLICE":
        return None

    un_type = _FIGMA_TYPE_MAP.get(node_type, NodeType.FRAME)
    if un_type is None:
        return None

    # Basic properties
    figma_id = node.get("id", "")
    name = node.get("name", "Untitled")

    # Position
    abs_bb = node.get("absoluteBoundingBox", {})
    x = abs_bb.get("x", node.get("x", 0)) or 0
    y = abs_bb.get("y", node.get("y", 0)) or 0

    # Size
    width = abs_bb.get("width", node.get("width", 100)) or 100
    height = abs_bb.get("height", node.get("height", 100)) or 100

    # Sizing mode
    width_mode = SizingMode.FIXED
    height_mode = SizingMode.FIXED
    layout_align = node.get("layoutAlign")
    if layout_align == "STRETCH":
        width_mode = SizingMode.FILL
    if node.get("layoutGrow") == 1:
        height_mode = SizingMode.FILL

    # Opacity
    opacity = node.get("opacity", 1.0) or 1.0

    # Visible
    visible = node.get("visible", True)
    if visible is None:
        visible = True

    # Blend mode
    blend_mode = _BLEND_MODE_MAP.get(node.get("blendMode", "NORMAL"), BlendMode.NORMAL)

    # Clip content
    clip_content = node.get("clipsContent", False) or node.get("overflowDirection", 0) != 0

    # Rotation
    rotation = node.get("rotation", 0) or 0

    # Create the UNNode
    un_node = UNNode(
        type=un_type,
        id=figma_id,
        name=name,
        x=x,
        y=y,
        width=UNSize(value=width, mode=width_mode),
        height=UNSize(value=height, mode=height_mode),
        opacity=opacity,
        visible=visible,
        blend_mode=blend_mode,
        clip_content=clip_content,
        rotation=rotation,
        source_tool="figma",
        source_id=figma_id,
    )

    # Fills
    un_node.fills = _convert_fills(node.get("fills"), node_name=name)

    # Strokes
    un_node.strokes = _convert_strokes(node.get("strokes"))

    # Effects
    un_node.effects = _convert_effects(node.get("effects"))

    # Corner radius
    un_node.corner_radius = _convert_corner_radius(
        node.get("cornerRadius"),
        node.get("rectangleCornerRadius"),
    )

    # Layout (auto-layout)
    layout, gap, padding, justify, align = _convert_layout(node)
    un_node.layout = layout
    un_node.gap = gap
    un_node.padding = padding
    un_node.justify_content = justify
    un_node.align_items = align

    # Layout wrap
    un_node.layout_wrap = node.get("layoutWrap", "NO_WRAP") == "WRAP"

    # Variable bindings — extract Figma boundVariables into a dict keyed by prop name.
    # We replace the default list with a dict for richer dict-keyed access;
    # Python does not enforce the List[UNVariableBinding] annotation at runtime.
    bound_vars = node.get("boundVariables", {})
    if bound_vars:
        bindings_dict: Dict[str, UNVariableBinding] = {}
        for prop_name, binding_info in bound_vars.items():
            # binding_info can be a single binding dict or a list (e.g. fills array)
            if isinstance(binding_info, list):
                binding_info = binding_info[0] if binding_info else None
            if isinstance(binding_info, dict):
                var_id = binding_info.get("id", "")
                if var_id:
                    bindings_dict[prop_name] = UNVariableBinding(
                        variable_id=var_id,
                        variable_name=binding_info.get("name", var_id),
                        collection_name=binding_info.get("collectionName", ""),
                        resolved_type=binding_info.get("resolvedType", "COLOR"),
                    )
        if bindings_dict:
            # Store as dict for keyed access; falls back gracefully to empty list if unset
            un_node.variable_bindings = bindings_dict  # type: ignore[assignment]

    # Text-specific properties
    if node_type == "TEXT":
        un_node.text_content = node.get("characters", "")
        style = node.get("style", {})
        un_node.text_style = _convert_text_style(style)
        un_node.text_runs = _extract_text_runs(node, un_node.text_style)

        # Text color from fills if not already set
        if not un_node.fills:
            fills = node.get("fills", [])
            if fills:
                text_color = fills[0].get("color", {})
                if text_color:
                    un_node.fills.append(UNSolidFill(color=_figma_color_to_un(text_color)))

    # Path/Vector properties
    if node_type in ("VECTOR", "BOOLEAN_OPERATION", "STAR", "POLYGON", "REGULAR_POLYGON"):
        vector_paths = node.get("vectorPaths", [])
        if vector_paths:
            un_node.geometry = vector_paths[0].get("path", "")
            un_node.fill_rule = vector_paths[0].get("fillRule", "NONZERO").lower()
        else:
            un_node.geometry = ""
            un_node.fill_rule = "nonzero"

    # Ellipse properties
    if node_type == "ELLIPSE":
        un_node.inner_radius = node.get("innerCircleRadius", 0) or 0

    # Component/Instance properties
    if node_type == "INSTANCE":
        un_node.component_id = node.get("componentId", "")
        # componentProperties holds named prop values (text, booleans, variant choices)
        component_properties = node.get("componentProperties", {})
        if component_properties:
            un_node.component_props = dict(component_properties)
        # overrides holds direct property overrides on the instance
        instance_overrides = node.get("overrides", [])
        if instance_overrides:
            # Merge override entries into component_props under an "overrides" key
            if "overrides" not in un_node.component_props:
                un_node.component_props["overrides"] = instance_overrides
    elif node_type == "COMPONENT":
        un_node.component_id = node.get("componentId", figma_id)

    # Children
    children = node.get("children", [])
    for child in children:
        child_node = _figma_node_to_unnode(child, depth + 1)
        if child_node:
            un_node.children.append(child_node)

    return un_node


# ============================================================================
# FigmaReader — BaseReader implementation
# ============================================================================

class FigmaReader(BaseReader):
    """
    Read from Figma via the REST API and return a UNNode tree.

    Parameters
    ----------
    token       : Figma API token (FIGMA_API_KEY env var used if not provided)
    file_key   : Optional Figma file key to read (can also pass to read_node)

    Example
    -------
    ::

        with FigmaReader() as reader:
            tree = reader.read_node("ABC123")           # entire file
            tree = reader.read_node("ABC123", node_id="1:2")  # specific node
    """

    tool_name = "figma"

    def __init__(
        self,
        token: Optional[str] = None,
        file_key: Optional[str] = None,
    ) -> None:
        self._client = FigmaClient(token=token)
        self._file_key = file_key

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Verify connectivity and token."""
        self._client.ping()

    def disconnect(self) -> None:
        """No persistent connection to close."""
        pass

    # ── BaseReader interface ───────────────────────────────────────────────

    def read_node(self, file_key: str, node_id: str = "") -> UNNode:
        """
        Read from Figma and return a UNNode tree.

        Parameters
        ----------
        file_key : str
            Figma file key (from URL: figma.com/design/FILE_KEY/...)
        node_id : str, optional
            Specific node ID to read (e.g., "1:2"). If empty, returns entire file.

        Returns
        -------
        UNNode — root of the converted node tree.

        Raises
        ------
        NodeNotFoundError   if the node does not exist.
        FigmaAuthError     if the API token is invalid.
        FigmaAPIError      if the API request fails.
        """
        try:
            if node_id:
                # Get specific node(s)
                result = self._client.get_file_nodes(file_key, [node_id])
                nodes = result.get("nodes", {})
                if node_id not in nodes:
                    raise NodeNotFoundError(node_id, tool="figma")
                node_data = nodes[node_id].get("document", {})
            else:
                # Get entire file
                result = self._client.get_file(file_key)
                node_data = result.get("document", {})

            if not node_data:
                raise NodeNotFoundError(node_id or "root", tool="figma")

            tree = _figma_node_to_unnode(node_data)
            if tree is None:
                raise ValueError(f"Could not convert Figma node to UNNode")

            tree.source_tool = "figma"
            tree.source_id = node_id or file_key

            return tree

        except FigmaNotFoundError:
            raise
        except FigmaAuthError:
            raise
        except FigmaAPIError:
            raise
        except Exception as exc:
            raise FigmaAPIError(str(exc)) from exc

    # ── Optional helpers ─────────────────────────────────────────────────

    def list_nodes(self) -> List[Dict[str, Any]]:
        """Return a list of pages/canvases in the Figma file."""
        try:
            result = self._client.get_file(self._file_key or "")
            document = result.get("document", {})
            pages = document.get("children", [])
            return [
                {
                    "id": p.get("id", ""),
                    "name": p.get("name", ""),
                    "type": "page",
                }
                for p in pages
            ]
        except Exception as exc:
            log.warning("FigmaReader.list_nodes failed: %s", exc)
            return []

    def get_file_info(self) -> Dict[str, Any]:
        """Return metadata about the Figma file."""
        try:
            result = self._client.get_file(self._file_key or "")
            return {
                "name": result.get("name", ""),
                "lastModified": result.get("lastModified", ""),
                "version": result.get("version", ""),
            }
        except Exception:
            return {}

    def __repr__(self) -> str:
        return f"<FigmaReader client={self._client!r}>"
