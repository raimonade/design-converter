"""
Pencil Reader  —  Pencil.dev MCP → Universal Node Tree
=======================================================
Reads a Pencil artboard (or any node) by calling the Pencil MCP server,
then converts the returned node JSON into a UNNode tree that any downstream
adapter can consume.

Reading pipeline
----------------
1. ``PencilClient.get_node(node_id)``  → raw Pencil node dict (recursive)
2. ``_pencil_node_to_un``              → maps each Pencil node to a UNNode
3. Full UNNode tree returned to the caller

Pencil node shapes (inferred from MCP API conventions)
------------------------------------------------------
Every node dict contains at minimum:
  {
    "id":      str,
    "name":    str,
    "type":    "FRAME" | "TEXT" | "RECTANGLE" | "ELLIPSE" | "PATH" |
               "GROUP" | "IMAGE" | "LINE" | "COMPONENT" | "INSTANCE",
    "x":       float,
    "y":       float,
    "width":   float,
    "height":  float,
    "visible": bool,
    "opacity": float,            # 0.0–1.0
    "rotation": float,           # degrees
    "fills":   [...],
    "strokes": [...],
    "effects": [...],
    "children": [...],           # only on containers
  }

Fill shapes:
  Solid:    {"type": "SOLID", "color": "#rrggbb", "opacity": float}
  Linear:   {"type": "LINEAR_GRADIENT", "stops": [...], "angle": float}
  Radial:   {"type": "RADIAL_GRADIENT", "stops": [...]}
  Image:    {"type": "IMAGE", "url": str, "mode": "fill"|"fit"|"tile"}

Gradient stop: {"color": "#rrggbb", "position": float, "opacity": float}

Stroke shape:
  {"color": "#rrggbb", "width": float, "align": "inside"|"center"|"outside",
   "opacity": float, "dashPattern": [float]}

Effect shapes:
  Shadow: {"type": "DROP_SHADOW"|"INNER_SHADOW", "color": "#rrggbb",
           "offsetX": float, "offsetY": float, "blur": float, "spread": float}
  Blur:   {"type": "LAYER_BLUR"|"BACKGROUND_BLUR", "radius": float}

Layout shape (auto-layout frames):
  {"layout": "FLEX", "layoutDirection": "HORIZONTAL"|"VERTICAL",
   "gap": float, "padding": [top, right, bottom, left],
   "justifyContent": "start"|"center"|"end"|"space-between",
   "alignItems": "start"|"center"|"end"|"stretch"}

Text-specific fields:
  {"content": str, "fontSize": float, "fontFamily": str, "fontWeight": str,
   "fontStyle": str, "lineHeight": float|null, "letterSpacing": float,
   "textAlign": "left"|"center"|"right"|"justify",
   "textTransform": "none"|"uppercase"|"lowercase"|"capitalize",
   "textDecoration": str}

Usage
-----
    from adapters.pencil import PencilReader

    with PencilReader() as reader:
        boards = reader.list_nodes()
        tree   = reader.read_node(boards[0]["id"])

    # Without context manager
    reader = PencilReader()
    reader.connect()
    tree = reader.read_node("some-frame-id")
    reader.disconnect()
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Sys-path bootstrap (allows running from repo root or directly)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CONV_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _CONV_ROOT not in sys.path:
    sys.path.insert(0, _CONV_ROOT)

from adapters.base import BaseReader, NodeNotFoundError
from adapters.pencil.client import PencilClient, PencilToolError
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
    UNTextStyle,
    UNVariableBinding,
)
from utils.color import normalize_hex, parse_css_color

log = logging.getLogger(__name__)


# ===========================================================================
# Pencil → UNT mapping tables
# ===========================================================================

# Pencil node type string → NodeType enum
_NODE_TYPE_MAP: Dict[str, NodeType] = {
    "FRAME": NodeType.FRAME,
    "GROUP": NodeType.GROUP,
    "RECTANGLE": NodeType.RECTANGLE,
    "ELLIPSE": NodeType.ELLIPSE,
    "PATH": NodeType.PATH,
    "LINE": NodeType.PATH,  # lines become paths
    "TEXT": NodeType.TEXT,
    "IMAGE": NodeType.IMAGE,
    "COMPONENT": NodeType.COMPONENT,
    "INSTANCE": NodeType.INSTANCE,
    "VECTOR": NodeType.PATH,
    "BOOLEAN_OPERATION": NodeType.PATH,
    "SLICE": NodeType.FRAME,
    "ARTBOARD": NodeType.FRAME,
}

# Pencil layout direction → LayoutMode
_LAYOUT_DIR_MAP: Dict[str, LayoutMode] = {
    "HORIZONTAL": LayoutMode.HORIZONTAL,
    "VERTICAL": LayoutMode.VERTICAL,
    "horizontal": LayoutMode.HORIZONTAL,
    "vertical": LayoutMode.VERTICAL,
    "row": LayoutMode.HORIZONTAL,
    "column": LayoutMode.VERTICAL,
}

# Pencil justifyContent → JustifyContent
_JUSTIFY_MAP: Dict[str, JustifyContent] = {
    "start": JustifyContent.START,
    "flex-start": JustifyContent.START,
    "MIN": JustifyContent.START,
    "center": JustifyContent.CENTER,
    "CENTER": JustifyContent.CENTER,
    "end": JustifyContent.END,
    "flex-end": JustifyContent.END,
    "MAX": JustifyContent.END,
    "space-between": JustifyContent.SPACE_BETWEEN,
    "SPACE_BETWEEN": JustifyContent.SPACE_BETWEEN,
    "space-around": JustifyContent.SPACE_AROUND,
}

# Pencil alignItems → AlignItems
_ALIGN_MAP: Dict[str, AlignItems] = {
    "start": AlignItems.START,
    "flex-start": AlignItems.START,
    "MIN": AlignItems.START,
    "center": AlignItems.CENTER,
    "CENTER": AlignItems.CENTER,
    "end": AlignItems.END,
    "flex-end": AlignItems.END,
    "MAX": AlignItems.END,
    "stretch": AlignItems.STRETCH,
    "STRETCH": AlignItems.STRETCH,
    "baseline": AlignItems.START,
}

# Pencil textAlign → TextAlign
_TEXT_ALIGN_MAP: Dict[str, TextAlign] = {
    "left": TextAlign.LEFT,
    "LEFT": TextAlign.LEFT,
    "center": TextAlign.CENTER,
    "CENTER": TextAlign.CENTER,
    "right": TextAlign.RIGHT,
    "RIGHT": TextAlign.RIGHT,
    "justify": TextAlign.JUSTIFY,
    "JUSTIFIED": TextAlign.JUSTIFY,
}

# Pencil textTransform → TextTransform
_TEXT_TRANSFORM_MAP: Dict[str, TextTransform] = {
    "none": TextTransform.NONE,
    "NONE": TextTransform.NONE,
    "uppercase": TextTransform.UPPERCASE,
    "UPPER": TextTransform.UPPERCASE,
    "lowercase": TextTransform.LOWERCASE,
    "LOWER": TextTransform.LOWERCASE,
    "capitalize": TextTransform.CAPITALIZE,
    "TITLE": TextTransform.CAPITALIZE,
}

# Pencil stroke align → StrokeAlign
_STROKE_ALIGN_MAP: Dict[str, StrokeAlign] = {
    "inside": StrokeAlign.INSIDE,
    "INSIDE": StrokeAlign.INSIDE,
    "center": StrokeAlign.CENTER,
    "CENTER": StrokeAlign.CENTER,
    "outside": StrokeAlign.OUTSIDE,
    "OUTSIDE": StrokeAlign.OUTSIDE,
}

# Pencil blend mode → BlendMode
_BLEND_MAP: Dict[str, BlendMode] = {
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

# Pencil image fill mode → ImageFillMode
_IMG_MODE_MAP: Dict[str, ImageFillMode] = {
    "fill": ImageFillMode.FILL,
    "FILL": ImageFillMode.FILL,
    "fit": ImageFillMode.FIT,
    "FIT": ImageFillMode.FIT,
    "stretch": ImageFillMode.STRETCH,
    "STRETCH": ImageFillMode.STRETCH,
    "tile": ImageFillMode.TILE,
    "TILE": ImageFillMode.TILE,
    "crop": ImageFillMode.FILL,
    "CROP": ImageFillMode.FILL,
}

# Font weight aliases that Pencil may return as strings
_WEIGHT_ALIASES: Dict[str, str] = {
    "Thin": "100",
    "ExtraLight": "200",
    "UltraLight": "200",
    "Light": "300",
    "Regular": "400",
    "Normal": "400",
    "Medium": "500",
    "SemiBold": "600",
    "DemiBold": "600",
    "Bold": "700",
    "ExtraBold": "800",
    "UltraBold": "800",
    "Black": "900",
    "Heavy": "900",
}


# ===========================================================================
# Color helpers
# ===========================================================================


def _parse_color(raw: Any) -> Optional[UNColor]:
    """
    Parse a Pencil color value into a UNColor.

    Pencil may provide color as:
      - "#rrggbb" or "#rrggbbaa" hex string
      - {"r": 0-255, "g": 0-255, "b": 0-255, "a": 0-1}   (mixed int/float)
      - {"r": 0.0-1.0, "g": 0.0-1.0, "b": 0.0-1.0, "a": 0.0-1.0}  (all float)
      - "rgba(r, g, b, a)" CSS string
    """
    if raw is None:
        return None

    if isinstance(raw, str):
        try:
            return parse_css_color(raw)
        except Exception:
            try:
                return UNColor.from_hex(raw)
            except Exception:
                return None

    if isinstance(raw, dict):
        r = raw.get("r", 0)
        g = raw.get("g", 0)
        b = raw.get("b", 0)
        a = raw.get("a", 1.0)

        # Normalise: if r/g/b look like 0-255 ints, convert
        if isinstance(r, (int, float)) and r > 1.0:
            r = r / 255.0
        if isinstance(g, (int, float)) and g > 1.0:
            g = g / 255.0
        if isinstance(b, (int, float)) and b > 1.0:
            b = b / 255.0

        return UNColor(r=float(r), g=float(g), b=float(b), a=float(a))

    return None


def _color_with_opacity(raw_color: Any, fill_opacity: float) -> Optional[UNColor]:
    """Parse color and apply an additional fill-level opacity multiplier."""
    c = _parse_color(raw_color)
    if c is None:
        return None
    c.a = c.a * fill_opacity
    return c


# ===========================================================================
# Fill conversion
# ===========================================================================


def _convert_fills(raw_fills: List[Dict[str, Any]]) -> List[Any]:
    """Convert a Pencil fills array to a list of UNFill objects."""
    result = []
    for fill in raw_fills:
        if not fill.get("visible", True):
            continue
        ftype = fill.get("type", "SOLID").upper()
        opacity = float(fill.get("opacity", 1.0))

        if ftype in ("SOLID", "COLOR"):
            color = _color_with_opacity(fill.get("color") or fill.get("value"), opacity)
            if color:
                result.append(UNSolidFill(color=color, enabled=True))

        elif ftype in ("LINEAR_GRADIENT", "LINEAR"):
            stops = _convert_gradient_stops(fill.get("stops", []))
            angle = float(fill.get("angle", fill.get("rotation", 180.0)))
            result.append(
                UNGradientFill(
                    gradient_type=GradientType.LINEAR,
                    rotation=angle,
                    stops=stops,
                    opacity=opacity,
                    enabled=True,
                )
            )

        elif ftype in ("RADIAL_GRADIENT", "RADIAL"):
            stops = _convert_gradient_stops(fill.get("stops", []))
            result.append(
                UNGradientFill(
                    gradient_type=GradientType.RADIAL,
                    rotation=0.0,
                    stops=stops,
                    opacity=opacity,
                    enabled=True,
                )
            )

        elif ftype in ("ANGULAR_GRADIENT", "ANGULAR"):
            stops = _convert_gradient_stops(fill.get("stops", []))
            result.append(
                UNGradientFill(
                    gradient_type=GradientType.ANGULAR,
                    rotation=float(fill.get("angle", 0.0)),
                    stops=stops,
                    opacity=opacity,
                    enabled=True,
                )
            )

        elif ftype in ("IMAGE", "IMAGE_FILL"):
            url = fill.get("url") or fill.get("imageUrl") or fill.get("src", "")
            mode_str = (
                fill.get("mode")
                or fill.get("imageMode")
                or fill.get("scaleMode", "fill")
            )
            mode = _IMG_MODE_MAP.get(mode_str, ImageFillMode.FILL)
            result.append(
                UNImageFill(url=url, mode=mode, opacity=opacity, enabled=True)
            )

    return result


def _convert_gradient_stops(raw_stops: List[Dict[str, Any]]) -> List[UNGradientStop]:
    """Convert raw Pencil gradient stops to UNGradientStop list."""
    stops: List[UNGradientStop] = []
    for s in raw_stops:
        color = _parse_color(s.get("color") or s.get("value"))
        if color is None:
            continue
        # Apply per-stop opacity if present
        stop_opacity = float(s.get("opacity", 1.0))
        color.a = color.a * stop_opacity
        position = float(s.get("position", s.get("offset", 0.0)))
        stops.append(UNGradientStop(color=color, position=position))
    return stops


# ===========================================================================
# Stroke conversion
# ===========================================================================


def _convert_strokes(raw_strokes: List[Dict[str, Any]]) -> List[UNStroke]:
    """Convert Pencil strokes array to UNStroke list."""
    result: List[UNStroke] = []
    for s in raw_strokes:
        if not s.get("visible", True):
            continue

        color = _color_with_opacity(
            s.get("color") or s.get("value"),
            float(s.get("opacity", 1.0)),
        )
        if color is None:
            continue

        width = float(s.get("width") or s.get("strokeWidth") or s.get("weight", 1.0))
        align_str = s.get("align") or s.get("position") or "center"
        align = _STROKE_ALIGN_MAP.get(align_str, StrokeAlign.CENTER)
        cap = s.get("cap") or s.get("lineCap") or "none"
        join = s.get("join") or s.get("lineJoin") or "miter"
        dash = s.get("dashPattern") or s.get("dashes") or []

        result.append(
            UNStroke(
                fill=UNSolidFill(color=color),
                thickness=UNStrokeThickness.uniform(width),
                align=align,
                cap=cap,
                join=join,
                dash_pattern=[float(d) for d in dash],
                enabled=True,
            )
        )
    return result


# ===========================================================================
# Effect conversion
# ===========================================================================


def _convert_effects(raw_effects: List[Dict[str, Any]]) -> List[Any]:
    """Convert Pencil effects array to UNEffect list."""
    result = []
    for e in raw_effects:
        if not e.get("visible", True):
            continue
        etype = (e.get("type") or "").upper()

        if etype in ("DROP_SHADOW", "DROPSHADOW"):
            color = _parse_color(e.get("color")) or UNColor(r=0, g=0, b=0, a=0.25)
            result.append(
                UNDropShadow(
                    color=color,
                    offset_x=float(e.get("offsetX", e.get("x", 0.0))),
                    offset_y=float(e.get("offsetY", e.get("y", 4.0))),
                    blur=float(e.get("blur", e.get("radius", 8.0))),
                    spread=float(e.get("spread", 0.0)),
                    inner=False,
                    enabled=True,
                )
            )

        elif etype in ("INNER_SHADOW", "INNERSHADOW"):
            color = _parse_color(e.get("color")) or UNColor(r=0, g=0, b=0, a=0.25)
            result.append(
                UNDropShadow(
                    color=color,
                    offset_x=float(e.get("offsetX", e.get("x", 0.0))),
                    offset_y=float(e.get("offsetY", e.get("y", 4.0))),
                    blur=float(e.get("blur", e.get("radius", 8.0))),
                    spread=float(e.get("spread", 0.0)),
                    inner=True,
                    enabled=True,
                )
            )

        elif etype in ("LAYER_BLUR", "GAUSSIAN_BLUR", "BLUR"):
            result.append(
                UNBlur(
                    radius=float(e.get("radius", e.get("blur", 4.0))),
                    background=False,
                    enabled=True,
                )
            )

        elif etype in ("BACKGROUND_BLUR", "BACKDROP_BLUR"):
            result.append(
                UNBlur(
                    radius=float(e.get("radius", e.get("blur", 4.0))),
                    background=True,
                    enabled=True,
                )
            )

    return result


# ===========================================================================
# Layout / sizing conversion
# ===========================================================================


def _convert_layout(raw: Dict[str, Any], node: UNNode) -> None:
    """
    Read Pencil auto-layout fields and set them on `node`.

    Pencil may encode layout in several ways:
      - Top-level "layout" field:  "FLEX" | "NONE" | "AUTO"
      - "layoutMode" field:        "HORIZONTAL" | "VERTICAL" | "NONE"
      - Legacy style dict with "display": "flex"
    """
    layout_str = (
        raw.get("layout") or raw.get("layoutMode") or raw.get("layoutType") or "NONE"
    )
    layout_str = str(layout_str).upper()

    # Interpret shorthand direction values
    if layout_str in ("HORIZONTAL", "ROW"):
        node.layout = LayoutMode.HORIZONTAL
    elif layout_str in ("VERTICAL", "COLUMN"):
        node.layout = LayoutMode.VERTICAL
    elif layout_str in ("FLEX", "AUTO", "AUTO_LAYOUT"):
        direction = raw.get("layoutDirection") or raw.get("flexDirection") or "VERTICAL"
        node.layout = _LAYOUT_DIR_MAP.get(str(direction).upper(), LayoutMode.VERTICAL)
    else:
        node.layout = LayoutMode.NONE
        return

    # Gap
    node.gap = float(
        raw.get("gap") or raw.get("itemSpacing") or raw.get("layoutGap") or 0.0
    )

    # Padding
    pad_raw = raw.get("padding")
    if isinstance(pad_raw, list) and len(pad_raw) >= 4:
        node.padding = UNPadding(
            top=float(pad_raw[0]),
            right=float(pad_raw[1]),
            bottom=float(pad_raw[2]),
            left=float(pad_raw[3]),
        )
    elif isinstance(pad_raw, list) and len(pad_raw) == 1:
        p = float(pad_raw[0])
        node.padding = UNPadding(top=p, right=p, bottom=p, left=p)
    elif isinstance(pad_raw, (int, float)):
        p = float(pad_raw)
        node.padding = UNPadding(top=p, right=p, bottom=p, left=p)
    elif isinstance(pad_raw, dict):
        node.padding = UNPadding(
            top=float(pad_raw.get("top", 0)),
            right=float(pad_raw.get("right", 0)),
            bottom=float(pad_raw.get("bottom", 0)),
            left=float(pad_raw.get("left", 0)),
        )
    else:
        # Try individual padding fields
        pt = float(raw.get("paddingTop", raw.get("padding_top", 0)))
        pr = float(raw.get("paddingRight", raw.get("padding_right", 0)))
        pb = float(raw.get("paddingBottom", raw.get("padding_bottom", 0)))
        pl = float(raw.get("paddingLeft", raw.get("padding_left", 0)))
        node.padding = UNPadding(top=pt, right=pr, bottom=pb, left=pl)

    # Justify / align
    node.justify_content = _JUSTIFY_MAP.get(
        str(raw.get("justifyContent", raw.get("primaryAxisAlignItems", "start"))),
        JustifyContent.START,
    )
    node.align_items = _ALIGN_MAP.get(
        str(raw.get("alignItems", raw.get("counterAxisAlignItems", "start"))),
        AlignItems.START,
    )


def _convert_sizing(raw: Dict[str, Any], node: UNNode) -> None:
    """
    Map Pencil sizing mode fields to UNSize.

    Pencil may use:
      - "widthMode":  "FIXED" | "HUG" | "FILL"
      - "heightMode": "FIXED" | "HUG" | "FILL"
      - Or Figma-style "primaryAxisSizingMode" / "counterAxisSizingMode"
    """
    w_mode_str = raw.get("widthMode") or raw.get("widthSizing") or "FIXED"
    h_mode_str = raw.get("heightMode") or raw.get("heightSizing") or "FIXED"

    w = float(raw.get("width", 0.0))
    h = float(raw.get("height", 0.0))

    if str(w_mode_str).upper() == "HUG":
        node.width = UNSize.hug()
    elif str(w_mode_str).upper() == "FILL":
        node.width = UNSize.fill()
    else:
        node.width = UNSize.fixed(w)

    if str(h_mode_str).upper() == "HUG":
        node.height = UNSize.hug()
    elif str(h_mode_str).upper() == "FILL":
        node.height = UNSize.fill()
    else:
        node.height = UNSize.fixed(h)


def _convert_corner_radius(raw: Dict[str, Any]) -> UNCornerRadius:
    """Convert Pencil corner radius fields to UNCornerRadius."""
    # Uniform radius
    uniform = raw.get("cornerRadius") or raw.get("borderRadius")
    if uniform is not None:
        try:
            r = float(uniform)
            return UNCornerRadius.all(r)
        except (ValueError, TypeError):
            pass

    # Per-corner radii
    tl = float(
        raw.get("cornerRadiusTL")
        or raw.get("topLeftRadius")
        or raw.get("borderTopLeftRadius")
        or 0.0
    )
    tr = float(
        raw.get("cornerRadiusTR")
        or raw.get("topRightRadius")
        or raw.get("borderTopRightRadius")
        or 0.0
    )
    br = float(
        raw.get("cornerRadiusBR")
        or raw.get("bottomRightRadius")
        or raw.get("borderBottomRightRadius")
        or 0.0
    )
    bl = float(
        raw.get("cornerRadiusBL")
        or raw.get("bottomLeftRadius")
        or raw.get("borderBottomLeftRadius")
        or 0.0
    )

    # Also check array form: [tl, tr, br, bl]
    corners_arr = raw.get("cornerRadii") or raw.get("radii")
    if isinstance(corners_arr, list) and len(corners_arr) >= 4:
        tl, tr, br, bl = (float(v) for v in corners_arr[:4])

    return UNCornerRadius(tl=tl, tr=tr, br=br, bl=bl)


# ===========================================================================
# Text style conversion
# ===========================================================================


def _convert_text_style(raw: Dict[str, Any]) -> UNTextStyle:
    """
    Convert Pencil text node fields into a UNTextStyle.

    Pencil may store typography at the node level (for simple text)
    or inside a "textStyle" sub-dict.
    """
    ts = raw.get("textStyle") or raw.get("style") or {}

    # Merge node-level typography fields with textStyle sub-dict
    # (node-level takes precedence for overrides)
    merged: Dict[str, Any] = {}
    if isinstance(ts, dict):
        merged.update(ts)
    merged.update(
        {
            k: v
            for k, v in raw.items()
            if k
            in (
                "fontFamily",
                "fontSize",
                "fontWeight",
                "fontStyle",
                "lineHeight",
                "letterSpacing",
                "textAlign",
                "textTransform",
                "textDecoration",
            )
        }
    )

    # Font family
    font_family = (
        merged.get("fontFamily")
        or merged.get("font_family")
        or merged.get("font")
        or "Inter"
    )
    if isinstance(font_family, str):
        font_family = font_family.split(",")[0].strip().strip("'\"")

    # Font size
    font_size = float(merged.get("fontSize") or merged.get("font_size") or 14.0)

    # Font weight — may come as string name or numeric
    raw_weight = merged.get("fontWeight") or merged.get("font_weight") or "400"
    font_weight = _WEIGHT_ALIASES.get(str(raw_weight), str(raw_weight))
    # If it's still a float string like "700.0", clean it up
    try:
        font_weight = str(int(float(font_weight)))
    except (ValueError, TypeError):
        font_weight = "400"

    # Font style
    font_style_raw = merged.get("fontStyle") or merged.get("font_style") or "normal"
    font_style = "italic" if "italic" in str(font_style_raw).lower() else "normal"

    # Line height
    lh_raw = merged.get("lineHeight") or merged.get("line_height")
    line_height: Optional[float] = None
    if lh_raw is not None and lh_raw != "normal":
        try:
            lh = float(lh_raw)
            # If line height < 10, treat as multiplier
            if lh < 10:
                line_height = lh * font_size
            else:
                line_height = lh
        except (ValueError, TypeError):
            line_height = None

    # Letter spacing
    letter_spacing = float(
        merged.get("letterSpacing") or merged.get("letter_spacing") or 0.0
    )

    # Text align
    text_align = _TEXT_ALIGN_MAP.get(
        str(merged.get("textAlign") or merged.get("text_align") or "left"),
        TextAlign.LEFT,
    )

    # Text transform
    text_transform = _TEXT_TRANSFORM_MAP.get(
        str(merged.get("textTransform") or merged.get("text_transform") or "none"),
        TextTransform.NONE,
    )

    # Text decoration
    text_decoration = str(
        merged.get("textDecoration") or merged.get("text_decoration") or "none"
    )

    # Auto resize — default to WIDTH_HEIGHT (hug) for text nodes
    auto_resize = TextAutoResize.WIDTH_HEIGHT

    return UNTextStyle(
        font_family=font_family,
        font_size=font_size,
        font_weight=font_weight,
        font_style=font_style,
        line_height=line_height,
        letter_spacing=letter_spacing,
        text_align=text_align,
        text_transform=text_transform,
        text_decoration=text_decoration,
        text_auto_resize=auto_resize,
    )


# ===========================================================================
# Main node converter
# ===========================================================================


def _pencil_node_to_un(raw: Dict[str, Any], depth: int = 0) -> Optional[UNNode]:
    """
    Convert one Pencil node dict (and its subtree) into a UNNode.

    Parameters
    ----------
    raw   : Pencil node dict as returned by get_node() / get_page()
    depth : Current recursion depth (for debugging)

    Returns
    -------
    UNNode, or None if the node type is unrecognised / should be skipped.
    """
    if not raw or not isinstance(raw, dict):
        return None

    raw_type = str(raw.get("type", "FRAME")).upper()
    node_type = _NODE_TYPE_MAP.get(raw_type, NodeType.FRAME)

    node_id = str(raw.get("id", ""))
    node_name = str(raw.get("name", raw_type.lower()))
    x = float(raw.get("x", 0.0))
    y = float(raw.get("y", 0.0))
    opacity = float(raw.get("opacity", 1.0))
    visible = bool(raw.get("visible", True))
    rotation = float(raw.get("rotation", 0.0))
    blend_raw = str(raw.get("blendMode", raw.get("blend_mode", "NORMAL"))).upper()
    blend = _BLEND_MAP.get(blend_raw, BlendMode.NORMAL)

    # ── Size ──────────────────────────────────────────────────────────────
    width_val = float(raw.get("width", 0.0))
    height_val = float(raw.get("height", 0.0))
    width = UNSize.fixed(width_val)
    height = UNSize.fixed(height_val)

    # ── Corner radius ─────────────────────────────────────────────────────
    corner_radius = _convert_corner_radius(raw)

    # ── Fills / strokes / effects ─────────────────────────────────────────
    raw_fills = raw.get("fills", raw.get("fill", []))
    raw_strokes = raw.get("strokes", raw.get("stroke", []))
    raw_effects = raw.get("effects", raw.get("effect", []))

    if not isinstance(raw_fills, list):
        raw_fills = [raw_fills] if raw_fills else []
    if not isinstance(raw_strokes, list):
        raw_strokes = [raw_strokes] if raw_strokes else []
    if not isinstance(raw_effects, list):
        raw_effects = [raw_effects] if raw_effects else []

    fills = _convert_fills(raw_fills)
    strokes = _convert_strokes(raw_strokes)
    effects = _convert_effects(raw_effects)

    # Convenience: backgroundColor shorthand → solid fill
    bg_color = raw.get("backgroundColor") or raw.get("background_color")
    if bg_color and not fills:
        c = _parse_color(bg_color)
        if c:
            fills.append(UNSolidFill(color=c))

    # ── Build the base node ───────────────────────────────────────────────
    node = UNNode(
        type=node_type,
        id=node_id,
        name=node_name,
        x=x,
        y=y,
        width=width,
        height=height,
        fills=fills,
        strokes=strokes,
        effects=effects,
        opacity=opacity,
        visible=visible,
        rotation=rotation,
        blend_mode=blend,
        corner_radius=corner_radius,
        clip_content=bool(raw.get("clipContent", raw.get("clip_content", False))),
        source_tool="pencil",
        source_id=node_id,
    )

    # ── Sizing mode overrides ─────────────────────────────────────────────
    _convert_sizing(raw, node)

    # ── Type-specific fields ──────────────────────────────────────────────

    if node_type == NodeType.TEXT:
        node.text_content = str(
            raw.get("content") or raw.get("text") or raw.get("characters") or ""
        )
        node.text_style = _convert_text_style(raw)
        # Text color: first fill if solid, or from "color" field
        if not node.fills:
            color_raw = raw.get("color") or raw.get("textColor") or raw.get("fontColor")
            if color_raw:
                c = _parse_color(color_raw)
                if c:
                    node.fills.append(UNSolidFill(color=c))

    elif node_type == NodeType.PATH:
        node.geometry = str(
            raw.get("pathData") or raw.get("d") or raw.get("geometry") or ""
        )
        node.fill_rule = str(
            raw.get("fillRule") or raw.get("fill_rule") or "nonzero"
        ).lower()

    elif node_type == NodeType.ELLIPSE:
        node.inner_radius = float(raw.get("innerRadius", raw.get("inner_radius", 0.0)))
        node.start_angle = float(raw.get("startAngle", raw.get("start_angle", 0.0)))
        node.sweep_angle = float(raw.get("sweepAngle", raw.get("sweep_angle", 360.0)))

    elif node_type == NodeType.IMAGE:
        node.image_url = str(
            raw.get("imageUrl") or raw.get("src") or raw.get("url") or ""
        )
        mode_raw = str(raw.get("imageMode") or raw.get("mode") or "fill")
        node.image_mode = _IMG_MODE_MAP.get(mode_raw, ImageFillMode.FILL)

    elif node_type == NodeType.INSTANCE:
        node.component_id = str(raw.get("componentId") or raw.get("component_id") or "")
        node.component_props = dict(
            raw.get("componentProperties") or raw.get("props") or {}
        )

    # ── Auto-layout (frames only) ─────────────────────────────────────────
    if node_type in (NodeType.FRAME, NodeType.COMPONENT, NodeType.INSTANCE):
        _convert_layout(raw, node)

    # ── Children ──────────────────────────────────────────────────────────
    raw_children = raw.get("children") or raw.get("nodes") or []
    for child_raw in raw_children:
        child_node = _pencil_node_to_un(child_raw, depth=depth + 1)
        if child_node is not None:
            node.children.append(child_node)

    return node


# ===========================================================================
# Style variable helpers
# ===========================================================================


def _build_style_index(styles: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Build a lookup index from the raw get_styles() response.

    Pencil's get_styles() may return a dict with top-level keys like:
      "colors", "typography", "effects", "grids" — each being a list or dict
      of named style variables.

    Also handles flat dicts where each key is a variable name mapping to a
    style definition dict with at least an "id" field.

    Returns a mapping:
        { variable_name: { "id": str, "property": str, ... } }
    """
    index: Dict[str, Dict[str, str]] = {}

    if not isinstance(styles, dict):
        return index

    # Flat format: {"--primary": {"id": "var-1", "value": "#ff0000"}, ...}
    # Detect by checking if values are dicts with "id" or "value" keys.
    if styles and all(isinstance(v, dict) for v in styles.values()):
        for name, defn in styles.items():
            if isinstance(defn, dict):
                var_id = str(defn.get("id") or name)
                index[name] = {"id": var_id, "name": name}
        return index

    # Grouped format: {"colors": [...], "typography": [...], ...}
    _property_map = {
        "colors": "fill",
        "color": "fill",
        "typography": "fontSize",
        "text": "fontSize",
        "effects": "effect",
        "grids": "grid",
    }

    for group_key, items in styles.items():
        prop = _property_map.get(group_key.lower(), group_key)

        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or item.get("variable") or "")
                var_id = str(item.get("id") or name)
                if name:
                    index[name] = {"id": var_id, "name": name, "property": prop}

        elif isinstance(items, dict):
            for name, item in items.items():
                if isinstance(item, dict):
                    var_id = str(item.get("id") or name)
                    index[name] = {"id": var_id, "name": name, "property": prop}
                else:
                    index[name] = {"id": name, "name": name, "property": prop}

    return index


