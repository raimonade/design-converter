from __future__ import annotations

import json
import re

from ptf.tree import TreeNode
from ptf.parsers import (
    parse_px, parse_hex_color, parse_color_with_alpha, format_color,
    map_font_family, map_font_weight,
    parse_letter_spacing, parse_line_height, parse_box_shadow,
)


class FigmaCodeGen:
    """Generates Figma Plugin API JavaScript from a Paper tree."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._counter = 0
        self._fonts_needed: set[tuple[str, str]] = set()

    def generate(self, tree: TreeNode, artboard_width: int, artboard_height: int) -> str:
        self._collect_fonts(tree)

        self._lines = []
        L = self._lines
        L.append("(async () => { try {")

        for family, style in sorted(self._fonts_needed):
            L.append(
                f"  await figma.loadFontAsync("
                f"{{family:{json.dumps(family)},style:{json.dumps(style)}}});"
            )

        L.append("  const page = figma.currentPage;")
        L.append("")

        root_var = self._emit_artboard(tree, artboard_width, artboard_height)

        L.append(f"  figma.viewport.scrollAndZoomIntoView([{root_var}]);")
        L.append(
            f"  return {{success:true,nodeId:{root_var}.id,"
            f"nodeName:{root_var}.name}};"
        )
        L.append("} catch(e) { return {success:false,error:String(e)}; }")
        L.append("})();")

        return "\n".join(L)

    def _next_var(self) -> str:
        v = f"n{self._counter}"
        self._counter += 1
        return v

    def _collect_fonts(self, node: TreeNode) -> None:
        styles = node.styles
        if node.component == "Text":
            family = map_font_family(styles.get("fontFamily", "Inter"))
            weight = styles.get("fontWeight", 400)
            style_name = map_font_weight(weight)
            self._fonts_needed.add((family, style_name))
        for child in node.children:
            self._collect_fonts(child)

    def _emit_artboard(self, node: TreeNode, width: int, height: int) -> str:
        var = self._next_var()
        L = self._lines
        styles = node.styles

        L.append(f"  const {var} = figma.createFrame();")
        L.append(f"  page.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")
        L.append(f"  {var}.resize({width},{height});")

        bg = styles.get("backgroundColor")
        if bg:
            color = parse_hex_color(bg)
            if color:
                L.append(
                    f"  {var}.fills = [{{type:'SOLID',"
                    f"color:{format_color(color)}}}];"
                )

        flex_dir = styles.get("flexDirection", "row")
        if styles.get("display") == "flex":
            layout_mode = "VERTICAL" if flex_dir == "column" else "HORIZONTAL"
            L.append(f'  {var}.layoutMode = "{layout_mode}";')
            L.append(f'  {var}.counterAxisSizingMode = "FIXED";')
            L.append(f'  {var}.primaryAxisSizingMode = "AUTO";')

            self._emit_padding(var, styles)
            self._emit_gap(var, styles)
            self._emit_justify(var, styles)
            L.append(f'  {var}.counterAxisAlignItems = "MIN";')

        if styles.get("overflow") == "clip":
            L.append(f"  {var}.clipsContent = true;")

        L.append("")

        for child in node.children:
            child_var = self._emit_node(child, var)
            self._emit_child_sizing(child_var, child, node)

        return var

    def _emit_node(self, node: TreeNode, parent_var: str) -> str:
        if node.component == "Text":
            return self._emit_text(node, parent_var)
        if node.component == "Rectangle":
            return self._emit_rectangle(node, parent_var)
        if node.component in ("SVG", "SVGVisualElement"):
            return self._emit_svg_placeholder(node, parent_var)
        return self._emit_frame(node, parent_var)

    def _emit_frame(self, node: TreeNode, parent_var: str) -> str:
        var = self._next_var()
        L = self._lines
        styles = node.styles

        L.append(f"  const {var} = figma.createFrame();")
        L.append(f"  {parent_var}.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")

        has_explicit_flex = styles.get("display") == "flex"
        has_children = len(node.children) > 0
        has_padding = any(
            styles.get(k) for k in (
                "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
                "paddingBlock", "paddingInline",
            )
        )
        is_flex = has_explicit_flex or has_children or has_padding

        if is_flex:
            flex_dir = styles.get("flexDirection", "row")
            if not has_explicit_flex and flex_dir == "row":
                flex_dir = "column"
            layout_mode = "VERTICAL" if flex_dir == "column" else "HORIZONTAL"
            L.append(f'  {var}.layoutMode = "{layout_mode}";')

            skip_top_pad = (
                layout_mode == "HORIZONTAL"
                and styles.get("overflow") == "clip"
                and any(
                    child.styles.get("flexGrow")
                    and str(child.styles.get("flexGrow")) not in ("0", "")
                    for child in node.children
                )
            )
            self._emit_padding(var, styles, top_override=0 if skip_top_pad else None)
            self._emit_gap(var, styles)
            self._emit_justify(var, styles)
            self._emit_align(var, styles)
            self._emit_frame_sizing(var, styles, layout_mode)
        else:
            w = parse_px(styles.get("width"))
            h = parse_px(styles.get("height"))
            if w is not None and h is not None:
                L.append(f"  {var}.resize({w},{h});")
            elif w is not None:
                L.append(f"  {var}.resize({w},100);")
            elif h is not None:
                L.append(f"  {var}.resize(100,{h});")

        self._emit_fills(var, node, L)

        self._emit_border_radius(var, styles)
        self._emit_border(var, styles)

        if styles.get("overflow") == "clip":
            L.append(f"  {var}.clipsContent = true;")

        shadow = styles.get("boxShadow")
        if shadow:
            effects = parse_box_shadow(shadow)
            if effects:
                self._emit_effects(var, effects)

        L.append("")

        for child in node.children:
            child_var = self._emit_node(child, var)
            if is_flex:
                self._emit_child_sizing(child_var, child, node)

        return var

    def _emit_fills(self, var: str, node: TreeNode, L: list[str]) -> None:
        styles = node.styles
        bg = styles.get("backgroundColor")

        if node.image_b64:
            bg_size = styles.get("backgroundSize", "cover")
            scale = "FIT" if bg_size == "contain" else "FILL"
            self._emit_image_from_b64(var, node.image_b64, scale, L)
        elif bg:
            color = parse_hex_color(bg)
            if color:
                L.append(
                    f"  {var}.fills = [{{type:'SOLID',"
                    f"color:{format_color(color)}}}];"
                )
        else:
            L.append(f"  {var}.fills = [];")

    def _emit_image_from_b64(self, var: str, b64: str, scale: str, L: list[str]) -> None:
        L.append(f"  {{")
        L.append(f"    const b64_{var} = {json.dumps(b64)};")
        L.append(f"    const bin_{var} = atob(b64_{var});")
        L.append(f"    const bytes_{var} = new Uint8Array(bin_{var}.length);")
        L.append(f"    for(let i=0;i<bin_{var}.length;i++) bytes_{var}[i]=bin_{var}.charCodeAt(i);")
        L.append(f"    const img_{var} = figma.createImage(bytes_{var});")
        L.append(f"    {var}.fills = [{{type:'IMAGE',scaleMode:'{scale}',imageHash:img_{var}.hash}}];")
        L.append(f"  }}")

    def _emit_text(self, node: TreeNode, parent_var: str) -> str:
        var = self._next_var()
        L = self._lines
        styles = node.styles

        L.append(f"  const {var} = figma.createText();")
        L.append(f"  {parent_var}.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")

        family = map_font_family(styles.get("fontFamily", "Inter"))
        weight = styles.get("fontWeight", 400)
        style_name = map_font_weight(weight)
        L.append(
            f"  {var}.fontName = {{family:{json.dumps(family)},"
            f"style:{json.dumps(style_name)}}};"
        )

        font_size = parse_px(styles.get("fontSize"))
        if font_size:
            L.append(f"  {var}.fontSize = {font_size};")

        ls = parse_letter_spacing(str(styles.get("letterSpacing", "")))
        if ls:
            L.append(f"  {var}.letterSpacing = {ls};")

        lh = parse_line_height(styles.get("lineHeight"))
        if lh:
            L.append(f"  {var}.lineHeight = {lh};")

        L.append(f'  {var}.textAutoResize = "WIDTH_AND_HEIGHT";')

        text = node.text_content or node.name
        L.append(f"  {var}.characters = {json.dumps(text, ensure_ascii=False)};")

        if node.node_width and node.node_width > 0:
            max_w = styles.get("maxWidth")
            width_str = styles.get("width")
            if max_w or (width_str and width_str not in ("auto", "fit-content")):
                L.append(f'  {var}.textAutoResize = "HEIGHT";')
                L.append(f"  {var}.resize({node.node_width},{node.node_height or 100});")

        color_hex = styles.get("color")
        if color_hex:
            color = parse_hex_color(color_hex)
            if color:
                L.append(
                    f"  {var}.fills = [{{type:'SOLID',"
                    f"color:{format_color(color)}}}];"
                )

        L.append("")
        return var

    def _emit_rectangle(self, node: TreeNode, parent_var: str) -> str:
        var = self._next_var()
        L = self._lines
        styles = node.styles

        L.append(f"  const {var} = figma.createRectangle();")
        L.append(f"  {parent_var}.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")

        w = parse_px(styles.get("width"))
        h = parse_px(styles.get("height"))
        if w and h:
            L.append(f"  {var}.resize({w},{h});")

        if node.image_b64:
            bg_size = styles.get("backgroundSize", "cover")
            scale = "FIT" if bg_size == "contain" else "FILL"
            self._emit_image_from_b64(var, node.image_b64, scale, L)
        else:
            bg = styles.get("backgroundColor")
            if bg:
                color = parse_hex_color(bg)
                if color:
                    L.append(
                        f"  {var}.fills = [{{type:'SOLID',"
                        f"color:{format_color(color)}}}];"
                    )

        self._emit_border_radius(var, styles)
        self._emit_border(var, styles)

        L.append("")
        return var

    def _emit_svg_placeholder(self, node: TreeNode, parent_var: str) -> str:
        var = self._next_var()
        L = self._lines
        w = node.node_width or 20
        h = node.node_height or 20

        L.append(f"  const {var} = figma.createRectangle();")
        L.append(f"  {parent_var}.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")
        L.append(f"  {var}.resize({w},{h});")

        if node.image_b64:
            self._emit_image_from_b64(var, node.image_b64, "FILL", L)
        else:
            L.append(f"  {var}.fills = [{{type:'SOLID',color:{{r:0.8,g:0.8,b:0.8}}}}];")

        L.append("")
        return var

    def _emit_padding(self, var: str, styles: dict, top_override: float | None = None) -> None:
        L = self._lines
        pb = parse_px(styles.get("paddingBlock"))
        pi = parse_px(styles.get("paddingInline"))
        pt = parse_px(styles.get("paddingTop"))
        pr = parse_px(styles.get("paddingRight"))
        pbot = parse_px(styles.get("paddingBottom"))
        pl = parse_px(styles.get("paddingLeft"))

        top = pt if pt is not None else (pb if pb is not None else 0)
        if top_override is not None:
            top = top_override
        right = pr if pr is not None else (pi if pi is not None else 0)
        bottom = pbot if pbot is not None else (pb if pb is not None else 0)
        left = pl if pl is not None else (pi if pi is not None else 0)

        if any(v > 0 for v in [top, right, bottom, left]):
            L.append(
                f"  {var}.paddingTop = {top};"
                f" {var}.paddingRight = {right};"
                f" {var}.paddingBottom = {bottom};"
                f" {var}.paddingLeft = {left};"
            )

    def _emit_gap(self, var: str, styles: dict) -> None:
        gap = parse_px(styles.get("gap"))
        if gap is not None and gap > 0:
            self._lines.append(f"  {var}.itemSpacing = {gap};")

    def _emit_justify(self, var: str, styles: dict) -> None:
        jc = styles.get("justifyContent", "")
        jc_map = {
            "flex-start": "MIN",
            "center": "CENTER",
            "flex-end": "MAX",
            "space-between": "SPACE_BETWEEN",
        }
        mapped = jc_map.get(jc)
        if mapped:
            self._lines.append(f'  {var}.primaryAxisAlignItems = "{mapped}";')

    def _emit_align(self, var: str, styles: dict) -> None:
        ai = styles.get("alignItems", "")
        ai_map = {
            "flex-start": "MIN",
            "center": "CENTER",
            "flex-end": "MAX",
            "stretch": "STRETCH",
            "baseline": "MIN",
        }
        mapped = ai_map.get(ai)
        if mapped:
            self._lines.append(f'  {var}.counterAxisAlignItems = "{mapped}";')

    def _emit_frame_sizing(self, var: str, styles: dict, layout_mode: str) -> None:
        L = self._lines
        w = styles.get("width")
        h = styles.get("height")

        if layout_mode == "VERTICAL":
            h_px = parse_px(h) if h else None
            if h_px is not None and h != "fit-content":
                L.append(f'  {var}.primaryAxisSizingMode = "FIXED";')
            else:
                L.append(f'  {var}.primaryAxisSizingMode = "AUTO";')

            if w == "100%":
                pass
            elif w is not None and w != "100%":
                w_px = parse_px(w)
                if w_px is not None:
                    L.append(f'  {var}.counterAxisSizingMode = "FIXED";')
                    L.append(f"  {var}.resize({w_px},{var}.height);")
                else:
                    L.append(f'  {var}.counterAxisSizingMode = "AUTO";')
            else:
                L.append(f'  {var}.counterAxisSizingMode = "AUTO";')

        else:
            w_px = parse_px(w) if w else None
            if w == "100%":
                L.append(f'  {var}.primaryAxisSizingMode = "FIXED";')
            elif w_px is not None:
                L.append(f'  {var}.primaryAxisSizingMode = "FIXED";')
                L.append(f"  {var}.resize({w_px},{var}.height);")
            else:
                L.append(f'  {var}.primaryAxisSizingMode = "AUTO";')

            h_px = parse_px(h) if h else None
            if h_px is not None and h != "fit-content":
                L.append(f'  {var}.counterAxisSizingMode = "FIXED";')
                L.append(f"  {var}.resize({var}.width,{h_px});")
            else:
                L.append(f'  {var}.counterAxisSizingMode = "AUTO";')

    def _emit_child_sizing(self, child_var: str, child: TreeNode, parent: TreeNode) -> None:
        L = self._lines
        styles = child.styles
        parent_styles = parent.styles

        flex_dir = parent_styles.get("flexDirection", "row")
        is_vertical = flex_dir == "column"

        w = styles.get("width")
        h = styles.get("height")
        flex_grow = styles.get("flexGrow")
        flex_shrink = styles.get("flexShrink")

        if is_vertical:
            parent_align = parent_styles.get("alignItems", "stretch")
            has_explicit_w = w is not None and w not in ("100%", "auto", "fit-content")
            w_px = parse_px(w) if has_explicit_w else None

            should_stretch = (
                w_px is None
                and parent_align in ("stretch", "", "normal")
            )
            if should_stretch:
                L.append(f'  {child_var}.layoutAlign = "STRETCH";')
                child_flex = child.styles.get("display") == "flex"
                child_dir = child.styles.get("flexDirection", "row")
                if child_flex and child_dir != "column":
                    L.append(f'  {child_var}.primaryAxisSizingMode = "FIXED";')

            if flex_grow and str(flex_grow) not in ("0", ""):
                L.append(f"  {child_var}.layoutGrow = 1;")

        else:
            parent_align = parent_styles.get("alignItems", "stretch")
            has_explicit_h = h is not None and h not in ("100%", "auto", "fit-content")
            is_clipped_grower = (
                styles.get("overflow") == "clip"
                and flex_grow and str(flex_grow) not in ("0", "")
            )

            should_stretch = (
                not is_clipped_grower
                and (
                    h == "100%"
                    or (parent_align in ("stretch", "", "normal") and not has_explicit_h)
                )
            )
            if should_stretch:
                L.append(f'  {child_var}.layoutAlign = "STRETCH";')
                child_flex = child.styles.get("display") == "flex"
                child_dir = child.styles.get("flexDirection", "column")
                if child_flex and child_dir == "column":
                    L.append(f'  {child_var}.primaryAxisSizingMode = "FIXED";')

            if flex_grow and str(flex_grow) not in ("0", ""):
                L.append(f"  {child_var}.layoutGrow = 1;")

            if flex_shrink == "0":
                L.append(f"  {child_var}.layoutGrow = 0;")

    def _emit_border_radius(self, var: str, styles: dict) -> None:
        L = self._lines
        uniform = parse_px(styles.get("borderRadius"))
        if uniform is not None and uniform > 0:
            L.append(f"  {var}.cornerRadius = {uniform};")
            return

        tl = parse_px(styles.get("borderTopLeftRadius"))
        tr = parse_px(styles.get("borderTopRightRadius"))
        br = parse_px(styles.get("borderBottomRightRadius"))
        bl = parse_px(styles.get("borderBottomLeftRadius"))

        has_any = any(v is not None and v > 0 for v in [tl, tr, br, bl])
        if has_any:
            L.append(
                f"  {var}.topLeftRadius = {tl or 0};"
                f" {var}.topRightRadius = {tr or 0};"
                f" {var}.bottomRightRadius = {br or 0};"
                f" {var}.bottomLeftRadius = {bl or 0};"
            )

    def _emit_border(self, var: str, styles: dict) -> None:
        L = self._lines
        bw = parse_px(styles.get("borderWidth"))
        bc = styles.get("borderColor")

        btw = parse_px(styles.get("borderTopWidth"))
        brw = parse_px(styles.get("borderRightWidth"))
        bbw = parse_px(styles.get("borderBottomWidth"))
        blw = parse_px(styles.get("borderLeftWidth"))

        width = bw
        if not width or width <= 0:
            indiv = [v for v in [btw, brw, bbw, blw] if v is not None and v > 0]
            if indiv:
                width = max(indiv)

        color_hex = bc
        if not color_hex:
            for prop in ("borderTopColor", "borderRightColor",
                         "borderBottomColor", "borderLeftColor"):
                c = styles.get(prop)
                if c:
                    color_hex = c
                    break

        if not width or width <= 0:
            ow = parse_px(styles.get("outlineWidth"))
            oc = styles.get("outlineColor")
            if ow and ow > 0:
                width = ow
                color_hex = oc

        if not width or width <= 0 or not color_hex:
            return

        color, opacity = parse_color_with_alpha(color_hex)
        if not color:
            return

        fill_part = f"color:{format_color(color)}"
        if opacity < 1.0:
            fill_part += f",opacity:{opacity:.4f}"

        L.append(f"  {var}.strokes = [{{type:'SOLID',{fill_part}}}];")
        L.append(f"  {var}.strokeWeight = {width};")
        L.append(f'  {var}.strokeAlign = "INSIDE";')

    def _emit_effects(self, var: str, effects: list[dict]) -> None:
        parts = []
        for eff in effects:
            color = eff["color"]
            parts.append(
                f"{{type:'{eff['type']}',"
                f"color:{{r:{color['r']:.4f},g:{color['g']:.4f},"
                f"b:{color['b']:.4f},a:{eff['opacity']:.4f}}},"
                f"offset:{{x:{eff['offset_x']},y:{eff['offset_y']}}},"
                f"radius:{eff['blur']},spread:{eff['spread']},"
                f"visible:true,blendMode:'NORMAL'}}"
            )
        self._lines.append(f"  {var}.effects = [{','.join(parts)}];")
