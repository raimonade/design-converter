"""
FigmaWriter — UNNode → Figma Plugin API JavaScript

Why JavaScript (not REST API)
-------------------------------
Figma's REST API is **read-only** for design nodes. You can read files and
post comments/variables via REST, but creating or mutating FRAME / TEXT /
RECTANGLE / etc. nodes requires the Figma Plugin API — JavaScript that runs
inside Figma's plugin sandbox.

Two modes
---------
mode="script" (default)
    Emit a self-contained IIFE .js file the user pastes into
    Figma ▶ Plugins ▶ Development ▶ Open Console (Cmd+Opt+I).
    write_node() returns the absolute path to the saved .js file.

mode="bridge"
    Start a minimal RFC 6455 WebSocket SERVER on `bridge_port` (default 9224).
    The Desktop Bridge Figma plugin must be configured to connect to that port.
    write_node() returns the created node-ID string from the plugin response.

Field mapping: UNNode → Figma Plugin API
-----------------------------------------
    node.width.value / node.height.value  →  resize(w, h)
    node.width.mode / node.height.mode    →  primaryAxisSizingMode / counterAxisSizingMode
    node.layout                           →  layoutMode  (not node.layout_mode)
    node.gap                              →  itemSpacing  (not node.item_spacing)
    node.geometry                         →  SVG path     (not node.svg_data)
    node.locked                           →  locked
    node.text_runs                        →  setRange* API for rich text
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import socket
import struct
import sys
import textwrap
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_THIS_DIR = Path(__file__).resolve().parent
_SVC_ROOT = _THIS_DIR
while _SVC_ROOT.name != "design-converter" and _SVC_ROOT.parent != _SVC_ROOT:
    _SVC_ROOT = _SVC_ROOT.parent
if str(_SVC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SVC_ROOT))

from adapters.base import BaseWriter
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
    UNDropShadow,
    UNGradientFill,
    UNImageFill,
    UNNode,
    UNSolidFill,
    UNStroke,
    UNStrokeThickness,
    UNTextRun,
    UNTextStyle,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _rgba(c: "UNColor") -> str:
    """Format a UNColor as a Figma Plugin API colour object {r,g,b,a} with 0-1 channels."""
    r = max(0.0, min(1.0, c.r))
    g = max(0.0, min(1.0, c.g))
    b = max(0.0, min(1.0, c.b))
    a = max(0.0, min(1.0, c.a))
    return f"{{r:{r:.4f},g:{g:.4f},b:{b:.4f},a:{a:.4f}}}"


def _js_bool(v: bool) -> str:
    return "true" if v else "false"


def _blend_mode(bm: Optional[BlendMode]) -> str:
    _MAP = {
        BlendMode.NORMAL: "NORMAL",
        BlendMode.MULTIPLY: "MULTIPLY",
        BlendMode.SCREEN: "SCREEN",
        BlendMode.OVERLAY: "OVERLAY",
        BlendMode.DARKEN: "DARKEN",
        BlendMode.LIGHTEN: "LIGHTEN",
        BlendMode.DODGE: "COLOR_DODGE",
        BlendMode.BURN: "COLOR_BURN",
        BlendMode.HARD_LIGHT: "HARD_LIGHT",
        BlendMode.SOFT_LIGHT: "SOFT_LIGHT",
        BlendMode.DIFFERENCE: "DIFFERENCE",
        BlendMode.EXCLUSION: "EXCLUSION",
        BlendMode.HUE: "HUE",
        BlendMode.SATURATION: "SATURATION",
        BlendMode.COLOR: "COLOR",
        BlendMode.LUMINOSITY: "LUMINOSITY",
    }
    return _MAP.get(bm, "NORMAL") if bm else "NORMAL"


def _gradient_transform(rotation: float) -> str:
    """CSS rotation angle (degrees) → Figma 2×3 gradient transform matrix."""
    rad = math.radians(rotation % 360)
    s = math.sin(rad)
    c = math.cos(rad)
    a, b, cc = s, -c, (1 - s + c) / 2
    d, e, f = c, s, (1 - c - s) / 2
    return (
        f"[[{a:.6f},{b:.6f},{cc:.6f}],"
        f"[{d:.6f},{e:.6f},{f:.6f}]]"
    )


def _weight_to_style(weight: str, italic: bool = False) -> str:
    """Convert numeric font weight to Figma style name string."""
    _MAP = {
        "100": "Thin", "200": "ExtraLight", "300": "Light",
        "400": "Regular", "500": "Medium", "600": "SemiBold",
        "700": "Bold", "800": "ExtraBold", "900": "Black",
    }
    name = _MAP.get(str(weight), "Regular")
    return f"{name} Italic" if italic else name


# ---------------------------------------------------------------------------
# _FigmaCodeEmitter — UNNode tree → Figma Plugin API IIFE JavaScript
# ---------------------------------------------------------------------------

class _FigmaCodeEmitter:

    def __init__(
        self,
        root: UNNode,
        parent_id: str = "",
        replace_id: str = "",
    ) -> None:
        self._root = root
        self._parent_id = parent_id
        self._replace_id = replace_id
        self._lines: List[str] = []
        self._counter = 0
        # (family, style) → needs loadFontAsync
        self._fonts: Set[Tuple[str, str]] = set()

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def emit(self) -> str:
        self._collect_fonts(self._root)

        L = self._lines
        L.append("(async () => { try {")

        for family, style in sorted(self._fonts):
            L.append(
                f'  await figma.loadFontAsync({{family:{json.dumps(family)},'
                f'style:{json.dumps(style)}}});'
            )

        if self._parent_id:
            L.append(
                f'  const _par = figma.getNodeById({json.dumps(self._parent_id)})'
                f' || figma.currentPage;'
            )
        else:
            L.append("  const _par = figma.currentPage;")

        if self._replace_id:
            L.append(
                f'  const _old = figma.getNodeById({json.dumps(self._replace_id)});'
            )
            L.append("  if (_old) _old.remove();")

        root_var = self._emit_node(self._root, "_par")
        L.append(
            f'  return {{success:true,nodeId:{root_var}.id,'
            f'nodeName:{root_var}.name}};'
        )
        L.append("} catch(e) { return {success:false,error:String(e)}; }")
        L.append("})();")
        return "\n".join(L)

    # ------------------------------------------------------------------
    # font collection
    # ------------------------------------------------------------------

    def _collect_fonts(self, node: UNNode) -> None:
        if node.type == NodeType.TEXT and node.text_style:
            ts = node.text_style
            family = ts.font_family or "Inter"
            fn = ts.figma_font_name()
            self._fonts.add((family, fn["style"]))
        # Also collect fonts from text_runs
        for run in (node.text_runs or []):
            if run.font_family:
                italic = run.italic or False
                weight = run.font_weight or "400"
                style = _weight_to_style(weight, italic)
                self._fonts.add((run.font_family, style))
        for child in (node.children or []):
            self._collect_fonts(child)

    # ------------------------------------------------------------------
    # node dispatch
    # ------------------------------------------------------------------

    def _next_var(self) -> str:
        v = f"n{self._counter}"
        self._counter += 1
        return v

    def _emit_node(self, node: UNNode, parent_var: str) -> str:
        dispatch = {
            NodeType.FRAME: self._emit_frame,
            NodeType.COMPONENT: self._emit_component,
            NodeType.INSTANCE: self._emit_instance,
            NodeType.GROUP: self._emit_group,
            NodeType.TEXT: self._emit_text,
            NodeType.RECTANGLE: self._emit_rect,
            NodeType.ELLIPSE: self._emit_ellipse,
            NodeType.LINE: self._emit_line,
            NodeType.PATH: self._emit_path,
        }
        # IMAGE node: treat as a rectangle with image fill
        fn = dispatch.get(node.type, self._emit_frame)
        return fn(node, parent_var)

    # ------------------------------------------------------------------
    # node emitters
    # ------------------------------------------------------------------

    def _emit_frame(self, node: UNNode, parent_var: str) -> str:
        var = self._next_var()
        self._lines.append(f"  const {var} = figma.createFrame();")
        self._lines.append(f"  {parent_var}.appendChild({var});")
        self._set_name(var, node)
        self._set_common(var, node)
        self._set_layout(var, node)
        self._emit_children(node, var)
        return var

    def _emit_component(self, node: UNNode, parent_var: str) -> str:
        var = self._next_var()
        self._lines.append(f"  const {var} = figma.createComponent();")
        self._lines.append(f"  {parent_var}.appendChild({var});")
        self._set_name(var, node)
        self._set_common(var, node)
        self._set_layout(var, node)
        self._emit_children(node, var)
        return var

    def _emit_instance(self, node: UNNode, parent_var: str) -> str:
        if node.component_id:
            var = self._next_var()
            cid = json.dumps(node.component_id)
            self._lines.append(
                f"  const _comp_{var} = figma.getNodeById({cid});"
            )
            self._lines.append(
                f"  const {var} = _comp_{var} && _comp_{var}.type === 'COMPONENT'"
                f" ? _comp_{var}.createInstance() : figma.createFrame();"
            )
            self._lines.append(f"  {parent_var}.appendChild({var});")
            self._set_name(var, node)
            self._set_common(var, node)
            return var
        return self._emit_frame(node, parent_var)

    def _emit_group(self, node: UNNode, parent_var: str) -> str:
        children = node.children or []
        if not children:
            return self._emit_frame(node, parent_var)
        child_vars: List[str] = []
        # figma.group() requires that child nodes are NOT yet parented to
        # parent_var — add them to the current page first, then group.
        for child in children:
            cv = self._emit_node(child, "figma.currentPage")
            child_vars.append(cv)
        var = self._next_var()
        arr = "[" + ",".join(child_vars) + "]"
        self._lines.append(f"  const {var} = figma.group({arr}, {parent_var});")
        self._set_name(var, node)
        self._set_opacity(var, node)
        self._set_blend(var, node)
        self._set_visible(var, node)
        self._set_locked(var, node)
        return var

    def _emit_text(self, node: UNNode, parent_var: str) -> str:
        var = self._next_var()
        self._lines.append(f"  const {var} = figma.createText();")
        self._lines.append(f"  {parent_var}.appendChild({var});")
        self._set_name(var, node)
        self._set_position(var, node)
        self._set_opacity(var, node)
        self._set_blend(var, node)
        self._set_visible(var, node)
        self._set_locked(var, node)

        ts = node.text_style
        if ts:
            family = ts.font_family or "Inter"
            fn = ts.figma_font_name()
            self._lines.append(
                f'  {var}.fontName = {{family:{json.dumps(family)},'
                f'style:{json.dumps(fn["style"])}}};'
            )
            if ts.font_size:
                self._lines.append(f"  {var}.fontSize = {ts.font_size};")
            if ts.letter_spacing is not None and ts.letter_spacing != 0:
                self._lines.append(
                    f"  {var}.letterSpacing = {{value:{ts.letter_spacing},unit:'PIXELS'}};"
                )
            if ts.line_height is not None:
                self._lines.append(
                    f"  {var}.lineHeight = {{value:{ts.line_height},unit:'PIXELS'}};"
                )
            if ts.text_align:
                _ta = {
                    TextAlign.LEFT: "LEFT", TextAlign.CENTER: "CENTER",
                    TextAlign.RIGHT: "RIGHT", TextAlign.JUSTIFY: "JUSTIFIED",
                }
                self._lines.append(
                    f'  {var}.textAlignHorizontal = "{_ta.get(ts.text_align, "LEFT")}";'
                )
            if ts.text_transform and ts.text_transform != TextTransform.NONE:
                _tt = {
                    TextTransform.UPPERCASE: "UPPER",
                    TextTransform.LOWERCASE: "LOWER",
                    TextTransform.CAPITALIZE: "TITLE",
                }
                tt = _tt.get(ts.text_transform)
                if tt:
                    self._lines.append(f'  {var}.textCase = "{tt}";')
            td = getattr(ts, "text_decoration", "none") or "none"
            if td == "underline":
                self._lines.append(f'  {var}.textDecoration = "UNDERLINE";')
            elif td in ("line-through", "strikethrough"):
                self._lines.append(f'  {var}.textDecoration = "STRIKETHROUGH";')
            if ts.text_auto_resize:
                _ar = {
                    TextAutoResize.WIDTH_HEIGHT: "WIDTH_AND_HEIGHT",
                    TextAutoResize.HEIGHT: "HEIGHT",
                    TextAutoResize.NONE: "NONE",
                }
                ar = _ar.get(ts.text_auto_resize, "NONE")
                self._lines.append(f'  {var}.textAutoResize = "{ar}";')

        # Set characters AFTER font/size so Figma can validate.
        content = node.text_content or ""
        self._lines.append(f"  {var}.characters = {json.dumps(content)};")

        # Width/height (after textAutoResize).
        w = node.width.value if node.width else 100.0
        h = node.height.value if node.height else 100.0
        if ts and ts.text_auto_resize == TextAutoResize.NONE:
            # Fixed size: set both width and height
            self._lines.append(f"  {var}.resize({w},{h});")
        elif ts and ts.text_auto_resize == TextAutoResize.HEIGHT:
            # Only fix width; height auto-sizes to content
            self._lines.append(f"  {var}.resize({w},100);  // height auto-sized")
        # WIDTH_HEIGHT: don't resize at all, let Figma auto-size both
        elif not ts:
            # No text style — apply explicit size
            self._lines.append(f"  {var}.resize({w},{h});")

        # Fills for text color.
        if node.fills:
            self._lines.append(
                f"  {var}.fills = {self._render_fills(node.fills)};"
            )

        # Rich text runs — per-character style overrides.
        self._emit_text_runs(var, node)

        return var

    def _emit_rect(self, node: UNNode, parent_var: str) -> str:
        var = self._next_var()
        self._lines.append(f"  const {var} = figma.createRectangle();")
        self._lines.append(f"  {parent_var}.appendChild({var});")
        self._set_name(var, node)
        self._set_common(var, node)
        return var

    def _emit_ellipse(self, node: UNNode, parent_var: str) -> str:
        var = self._next_var()
        self._lines.append(f"  const {var} = figma.createEllipse();")
        self._lines.append(f"  {parent_var}.appendChild({var});")
        self._set_name(var, node)
        self._set_common(var, node)
        # Arc data for partial ellipses / donuts.
        if node.inner_radius > 0 or node.sweep_angle != 360:
            start_r = math.radians(node.start_angle)
            sweep_r = math.radians(node.sweep_angle)
            end_r = start_r + sweep_r
            self._lines.append(
                f"  {var}.arcData = {{"
                f"startingAngle:{start_r:.4f},"
                f"endingAngle:{end_r:.4f},"
                f"innerRadius:{node.inner_radius:.4f}}};"
            )
        return var

    def _emit_line(self, node: UNNode, parent_var: str) -> str:
        var = self._next_var()
        self._lines.append(f"  const {var} = figma.createLine();")
        self._lines.append(f"  {parent_var}.appendChild({var});")
        self._set_name(var, node)
        self._set_position(var, node)
        self._set_opacity(var, node)
        self._set_blend(var, node)
        self._set_visible(var, node)
        self._set_locked(var, node)
        self._set_rotation(var, node)
        self._set_strokes(var, node)
        w = node.width.value if node.width else 100.0
        self._lines.append(f"  {var}.resize({w},0);")
        return var

    def _emit_path(self, node: UNNode, parent_var: str) -> str:
        """Emit using SVG geometry (node.geometry) if available."""
        var = self._next_var()
        if node.geometry:
            # Wrap path data in an SVG for createNodeFromSvg.
            w = node.width.value if node.width else 100
            h = node.height.value if node.height else 100
            fill_color = "none"
            if node.fills:
                f0 = node.fills[0]
                if isinstance(f0, UNSolidFill):
                    fill_color = f0.color.to_hex()
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{w}" height="{h}">'
                f'<path d="{node.geometry}" fill="{fill_color}" '
                f'fill-rule="{node.fill_rule}"/>'
                f'</svg>'
            )
            self._lines.append(
                f"  const {var} = figma.createNodeFromSvg({json.dumps(svg)});"
            )
            self._lines.append(f"  {parent_var}.appendChild({var});")
        else:
            self._lines.append(f"  const {var} = figma.createVector();")
            self._lines.append(f"  {parent_var}.appendChild({var});")
            self._set_common(var, node)
        self._set_name(var, node)
        return var

    # ------------------------------------------------------------------
    # common property setters
    # ------------------------------------------------------------------

    def _set_name(self, var: str, node: UNNode) -> None:
        if node.name:
            self._lines.append(f"  {var}.name = {json.dumps(node.name)};")

    def _set_visible(self, var: str, node: UNNode) -> None:
        if node.visible is False:
            self._lines.append(f"  {var}.visible = false;")

    def _set_locked(self, var: str, node: UNNode) -> None:
        if node.locked:
            self._lines.append(f"  {var}.locked = true;")

    def _set_opacity(self, var: str, node: UNNode) -> None:
        if node.opacity is not None and node.opacity != 1.0:
            self._lines.append(f"  {var}.opacity = {node.opacity:.4f};")

    def _set_blend(self, var: str, node: UNNode) -> None:
        bm = _blend_mode(node.blend_mode)
        if bm != "NORMAL":
            self._lines.append(f'  {var}.blendMode = "{bm}";')

    def _set_position(self, var: str, node: UNNode) -> None:
        x = node.x or 0.0
        y = node.y or 0.0
        self._lines.append(f"  {var}.x = {x}; {var}.y = {y};")

    def _set_rotation(self, var: str, node: UNNode) -> None:
        if node.rotation:
            self._lines.append(f"  {var}.rotation = {node.rotation};")

    def _set_size(self, var: str, node: UNNode) -> None:
        """Resize using the concrete pixel values from UNSize."""
        w = node.width.value if node.width else 100.0
        h = node.height.value if node.height else 100.0
        self._lines.append(f"  {var}.resize({w},{h});")

    def _set_corner_radius(self, var: str, node: UNNode) -> None:
        if not node.corner_radius:
            return
        cr = node.corner_radius
        if cr.is_uniform():
            v = cr.value()
            if v:
                self._lines.append(f"  {var}.cornerRadius = {v};")
        else:
            tl = cr.top_left or 0
            tr = cr.top_right or 0
            br = cr.bottom_right or 0
            bl = cr.bottom_left or 0
            self._lines.append(
                f"  {var}.topLeftRadius = {tl}; {var}.topRightRadius = {tr};"
                f" {var}.bottomRightRadius = {br}; {var}.bottomLeftRadius = {bl};"
            )

    def _set_fills(self, var: str, node: UNNode) -> None:
        if node.fills is not None:
            self._lines.append(
                f"  {var}.fills = {self._render_fills(node.fills)};"
            )

    def _set_strokes(self, var: str, node: UNNode) -> None:
        if not node.strokes:
            return
        paints: List[str] = []
        for s in node.strokes:
            if isinstance(s.fill, UNSolidFill):
                paints.append(
                    f"{{type:'SOLID',color:{_rgba(s.fill.color)},"
                    f"opacity:{s.fill.color.a:.4f}}}"
                )
            else:
                paints.append("{type:'SOLID',color:{r:0,g:0,b:0,a:1},opacity:1}")
        self._lines.append(f"  {var}.strokes = [{','.join(paints)}];")

        s0 = node.strokes[0]
        thick = s0.thickness
        if isinstance(thick, (int, float)):
            self._lines.append(f"  {var}.strokeWeight = {thick};")
        elif isinstance(thick, UNStrokeThickness):
            self._lines.append(f"  {var}.strokeWeight = {thick.max_value()};")

        if s0.align:
            _sa = {
                StrokeAlign.INSIDE: "INSIDE",
                StrokeAlign.CENTER: "CENTER",
                StrokeAlign.OUTSIDE: "OUTSIDE",
            }
            sa = _sa.get(s0.align, "CENTER")
            self._lines.append(f'  {var}.strokeAlign = "{sa}";')

        if s0.cap and s0.cap not in ("none", ""):
            cap = s0.cap.upper()
            self._lines.append(f'  {var}.strokeCap = "{cap}";')

        if s0.join and s0.join != "miter":
            join = s0.join.upper()
            self._lines.append(f'  {var}.strokeJoin = "{join}";')

        if s0.dash_pattern:
            dashes = json.dumps(s0.dash_pattern)
            self._lines.append(f"  {var}.dashPattern = {dashes};")

    def _set_effects(self, var: str, node: UNNode) -> None:
        if not node.effects:
            return
        parts: List[str] = []
        for eff in node.effects:
            if isinstance(eff, UNDropShadow):
                kind = "INNER_SHADOW" if eff.inner else "DROP_SHADOW"
                c = eff.color or UNColor(0, 0, 0, 0.25)
                parts.append(
                    f"{{type:'{kind}',color:{_rgba(c)},"
                    f"offset:{{x:{eff.offset_x or 0},y:{eff.offset_y or 0}}},"
                    f"radius:{eff.blur or 0},spread:{eff.spread or 0},"
                    f"visible:true,blendMode:'NORMAL'}}"
                )
            elif isinstance(eff, UNBlur):
                kind = "BACKGROUND_BLUR" if eff.background else "LAYER_BLUR"
                parts.append(
                    f"{{type:'{kind}',radius:{eff.radius or 4},visible:true}}"
                )
        if parts:
            self._lines.append(f"  {var}.effects = [{','.join(parts)}];")

    def _set_clip(self, var: str, node: UNNode) -> None:
        if node.clip_content:
            self._lines.append(f"  {var}.clipsContent = true;")

    def _emit_variable_bindings(self, var: str, node: UNNode) -> None:
        """Emit setBoundVariable() for any design token bindings on this node."""
        bindings = getattr(node, "variable_bindings", {}) or {}
        if not bindings:
            return
        for prop_name, binding in bindings.items():
            vid = json.dumps(str(binding.variable_id))
            self._lines.append(
                f"  /* token: {binding.variable_name} */\n"
                f"  (function() {{\n"
                f"    try {{\n"
                f"      const _v = figma.variables.getVariableById({vid});\n"
                f"      if (_v) {var}.setBoundVariable({json.dumps(prop_name)}, _v);\n"
                f"    }} catch(_e) {{ /* variable not found: {binding.variable_name} */ }}\n"
                f"  }})();"
            )

    def _set_common(self, var: str, node: UNNode) -> None:
        self._set_position(var, node)
        self._set_size(var, node)
        self._set_opacity(var, node)
        self._set_blend(var, node)
        self._set_visible(var, node)
        self._set_locked(var, node)
        self._set_rotation(var, node)
        self._set_corner_radius(var, node)
        self._set_clip(var, node)
        self._set_fills(var, node)
        self._set_strokes(var, node)
        self._set_effects(var, node)
        self._emit_variable_bindings(var, node)

    def _set_layout(self, var: str, node: UNNode) -> None:
        """Set auto-layout properties on frame/component nodes."""
        # node.layout is the LayoutMode field (not node.layout_mode)
        if not node.layout or node.layout == LayoutMode.NONE:
            return

        _lm = {LayoutMode.HORIZONTAL: "HORIZONTAL", LayoutMode.VERTICAL: "VERTICAL"}
        lm = _lm.get(node.layout, "NONE")
        self._lines.append(f'  {var}.layoutMode = "{lm}";')

        # node.gap is the item spacing field (not node.item_spacing)
        if node.gap:
            self._lines.append(f"  {var}.itemSpacing = {node.gap};")

        if node.padding and not node.padding.is_zero():
            p = node.padding
            self._lines.append(
                f"  {var}.paddingTop = {p.top or 0};"
                f" {var}.paddingRight = {p.right or 0};"
                f" {var}.paddingBottom = {p.bottom or 0};"
                f" {var}.paddingLeft = {p.left or 0};"
            )

        if node.justify_content:
            _jc = {
                JustifyContent.START: "MIN",
                JustifyContent.CENTER: "CENTER",
                JustifyContent.END: "MAX",
                JustifyContent.SPACE_BETWEEN: "SPACE_BETWEEN",
                JustifyContent.SPACE_AROUND: "SPACE_BETWEEN",  # closest Figma has
            }
            jc = _jc.get(node.justify_content, "MIN")
            self._lines.append(f'  {var}.primaryAxisAlignItems = "{jc}";')

        if node.align_items:
            _ai = {
                AlignItems.START: "MIN",
                AlignItems.CENTER: "CENTER",
                AlignItems.END: "MAX",
                AlignItems.STRETCH: "STRETCH",
            }
            ai = _ai.get(node.align_items, "MIN")
            self._lines.append(f'  {var}.counterAxisAlignItems = "{ai}";')

        # Sizing modes — use node.width.mode / node.height.mode (UNSize)
        w_mode = node.width.mode if node.width else SizingMode.FIXED
        h_mode = node.height.mode if node.height else SizingMode.FIXED

        # Primary axis = layout direction
        if node.layout == LayoutMode.HORIZONTAL:
            primary_mode = w_mode
            counter_mode = h_mode
        else:
            primary_mode = h_mode
            counter_mode = w_mode

        if primary_mode == SizingMode.HUG:
            self._lines.append(f'  {var}.primaryAxisSizingMode = "AUTO";')
        if counter_mode == SizingMode.HUG:
            self._lines.append(f'  {var}.counterAxisSizingMode = "AUTO";')
        if w_mode == SizingMode.FILL or h_mode == SizingMode.FILL:
            self._lines.append(f"  {var}.layoutGrow = 1;")

        if node.layout_wrap:
            self._lines.append(f'  {var}.layoutWrap = "WRAP";')

    def _emit_children(self, node: UNNode, parent_var: str) -> None:
        for child in (node.children or []):
            self._emit_node(child, parent_var)

    # ------------------------------------------------------------------
    # rich text runs
    # ------------------------------------------------------------------

    def _emit_text_runs(self, var: str, node: UNNode) -> None:
        """Emit Figma setRange* calls for per-character style overrides."""
        runs = node.text_runs or []
        if not runs:
            return

        for run in runs:
            s = run.start
            e = run.end
            if s >= e:
                continue

            # Font override — emit whenever family, weight, or italic changes.
            if run.font_family or run.font_weight or run.italic:
                base_ts = node.text_style
                family = run.font_family or (base_ts.font_family if base_ts else "Inter") or "Inter"
                italic = run.italic
                if not italic and base_ts:
                    italic = base_ts.font_style == "italic"
                weight = run.font_weight or (base_ts.font_weight if base_ts else "400") or "400"
                style = _weight_to_style(weight, italic)
                self._lines.append(
                    f'  {var}.setRangeFontName('
                    f'{{family:{json.dumps(family)},style:{json.dumps(style)}}},'
                    f'{s},{e});'
                )
            if run.font_size:
                self._lines.append(
                    f"  {var}.setRangeFontSize({run.font_size},{s},{e});"
                )

            # Color override.
            if run.fill:
                rgba = _rgba(run.fill)
                self._lines.append(
                    f"  {var}.setRangeFills("
                    f"[{{type:'SOLID',color:{rgba},opacity:{run.fill.a:.4f}}}],"
                    f"{s},{e});"
                )

            # Text decoration.
            if run.underline:
                self._lines.append(
                    f'  {var}.setRangeTextDecoration("UNDERLINE",{s},{e});'
                )
            elif run.strikethrough:
                self._lines.append(
                    f'  {var}.setRangeTextDecoration("STRIKETHROUGH",{s},{e});'
                )

            # Letter spacing.
            if run.letter_spacing is not None:
                self._lines.append(
                    f"  {var}.setRangeLetterSpacing("
                    f"{{value:{run.letter_spacing},unit:'PIXELS'}},{s},{e});"
                )

            # Text transform.
            if run.text_transform and run.text_transform != TextTransform.NONE:
                _tt = {
                    TextTransform.UPPERCASE: "UPPER",
                    TextTransform.LOWERCASE: "LOWER",
                    TextTransform.CAPITALIZE: "TITLE",
                }
                tt = _tt.get(run.text_transform)
                if tt:
                    self._lines.append(
                        f'  {var}.setRangeTextCase("{tt}",{s},{e});'
                    )

    # ------------------------------------------------------------------
    # fill rendering
    # ------------------------------------------------------------------

    def _render_fills(self, fills) -> str:
        parts: List[str] = []
        for fill in fills:
            if isinstance(fill, UNSolidFill):
                parts.append(
                    f"{{type:'SOLID',color:{_rgba(fill.color)},"
                    f"opacity:{fill.color.a:.4f},"
                    f"visible:{_js_bool(fill.enabled)}}}"
                )
            elif isinstance(fill, UNGradientFill):
                parts.append(self._render_gradient(fill))
            elif isinstance(fill, UNImageFill):
                # Image fills need the image bytes — emit a placeholder comment.
                parts.append(
                    "{type:'SOLID',color:{r:0.8,g:0.8,b:0.8,a:1},opacity:1,"
                    "visible:true/*IMAGE_FILL:replace_with_image_paint*/}"
                )
        return "[" + ",".join(parts) + "]"

    def _render_gradient(self, fill: UNGradientFill) -> str:
        _gt = {
            GradientType.LINEAR: "GRADIENT_LINEAR",
            GradientType.RADIAL: "GRADIENT_RADIAL",
            GradientType.ANGULAR: "GRADIENT_ANGULAR",
            GradientType.DIAMOND: "GRADIENT_DIAMOND",
        }
        gtype = _gt.get(fill.gradient_type, "GRADIENT_LINEAR")
        stops: List[str] = []
        for stop in (fill.stops or []):
            stops.append(
                f"{{position:{stop.position:.4f},"
                f"color:{_rgba(stop.color)}}}"
            )
        transform = _gradient_transform(fill.rotation or 0.0)
        return (
            f"{{type:'{gtype}',"
            f"gradientStops:[{','.join(stops)}],"
            f"gradientTransform:{transform},"
            f"visible:{_js_bool(fill.enabled)}}}"
        )


# ---------------------------------------------------------------------------
# _DesktopBridge — pure stdlib RFC 6455 WebSocket SERVER
# ---------------------------------------------------------------------------

class _DesktopBridge:
    """
    Minimal WebSocket server for the Desktop Bridge protocol.

    The Desktop Bridge Figma plugin connects to this server as a client.
    Sends EXECUTE_CODE → receives result.

    Protocol:
        → {"id": "<req_id>", "method": "EXECUTE_CODE",
           "params": {"code": "<js>", "timeout": <ms>}}
        ← {"id": "<req_id>", "result": {...}}
        ← {"id": "<req_id>", "error": "<msg>"}
    """

    _MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, port: int = 9224, connect_timeout: float = 60.0) -> None:
        self._port = port
        self._connect_timeout = connect_timeout
        self._srv: Optional[socket.socket] = None
        self._conn: Optional[socket.socket] = None
        self._req_counter = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", self._port))
        self._srv.listen(1)
        self._srv.settimeout(self._connect_timeout)
        print(
            f"[FigmaWriter] WebSocket server on ws://127.0.0.1:{self._port} — "
            f"configure Desktop Bridge plugin to connect here.",
            file=sys.stderr,
        )
        try:
            conn, addr = self._srv.accept()
        except socket.timeout:
            raise TimeoutError(
                f"Desktop Bridge plugin did not connect within "
                f"{self._connect_timeout}s. Port: {self._port}"
            )
        self._conn = conn
        self._conn.settimeout(None)
        self._ws_handshake()
        print(f"[FigmaWriter] Desktop Bridge connected from {addr}.", file=sys.stderr)

    def close(self) -> None:
        for s in (self._conn, self._srv):
            if s:
                try:
                    s.close()
                except Exception:
                    pass
        self._conn = None
        self._srv = None

    def execute_code(self, code: str, timeout_ms: int = 30000) -> dict:
        with self._lock:
            self._req_counter += 1
            req_id = f"py_{self._req_counter}_{int(time.time()*1000)}"
            self._send_json({
                "id": req_id,
                "method": "EXECUTE_CODE",
                "params": {"code": code, "timeout": timeout_ms},
            })
            deadline = time.time() + timeout_ms / 1000.0 + 5
            while time.time() < deadline:
                msg = self._recv_json(deadline - time.time())
                if msg and msg.get("id") == req_id:
                    return msg
            raise TimeoutError(f"No response from Figma plugin within {timeout_ms}ms.")

    # RFC 6455 handshake
    def _ws_handshake(self) -> None:
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = self._conn.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed during WS handshake.")
            raw += chunk
        headers: Dict[str, str] = {}
        for line in raw.split(b"\r\n")[1:]:
            if b":" in line:
                k, _, v = line.partition(b":")
                headers[k.strip().lower().decode()] = v.strip().decode()
        key = headers.get("sec-websocket-key", "")
        accept = base64.b64encode(
            hashlib.sha1((key + self._MAGIC).encode()).digest()
        ).decode()
        self._conn.sendall((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode())

    def _send_json(self, obj: dict) -> None:
        data = json.dumps(obj).encode("utf-8")
        n = len(data)
        if n < 126:
            hdr = struct.pack("!BB", 0x81, n)
        elif n < 65536:
            hdr = struct.pack("!BBH", 0x81, 126, n)
        else:
            hdr = struct.pack("!BBQ", 0x81, 127, n)
        self._conn.sendall(hdr + data)

    def _recv_json(self, timeout: float) -> Optional[dict]:
        self._conn.settimeout(max(timeout, 0.1))
        try:
            data = self._ws_recv()
        except socket.timeout:
            return None
        finally:
            self._conn.settimeout(None)
        return json.loads(data) if data else None

    def _ws_recv(self) -> Optional[bytes]:
        def rx(n: int) -> bytes:
            buf = b""
            while len(buf) < n:
                c = self._conn.recv(n - len(buf))
                if not c:
                    raise ConnectionError("WebSocket peer closed.")
                buf += c
            return buf
        hdr = rx(2)
        if (hdr[0] & 0x0F) == 8:
            return None
        masked = bool(hdr[1] & 0x80)
        length = hdr[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", rx(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", rx(8))[0]
        mask_key = rx(4) if masked else b"\x00\x00\x00\x00"
        payload = bytearray(rx(length))
        if masked:
            for i in range(length):
                payload[i] ^= mask_key[i % 4]
        return bytes(payload)


# ---------------------------------------------------------------------------
# FigmaWriter
# ---------------------------------------------------------------------------

class FigmaWriter(BaseWriter):
    """
    Write a UNNode tree into Figma via Plugin API JavaScript.

    Parameters
    ----------
    mode : "script" | "bridge" | "http"
        "script"  — save a self-contained .js IIFE to `output_dir`.
                    User pastes it into Figma ▶ Plugins ▶ Console.
        "bridge"  — start a local WebSocket server; Desktop Bridge executes live.
        "http"    — use HTTP bridge server (figma-bridge-server) for live execution.
                    This mode is symmetric with Paper (HTTP 29979) and enables
                    any client to write to Figma via HTTP POST.
    output_dir : str | Path | None
        Where to save .js files (mode="script"). Defaults to CWD.
    bridge_port : int
        WebSocket server port (mode="bridge"). Default 9224.
    http_bridge_port : int
        HTTP bridge server port (mode="http"). Default 9223.
    bridge_timeout : float
        Seconds to wait for EXECUTE_CODE response (mode="bridge" or "http").
    connect_timeout : float
        Seconds to wait for Desktop Bridge plugin to connect (mode="bridge").

    Note on Figma REST API
    ----------------------
    Figma's public REST API is **read-only** for design nodes.
    Creating/updating FRAME, TEXT, RECTANGLE etc. nodes requires
    the Figma Plugin API (JavaScript inside Figma) or a Figma app plugin.
    See: https://www.figma.com/developers/api#access
    This writer generates the required JavaScript automatically.
    """

    tool_name = "figma"

    def __init__(
        self,
        *,
        mode: str = "script",
        output_dir=None,
        bridge_port: int = 9224,
        bridge_timeout: float = 30.0,
        connect_timeout: float = 60.0,
        http_bridge_port: int = 9223,
    ) -> None:
        super().__init__()
        if mode not in ("script", "bridge", "http"):
            raise ValueError(f"mode must be 'script', 'bridge', or 'http', got {mode!r}")
        self._mode = mode
        self._output_dir = Path(output_dir) if output_dir else Path.cwd()
        self._bridge_port = bridge_port
        self._bridge_timeout = bridge_timeout
        self._connect_timeout = connect_timeout
        self._http_bridge_port = http_bridge_port
        self._bridge: Optional[_DesktopBridge] = None
        self._http_bridge: Optional["FigmaBridgeClient"] = None

    def connect(self) -> None:
        if self._mode == "bridge":
            self._bridge = _DesktopBridge(
                port=self._bridge_port,
                connect_timeout=self._connect_timeout,
            )
            self._bridge.start()
        elif self._mode == "http":
            # Lazy import to avoid circular dependency
            from adapters.figma.http_bridge import FigmaBridgeClient
            self._http_bridge = FigmaBridgeClient(port=self._http_bridge_port)
            # Check server first, then plugin
            if not self._http_bridge.is_server_running():
                raise RuntimeError(
                    f"HTTP bridge server not running on port {self._http_bridge_port}.\n"
                    f"  Start it with: python3 adapters/figma/bridge_server.py --port {self._http_bridge_port}\n"
                    f"  Or: figma-bridge-server --port {self._http_bridge_port}"
                )
            if not self._http_bridge.is_connected():
                raise RuntimeError(
                    f"HTTP bridge server is running but Desktop Bridge plugin is not connected.\n"
                    f"  1. Open Figma and run the Desktop Bridge plugin\n"
                    f"  2. Configure the plugin to connect to port {self._http_bridge_port}\n"
                    f"  3. Wait for the 'Connected' message in the plugin"
                )

    def disconnect(self) -> None:
        if self._bridge:
            self._bridge.close()
            self._bridge = None
        self._http_bridge = None

    def write_node(
        self,
        node: UNNode,
        parent_id: str = "",
        replace_id: str = "",
    ) -> str:
        """
        Convert *node* tree to Figma Plugin API JavaScript and execute or save it.

        Returns
        -------
        str
            mode="script"  → absolute path to saved .js file
            mode="bridge"  → Figma node-ID of the created node
            mode="http"    → Figma node-ID of the created node
        """
        emitter = _FigmaCodeEmitter(node, parent_id=parent_id, replace_id=replace_id)
        code = emitter.emit()

        if self._mode == "bridge":
            return self._write_via_bridge(code)
        if self._mode == "http":
            return self._write_via_http(code)
        return self._write_to_file(node, code)

    def _write_via_bridge(self, code: str) -> str:
        if not self._bridge:
            raise RuntimeError(
                "Bridge not connected. Call connect() first or use the "
                "context-manager form: `with FigmaWriter(mode='bridge') as w:`"
            )
        response = self._bridge.execute_code(
            code, timeout_ms=int(self._bridge_timeout * 1000)
        )
        if "error" in response:
            raise RuntimeError(f"Figma plugin error: {response['error']}")
        result = response.get("result", {})
        if isinstance(result, dict) and not result.get("success", True):
            raise RuntimeError(f"Figma execution failed: {result.get('error', 'unknown')}")
        return (result or {}).get("nodeId", "")

    def _write_via_http(self, code: str) -> str:
        """Execute code via HTTP bridge server (figma-bridge-server)."""
        if not self._http_bridge:
            # Lazy init
            from adapters.figma.http_bridge import FigmaBridgeClient
            self._http_bridge = FigmaBridgeClient(port=self._http_bridge_port)

        # Re-check connection before executing
        if not self._http_bridge.is_server_running():
            raise RuntimeError(
                f"HTTP bridge server not running on port {self._http_bridge_port}.\n"
                f"  Start it with: python3 adapters/figma/bridge_server.py --port {self._http_bridge_port}"
            )
        if not self._http_bridge.is_connected():
            raise RuntimeError(
                f"Desktop Bridge plugin not connected to HTTP bridge on port {self._http_bridge_port}.\n"
                f"  1. Open Figma and run the Desktop Bridge plugin\n"
                f"  2. Ensure the plugin is connected"
            )

        result = self._http_bridge.execute_code(code, timeout_ms=int(self._bridge_timeout * 1000))
        if not result.success:
            error_msg = result.error or "Unknown error"
            # Check for specific error conditions
            if "not connected" in error_msg.lower():
                raise RuntimeError(
                    f"Desktop Bridge plugin disconnected during execution.\n"
                    f"  Reconnect the plugin in Figma and try again.\n"
                    f"  Original error: {error_msg}"
                )
            raise RuntimeError(f"Figma HTTP bridge error: {error_msg}")
        return result.node_id or ""

    def _write_to_file(self, node: UNNode, code: str) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        safe = (node.name or "figma_node").replace(" ", "_").replace("/", "_")
        out = self._output_dir / f"{safe}.js"
        n = 1
        while out.exists():
            out = self._output_dir / f"{safe}_{n}.js"
            n += 1
        header = textwrap.dedent(f"""\
            // Generated by FigmaWriter — paste into Figma ▶ Plugins ▶ Console
            // Node : {node.name!r}
            // Type : {node.type.value}
            // Date : {time.strftime('%Y-%m-%d %H:%M:%S')}
            //
            // Steps:
            //   1. Open Figma
            //   2. Plugins ▶ Development ▶ Open Console  (Cmd+Opt+I)
            //   3. Paste this script and press Enter
            //
        """)
        out.write_text(header + code, encoding="utf-8")
        return str(out)