def _apply_style_bindings(node: UNNode, raw: Dict[str, Any],
                           style_index: Dict[str, Dict[str, str]]) -> None:
    """
    Look for variable references in the raw Pencil node and create
    UNVariableBinding entries on the UNNode for any matched styles.

    Pencil may encode variable references in raw node data as:
      - "variableBindings": {"fill": "colors/brand/primary", ...}
      - "boundVariables": {"fills": [{"id": "var-id", "name": "--primary"}], ...}
      - "styleId": str  (a reference to a named style)
      - "fillStyleId" / "strokeStyleId" / "textStyleId"
    """
    if not style_index and not raw.get("variableBindings") and not raw.get("boundVariables"):
        return

    # Format 1: explicit variableBindings map {"property": "variable-name"}
    vb_map = raw.get("variableBindings") or {}
    if isinstance(vb_map, dict):
        for prop, var_name in vb_map.items():
            if isinstance(var_name, str) and var_name:
                info = style_index.get(var_name, {})
                node.variable_bindings[prop] = UNVariableBinding(
                    property=prop,
                    variable=var_name,
                    tool_id=info.get("id") or var_name,
                )

    # Format 2: boundVariables (Figma-style) {"fills": [{"id": ..., "name": ...}]}
    bv_map = raw.get("boundVariables") or {}
    if isinstance(bv_map, dict):
        for prop, refs in bv_map.items():
            if isinstance(refs, list) and refs:
                ref = refs[0]  # Take first binding per property
                if isinstance(ref, dict):
                    var_name = str(ref.get("name") or ref.get("id") or "")
                    var_id = str(ref.get("id") or var_name)
                    if var_name and prop not in node.variable_bindings:
                        node.variable_bindings[prop] = UNVariableBinding(
                            property=prop,
                            variable=var_name,
                            tool_id=var_id,
                        )
            elif isinstance(refs, dict):
                var_name = str(refs.get("name") or refs.get("id") or "")
                var_id = str(refs.get("id") or var_name)
                if var_name and prop not in node.variable_bindings:
                    node.variable_bindings[prop] = UNVariableBinding(
                        property=prop,
                        variable=var_name,
                        tool_id=var_id,
                    )

    # Format 3: styleId fields — map to the style index by ID
    _style_id_props = {
        "fillStyleId": "fill",
        "strokeStyleId": "stroke",
        "textStyleId": "fontSize",
        "effectStyleId": "effect",
        "styleId": "fill",
    }
    for raw_key, prop in _style_id_props.items():
        style_id = raw.get(raw_key)
        if not style_id or not isinstance(style_id, str):
            continue
        # Look up in index by ID
        matched_name = style_id
        for name, info in style_index.items():
            if info.get("id") == style_id:
                matched_name = name
                break
        if prop not in node.variable_bindings:
            node.variable_bindings[prop] = UNVariableBinding(
                property=prop,
                variable=matched_name,
                tool_id=style_id,
            )


def _pencil_node_to_un_with_styles(
    raw: Dict[str, Any],
    style_index: Dict[str, Dict[str, str]],
    depth: int = 0,
) -> Optional[UNNode]:
    """
    Convert one Pencil node dict into a UNNode, also mapping style variable
    bindings from the style_index.  Wraps _pencil_node_to_un.
    """
    node = _pencil_node_to_un(raw, depth=depth)
    if node is None:
        return None
    _apply_style_bindings(node, raw, style_index)

    # Recurse into children and apply bindings there too
    raw_children = raw.get("children") or raw.get("nodes") or []
    # The children were already converted by _pencil_node_to_un; we need to
    # re-apply bindings to those child UNNodes using the raw child data.
    for i, child_raw in enumerate(raw_children):
        if i < len(node.children) and isinstance(child_raw, dict):
            _apply_style_bindings(node.children[i], child_raw, style_index)
            # Deep recursion: apply to grandchildren by calling this function
            # on the child raw and merging variable_bindings back
            child_with_bindings = _pencil_node_to_un_with_styles(
                child_raw, style_index, depth=depth + 1
            )
            if child_with_bindings is not None:
                node.children[i] = child_with_bindings

    return node


# ===========================================================================
# PencilReader — BaseReader implementation
# ===========================================================================


class PencilReader(BaseReader):
    """
    Read a Pencil.dev artboard (or any node) and return a UNNode tree.

    Parameters
    ----------
    host        : Pencil MCP server host (default '127.0.0.1')
    port        : Pencil MCP server port.  Pass None to auto-detect.
    auto_detect : Whether to auto-detect port when port=None.

    Example
    -------
    ::

        with PencilReader() as reader:
            boards = reader.list_nodes()
            tree   = reader.read_node(boards[0]["id"])

        # Non-context-manager usage
        reader = PencilReader(port=19002)
        reader.connect()
        tree = reader.read_node("artboard-abc")
        reader.disconnect()
    """

    tool_name = "pencil"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: Optional[int] = None,
        auto_detect: bool = True,
    ) -> None:
        self._client = PencilClient(host=host, port=port, auto_detect=auto_detect)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._client.connect()

    def disconnect(self) -> None:
        self._client.disconnect()

    # ── BaseReader interface ───────────────────────────────────────────────

    def _fetch_style_index(self) -> Dict[str, Dict[str, str]]:
        """
        Fetch the style/variable library from Pencil and build a lookup index.
        Returns an empty dict if the call fails or returns nothing.
        """
        try:
            styles = self._client.get_styles()
            if styles:
                index = _build_style_index(styles)
                log.debug(
                    "PencilReader: loaded %d style variables from get_styles()",
                    len(index),
                )
                return index
        except Exception as exc:
            log.debug("PencilReader: get_styles() unavailable: %s", exc)
        return {}

    def read_node(self, node_id: str) -> UNNode:
        """
        Read the node identified by ``node_id`` from Pencil, convert it to
        a UNNode tree, and return the root node.

        Parameters
        ----------
        node_id : str
            Pencil node ID (artboard, frame, or any other node).

        Returns
        -------
        UNNode — root of the converted subtree.

        Raises
        ------
        NodeNotFoundError     if the node does not exist.
        PencilConnectionError if the Pencil MCP server is unreachable.
        """
        # Fetch the style/variable library so we can map variable bindings
        style_index = self._fetch_style_index()

        try:
            raw = self._client.get_node(node_id)
        except PencilToolError as exc:
            if "not found" in str(exc).lower() or exc.code == 404:
                raise NodeNotFoundError(node_id, tool="pencil") from exc
            raise

        if not raw:
            raise NodeNotFoundError(node_id, tool="pencil")

        log.debug(
            "PencilReader.read_node: converting node '%s' (type=%s, children=%d)",
            node_id,
            raw.get("type", "?"),
            len(raw.get("children", [])),
        )

        node = _pencil_node_to_un_with_styles(raw, style_index)
        if node is None:
            raise ValueError(
                f"Failed to convert Pencil node '{node_id}' to UNNode. "
                f"Raw type: {raw.get('type', 'unknown')}"
            )

        return node

    def read_page(self, page_id: str = "") -> UNNode:
        """
        Read an entire Pencil page (all artboards and layers).

        Parameters
        ----------
        page_id : str
            Page ID.  Empty string reads the currently active page.

        Returns
        -------
        UNNode of type FRAME representing the page root.
        """
        # Fetch the style/variable library so we can map variable bindings
        style_index = self._fetch_style_index()

        raw = self._client.get_page(page_id)
        if not raw:
            raise ValueError(f"Pencil returned empty page for id='{page_id}'")
        node = _pencil_node_to_un_with_styles(raw, style_index)
        if node is None:
            raise ValueError("Failed to convert Pencil page to UNNode.")
        return node

    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        Return a list of top-level artboards in the current Pencil file.
        Each item: {"id": str, "name": str, "type": "artboard",
                    "width": float, "height": float}
        """
        try:
            boards = self._client.list_artboards()
            return [
                {
                    "id": b.get("id", ""),
                    "name": b.get("name", ""),
                    "type": "artboard",
                    "width": float(b.get("width", 0)),
                    "height": float(b.get("height", 0)),
                }
                for b in boards
            ]
        except Exception as exc:
            log.warning("PencilReader.list_nodes failed: %s", exc)
            return []

    def get_file_info(self) -> Dict[str, Any]:
        """Return metadata about the currently open Pencil file."""
        try:
            return self._client.get_file_info()
        except Exception:
            return {}

    def screenshot(self, node_id: str, scale: float = 1.0) -> Optional[bytes]:
        """Export a PNG screenshot of the given node via the Pencil MCP."""
        return self._client.export_node(node_id, format="png", scale=scale)

    # ── Convenience helpers ────────────────────────────────────────────────

    def read_artboard_by_name(self, name: str) -> UNNode:
        """
        Find an artboard by display name and read it.
        Raises NodeNotFoundError if no artboard with that name is found.
        """
        ab = self._client.get_artboard_by_name(name)
        if not ab:
            raise NodeNotFoundError(name, tool="pencil")
        return self.read_node(ab["id"])

    def __repr__(self) -> str:
        return f"<PencilReader client={self._client!r}>"
