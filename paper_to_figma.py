"""
paper_to_figma.py — Convert Paper Design artboards to Figma

Reads Paper's design tree via its MCP HTTP API, generates Figma Plugin API
JavaScript, and pushes via Desktop Bridge WebSocket.

Usage:
    .venv/bin/python3 paper_to_figma.py                        # all artboards
    .venv/bin/python3 paper_to_figma.py --artboard X6-0        # specific artboard
    .venv/bin/python3 paper_to_figma.py --artboard X6-0 --dry-run  # output JS only
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

log = logging.getLogger("paper_to_figma")

PAPER_MCP_URL = "http://127.0.0.1:29979/mcp"
BATCH_SIZE = 20  # max nodeIds per get_computed_styles call

# Font family mapping: Paper fonts -> Figma fonts
FONT_FAMILY_MAP = {
    "geist": "Inter",
    "system-ui": "Inter",
    "sans-serif": "Inter",
    "system sans-serif": "Inter",
}

WEIGHT_STYLE_MAP = {
    100: "Thin",
    200: "Extra Light",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "Semi Bold",
    700: "Bold",
    800: "Extra Bold",
    900: "Black",
}


@dataclass
class TreeNode:
    id: str
    name: str
    component: str  # "Frame", "Text", "Rectangle", etc.
    text_content: str = ""
    node_width: Optional[float] = None
    node_height: Optional[float] = None
    children: list[TreeNode] = field(default_factory=list)
    styles: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Paper MCP client
# ---------------------------------------------------------------------------


class PaperMCPClient:
    """Talks to Paper's MCP server over HTTP with SSE responses."""

    def __init__(self, url: str = PAPER_MCP_URL) -> None:
        self._url = url
        self._session_id: Optional[str] = None
        self._request_id = 0

    def initialize(self) -> None:
        resp = self._post({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "paper_to_figma", "version": "0.1"},
            },
        })
        sid = resp.headers.get("mcp-session-id")
        if sid:
            self._session_id = sid
            log.info("MCP session: %s", sid)
        else:
            log.warning("No mcp-session-id in response headers")

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        resp = self._post(payload)
        return self._parse_sse(resp)

    def get_basic_info(self) -> dict:
        return self.call_tool("get_basic_info")

    def get_children(self, node_id: str) -> list[dict]:
        result = self.call_tool("get_children", {"nodeId": node_id})
        return result.get("children", [])

    def get_computed_styles(self, node_ids: list[str]) -> dict[str, dict]:
        result = self.call_tool("get_computed_styles", {"nodeIds": node_ids})
        # Result is a dict of nodeId -> styles
        if isinstance(result, dict):
            # Filter out non-style keys (like "count")
            return {k: v for k, v in result.items() if isinstance(v, dict)}
        return {}

    def _post(self, payload: dict) -> requests.Response:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        resp = requests.post(self._url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp

    def _parse_sse(self, resp: requests.Response) -> dict:
        """Parse SSE response to extract JSON-RPC result."""
        content_type = resp.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            # Parse SSE: look for data: lines containing JSON
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        msg = json.loads(data_str)
                        # JSON-RPC response
                        if "result" in msg:
                            return self._extract_content(msg["result"])
                        if "error" in msg:
                            raise RuntimeError(
                                f"MCP error: {msg['error']}"
                            )
                    except json.JSONDecodeError:
                        continue
            raise RuntimeError("No valid JSON-RPC result in SSE response")

        # Plain JSON response
        msg = resp.json()
        if "result" in msg:
            return self._extract_content(msg["result"])
        if "error" in msg:
            raise RuntimeError(f"MCP error: {msg['error']}")
        return msg

    def _extract_content(self, result: dict) -> dict:
        """Extract the actual content from MCP tool result."""
        # MCP tools/call returns {content: [{type: "text", text: "..."}]}
        content_list = result.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                text = item["text"]
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
        return result


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------


def build_tree(client: PaperMCPClient, node_id: str, name: str, component: str) -> TreeNode:
    """Recursively build the full tree for a node."""
    text_content = ""
    node_width = None
    node_height = None
    if component == "Text":
        info = client.call_tool("get_node_info", {"nodeId": node_id})
        text_content = info.get("textContent", name)
        node_width = info.get("width")
        node_height = info.get("height")
    node = TreeNode(
        id=node_id, name=name, component=component,
        text_content=text_content, node_width=node_width, node_height=node_height,
    )
    if component != "Text":
        children_data = client.get_children(node_id)
        for child in children_data:
            child_node = build_tree(
                client,
                child["id"],
                child["name"],
                child["component"],
            )
            node.children.append(child_node)
    return node


def collect_all_ids(node: TreeNode) -> list[str]:
    """Collect all node IDs in the tree."""
    ids = [node.id]
    for child in node.children:
        ids.extend(collect_all_ids(child))
    return ids


def attach_styles(client: PaperMCPClient, tree: TreeNode) -> None:
    """Batch-fetch computed styles and attach to tree nodes."""
    all_ids = collect_all_ids(tree)
    log.info("  Fetching styles for %d nodes...", len(all_ids))

    all_styles: dict[str, dict] = {}
    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = all_ids[i : i + BATCH_SIZE]
        styles = client.get_computed_styles(batch)
        all_styles.update(styles)

    def _apply(node: TreeNode) -> None:
        node.styles = all_styles.get(node.id, {})
        for child in node.children:
            _apply(child)

    _apply(tree)


# ---------------------------------------------------------------------------
# CSS value parsers
# ---------------------------------------------------------------------------


def parse_px(value: str | int | float | None) -> Optional[float]:
    """Parse a CSS pixel value like '48px' -> 48.0. Passthrough numbers."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s.endswith("px"):
        try:
            return float(s[:-2])
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_hex_color(hex_str: str) -> Optional[dict]:
    """Parse '#2C7DFF' -> {r: 0.173, g: 0.490, b: 1.0}."""
    s = hex_str.strip().lstrip("#")
    if len(s) == 6:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
        return {"r": round(r, 4), "g": round(g, 4), "b": round(b, 4)}
    if len(s) == 8:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
        a = int(s[6:8], 16) / 255.0
        return {"r": round(r, 4), "g": round(g, 4), "b": round(b, 4), "a": round(a, 4)}
    return None


def parse_color_with_alpha(hex_str: str) -> tuple[Optional[dict], float]:
    """Parse hex color, return ({r,g,b}, opacity)."""
    color = parse_hex_color(hex_str)
    if color is None:
        return None, 1.0
    a = color.pop("a", 1.0)
    return color, a


def format_color(color: dict) -> str:
    """Format {r,g,b} as JS object literal."""
    return f"{{r:{color['r']:.4f},g:{color['g']:.4f},b:{color['b']:.4f}}}"


def map_font_family(raw: str) -> str:
    """Map Paper font families to Figma-compatible ones."""
    # Strip quotes and get first family
    families = [f.strip().strip('"').strip("'") for f in raw.split(",")]
    for fam in families:
        mapped = FONT_FAMILY_MAP.get(fam.lower())
        if mapped:
            return mapped
    # Fallback
    return "Inter"


def map_font_weight(weight: int | str) -> str:
    """Map numeric weight to Figma style name."""
    w = int(weight) if isinstance(weight, str) else weight
    return WEIGHT_STYLE_MAP.get(w, "Regular")


def parse_letter_spacing(value: str) -> Optional[str]:
    """Parse '-0.025em' -> {value: -2.5, unit: 'PERCENT'}."""
    if not value:
        return None
    s = str(value).strip()
    m = re.match(r"^(-?[\d.]+)em$", s)
    if m:
        em_val = float(m.group(1))
        percent = em_val * 100
        return f"{{value:{percent},unit:'PERCENT'}}"
    m = re.match(r"^(-?[\d.]+)px$", s)
    if m:
        return f"{{value:{float(m.group(1))},unit:'PIXELS'}}"
    return None


def parse_line_height(value: str | int | float) -> Optional[str]:
    """Parse '115%' -> {value:115, unit:'PERCENT'}, '18px' -> {value:18,unit:'PIXELS'}."""
    if value is None:
        return None
    s = str(value).strip()
    if s.endswith("%"):
        try:
            return f"{{value:{float(s[:-1])},unit:'PERCENT'}}"
        except ValueError:
            return None
    m = re.match(r"^(-?[\d.]+)px$", s)
    if m:
        return f"{{value:{float(m.group(1))},unit:'PIXELS'}}"
    try:
        v = float(s)
        # Bare number: treat as px
        return f"{{value:{v},unit:'PIXELS'}}"
    except ValueError:
        return None


def parse_border_radius(styles: dict) -> Optional[str]:
    """Extract border radius from styles, return JS code or None."""
    # Check for individual corners
    tl = parse_px(styles.get("borderTopLeftRadius"))
    tr = parse_px(styles.get("borderTopRightRadius"))
    br = parse_px(styles.get("borderBottomRightRadius"))
    bl = parse_px(styles.get("borderBottomLeftRadius"))

    # Shorthand
    uniform = parse_px(styles.get("borderRadius"))

    if uniform is not None and uniform > 0:
        # Check if it's a pill shape
        if uniform >= 999:
            return "cornerRadius_pill"
        return f"cornerRadius_uniform_{uniform}"

    if any(v is not None and v > 0 for v in [tl, tr, br, bl]):
        return f"cornerRadius_individual_{tl or 0}_{tr or 0}_{br or 0}_{bl or 0}"

    return None


def parse_box_shadow(value: str) -> list[dict]:
    """Parse CSS boxShadow into Figma effects.

    Examples:
      '#0A0A141A 0px 0px 0px 1px inset'
      '#0A0A1414 0px 4px 24px'
      '#0A0A141A 0px 0px 0px 1px inset, #0A0A1414 0px 4px 24px'
    """
    if not value:
        return []

    effects = []
    # Split on ", " but be careful with commas inside values
    # Simple approach: split by ", #" and re-add the "#"
    parts = re.split(r",\s*(?=#)", value.strip())
    for part in parts:
        part = part.strip()
        if not part:
            continue

        is_inset = "inset" in part
        part_clean = part.replace("inset", "").strip()

        # Match: #color x y blur [spread]
        m = re.match(
            r"(#[0-9A-Fa-f]+)\s+"
            r"(-?[\d.]+)px\s+(-?[\d.]+)px\s+(-?[\d.]+)px"
            r"(?:\s+(-?[\d.]+)px)?",
            part_clean,
        )
        if not m:
            continue

        color_hex = m.group(1)
        offset_x = float(m.group(2))
        offset_y = float(m.group(3))
        blur = float(m.group(4))
        spread = float(m.group(5)) if m.group(5) else 0.0

        color, opacity = parse_color_with_alpha(color_hex)
        if color is None:
            continue

        effect_type = "INNER_SHADOW" if is_inset else "DROP_SHADOW"
        effects.append({
            "type": effect_type,
            "color": color,
            "opacity": opacity,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "blur": blur,
            "spread": spread,
        })

    return effects


# ---------------------------------------------------------------------------
# Figma JS code generator
# ---------------------------------------------------------------------------


class FigmaCodeGen:
    """Generates Figma Plugin API JavaScript from a Paper tree."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._counter = 0
        self._fonts_needed: set[tuple[str, str]] = set()  # (family, style)

    def generate(self, tree: TreeNode, artboard_width: int, artboard_height: int) -> str:
        # Phase 1: collect all fonts needed
        self._collect_fonts(tree)

        # Phase 2: emit code
        self._lines = []
        L = self._lines
        L.append("(async () => { try {")

        # Load fonts
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
        """Emit the root artboard frame."""
        var = self._next_var()
        L = self._lines
        styles = node.styles

        L.append(f"  const {var} = figma.createFrame();")
        L.append(f"  page.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")
        L.append(f"  {var}.resize({width},{height});")

        # Background
        bg = styles.get("backgroundColor")
        if bg:
            color = parse_hex_color(bg)
            if color:
                L.append(
                    f"  {var}.fills = [{{type:'SOLID',"
                    f"color:{format_color(color)}}}];"
                )

        # Artboard layout
        flex_dir = styles.get("flexDirection", "row")
        if styles.get("display") == "flex":
            layout_mode = "VERTICAL" if flex_dir == "column" else "HORIZONTAL"
            L.append(f'  {var}.layoutMode = "{layout_mode}";')

            # Artboard sizing: fixed width, auto height
            L.append(f'  {var}.counterAxisSizingMode = "FIXED";')
            L.append(f'  {var}.primaryAxisSizingMode = "AUTO";')

            self._emit_padding(var, styles)
            self._emit_gap(var, styles)
            self._emit_justify(var, styles)

            # Artboards always use MIN so children can STRETCH to full width
            L.append(f'  {var}.counterAxisAlignItems = "MIN";')

        # Clip
        if styles.get("overflow") == "clip":
            L.append(f"  {var}.clipsContent = true;")

        L.append("")

        # Children
        for child in node.children:
            child_var = self._emit_node(child, var)
            self._emit_child_sizing(child_var, child, node)

        return var

    def _emit_node(self, node: TreeNode, parent_var: str) -> str:
        """Dispatch to the right emitter based on component type."""
        if node.component == "Text":
            return self._emit_text(node, parent_var)
        if node.component == "Rectangle":
            return self._emit_rectangle(node, parent_var)
        # Frame, or anything else: treat as frame
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
        # In Paper, frames with children or padding are effectively flex containers
        is_flex = has_explicit_flex or has_children or has_padding

        if is_flex:
            flex_dir = styles.get("flexDirection", "row")
            # Frames without explicit flex default to vertical stacking
            if not has_explicit_flex and flex_dir == "row":
                flex_dir = "column"
            layout_mode = "VERTICAL" if flex_dir == "column" else "HORIZONTAL"
            L.append(f'  {var}.layoutMode = "{layout_mode}";')

            self._emit_padding(var, styles)
            self._emit_gap(var, styles)
            self._emit_justify(var, styles)
            self._emit_align(var, styles)

            # Sizing modes for flex containers
            self._emit_frame_sizing(var, styles, layout_mode)
        else:
            # Non-flex, no children: use explicit dimensions (dividers, spacers)
            w = parse_px(styles.get("width"))
            h = parse_px(styles.get("height"))
            if w is not None and h is not None:
                L.append(f"  {var}.resize({w},{h});")
            elif w is not None:
                L.append(f"  {var}.resize({w},100);")
            elif h is not None:
                L.append(f"  {var}.resize(100,{h});")

        # Background
        bg = styles.get("backgroundColor")
        if bg:
            color = parse_hex_color(bg)
            if color:
                L.append(
                    f"  {var}.fills = [{{type:'SOLID',"
                    f"color:{format_color(color)}}}];"
                )
        else:
            # No background = transparent frame
            L.append(f"  {var}.fills = [];")

        # Border radius
        self._emit_border_radius(var, styles)

        # Clip
        if styles.get("overflow") == "clip":
            L.append(f"  {var}.clipsContent = true;")

        # Box shadow
        shadow = styles.get("boxShadow")
        if shadow:
            effects = parse_box_shadow(shadow)
            if effects:
                self._emit_effects(var, effects)

        L.append("")

        # Children
        for child in node.children:
            child_var = self._emit_node(child, var)
            if is_flex:
                self._emit_child_sizing(child_var, child, node)

        return var

    def _emit_text(self, node: TreeNode, parent_var: str) -> str:
        var = self._next_var()
        L = self._lines
        styles = node.styles

        L.append(f"  const {var} = figma.createText();")
        L.append(f"  {parent_var}.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")

        # Font
        family = map_font_family(styles.get("fontFamily", "Inter"))
        weight = styles.get("fontWeight", 400)
        style_name = map_font_weight(weight)
        L.append(
            f"  {var}.fontName = {{family:{json.dumps(family)},"
            f"style:{json.dumps(style_name)}}};"
        )

        # Font size
        font_size = parse_px(styles.get("fontSize"))
        if font_size:
            L.append(f"  {var}.fontSize = {font_size};")

        # Letter spacing
        ls = parse_letter_spacing(str(styles.get("letterSpacing", "")))
        if ls:
            L.append(f"  {var}.letterSpacing = {ls};")

        # Line height
        lh = parse_line_height(styles.get("lineHeight"))
        if lh:
            L.append(f"  {var}.lineHeight = {lh};")

        # Auto-resize: text nodes auto-size by default
        L.append(f'  {var}.textAutoResize = "WIDTH_AND_HEIGHT";')

        # Text content
        text = node.text_content or node.name
        L.append(f"  {var}.characters = {json.dumps(text, ensure_ascii=False)};")

        # Use actual Paper dimensions for text width constraint
        if node.node_width and node.node_width > 0:
            max_w = styles.get("maxWidth")
            width_str = styles.get("width")
            if max_w or (width_str and width_str not in ("auto", "fit-content")):
                L.append(f'  {var}.textAutoResize = "HEIGHT";')
                L.append(f"  {var}.resize({node.node_width},{node.node_height or 100});")

        # Color
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

        # Check for background image
        bg_image = styles.get("backgroundImage", "")
        image_url = None
        if bg_image.startswith("url("):
            m = re.match(r"url\(([^)]+)\)", bg_image)
            if m:
                image_url = m.group(1).strip("'\"")

        L.append(f"  const {var} = figma.createRectangle();")
        L.append(f"  {parent_var}.appendChild({var});")
        L.append(f"  {var}.name = {json.dumps(node.name, ensure_ascii=False)};")

        # Size
        w = parse_px(styles.get("width"))
        h = parse_px(styles.get("height"))
        if w and h:
            L.append(f"  {var}.resize({w},{h});")

        if image_url:
            # Gray placeholder for images
            L.append(
                f"  {var}.fills = [{{type:'SOLID',"
                f"color:{{r:0.85,g:0.85,b:0.85}}}}];"
            )
            L.append(f"  // Image URL: {image_url}")
        else:
            bg = styles.get("backgroundColor")
            if bg:
                color = parse_hex_color(bg)
                if color:
                    L.append(
                        f"  {var}.fills = [{{type:'SOLID',"
                        f"color:{format_color(color)}}}];"
                    )

        # Border radius
        self._emit_border_radius(var, styles)

        L.append("")
        return var

    def _emit_padding(self, var: str, styles: dict) -> None:
        L = self._lines
        # Check paddingBlock/paddingInline (shorthand)
        pb = parse_px(styles.get("paddingBlock"))
        pi = parse_px(styles.get("paddingInline"))
        # Individual paddings override shorthands
        pt = parse_px(styles.get("paddingTop"))
        pr = parse_px(styles.get("paddingRight"))
        pbot = parse_px(styles.get("paddingBottom"))
        pl = parse_px(styles.get("paddingLeft"))

        top = pt if pt is not None else (pb if pb is not None else 0)
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
            "baseline": "MIN",  # Figma has no baseline; closest is MIN
        }
        mapped = ai_map.get(ai)
        if mapped:
            self._lines.append(f'  {var}.counterAxisAlignItems = "{mapped}";')

    def _emit_frame_sizing(self, var: str, styles: dict, layout_mode: str) -> None:
        """Set sizing modes for flex containers."""
        L = self._lines
        w = styles.get("width")
        h = styles.get("height")

        if layout_mode == "VERTICAL":
            # Primary axis = vertical (height)
            h_px = parse_px(h) if h else None
            if h_px is not None and h != "fit-content":
                L.append(f'  {var}.primaryAxisSizingMode = "FIXED";')
            else:
                L.append(f'  {var}.primaryAxisSizingMode = "AUTO";')

            # Counter axis = horizontal (width)
            if w == "100%":
                pass  # handled by parent's child sizing
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
            # Primary axis = horizontal (width)
            w_px = parse_px(w) if w else None
            if w == "100%" or w == "fit-content" or w is None:
                # Will be sized by parent stretch or hug — use FIXED so
                # SPACE_BETWEEN distributes children across the full width
                L.append(f'  {var}.primaryAxisSizingMode = "FIXED";')
            elif w_px is not None:
                L.append(f'  {var}.primaryAxisSizingMode = "FIXED";')
            else:
                L.append(f'  {var}.primaryAxisSizingMode = "AUTO";')

            # Counter axis = vertical (height)
            h_px = parse_px(h) if h else None
            if h_px is not None and h != "fit-content":
                L.append(f'  {var}.counterAxisSizingMode = "FIXED";')
                L.append(f"  {var}.resize({var}.width,{h_px});")
            else:
                L.append(f'  {var}.counterAxisSizingMode = "AUTO";')

    def _emit_child_sizing(self, child_var: str, child: TreeNode, parent: TreeNode) -> None:
        """Set layoutAlign/layoutGrow on child based on its styles."""
        L = self._lines
        styles = child.styles
        parent_styles = parent.styles

        flex_dir = parent_styles.get("flexDirection", "row")
        is_vertical = flex_dir == "column"

        w = styles.get("width")
        h = styles.get("height")
        flex_grow = styles.get("flexGrow")
        flex_basis = styles.get("flexBasis")

        if is_vertical:
            # Parent is vertical: primary=height, counter=width
            # Width 100% -> stretch across counter axis
            if w == "100%":
                L.append(f'  {child_var}.layoutAlign = "STRETCH";')

            # flexGrow -> grow along primary axis
            if flex_grow and str(flex_grow) not in ("0", ""):
                L.append(f"  {child_var}.layoutGrow = 1;")

            # Explicit width
            if w and w != "100%" and w != "auto":
                w_px = parse_px(w)
                if w_px is not None:
                    L.append(f'  {child_var}.layoutAlign = "INHERIT";')

            # flexBasis with % -> grow
            if flex_basis and "0%" in str(flex_basis) and flex_grow and str(flex_grow) != "0":
                L.append(f"  {child_var}.layoutGrow = 1;")

        else:
            # Parent is horizontal: primary=width, counter=height
            # Height 100% -> stretch across counter axis
            if h == "100%":
                L.append(f'  {child_var}.layoutAlign = "STRETCH";')

            # flexGrow -> grow along primary axis
            if flex_grow and str(flex_grow) not in ("0", ""):
                L.append(f"  {child_var}.layoutGrow = 1;")

            # Explicit height
            explicit_h = parse_px(h)
            if explicit_h and h != "fit-content":
                pass  # height is set by the frame itself

            # flexBasis with 0% + grow -> fill
            if flex_basis and "0%" in str(flex_basis) and flex_grow and str(flex_grow) != "0":
                L.append(f"  {child_var}.layoutGrow = 1;")

    def _emit_border_radius(self, var: str, styles: dict) -> None:
        L = self._lines
        # Try uniform first
        uniform = parse_px(styles.get("borderRadius"))
        if uniform is not None and uniform > 0:
            L.append(f"  {var}.cornerRadius = {uniform};")
            return

        # Individual corners
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def convert_artboard(
    client: PaperMCPClient,
    artboard: dict,
) -> str:
    """Read one artboard from Paper and generate Figma JS."""
    artboard_id = artboard["id"]
    name = artboard["name"]
    width = artboard["width"]
    height = artboard["height"]

    log.info("Building tree for '%s' (%s)...", name, artboard_id)
    tree = build_tree(client, artboard_id, name, "Frame")
    attach_styles(client, tree)

    log.info("Generating Figma JS for '%s'...", name)
    gen = FigmaCodeGen()
    js_code = gen.generate(tree, width, height)

    return js_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Paper Design artboards to Figma"
    )
    parser.add_argument(
        "--artboard",
        help="Specific artboard ID to convert (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Output generated JS without pushing to Figma",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9224,
        help="Desktop Bridge WebSocket port (default: 9224)",
    )
    parser.add_argument(
        "--output",
        help="Save JS to file instead of stdout (with --dry-run)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    # Connect to Paper MCP
    log.info("Connecting to Paper MCP at %s...", PAPER_MCP_URL)
    try:
        client = PaperMCPClient()
        client.initialize()
    except requests.ConnectionError:
        log.error(
            "Cannot connect to Paper MCP at %s. "
            "Is Paper Design running?",
            PAPER_MCP_URL,
        )
        sys.exit(1)

    # Get artboard list
    info = client.get_basic_info()
    artboards = info.get("artboards", [])
    log.info(
        "Found %d artboards in '%s'",
        len(artboards),
        info.get("fileName", "?"),
    )

    # Filter if specific artboard requested
    if args.artboard:
        artboards = [a for a in artboards if a["id"] == args.artboard]
        if not artboards:
            log.error("Artboard '%s' not found", args.artboard)
            available = ", ".join(f"{a['id']} ({a['name']})" for a in info["artboards"])
            log.error("Available: %s", available)
            sys.exit(1)

    # Generate JS for each artboard
    js_outputs: list[tuple[str, str]] = []  # (name, js_code)
    for artboard in artboards:
        js_code = convert_artboard(client, artboard)
        js_outputs.append((artboard["name"], js_code))
        log.info(
            "Generated %d bytes of JS for '%s'",
            len(js_code),
            artboard["name"],
        )

    # Dry run: output JS
    if args.dry_run:
        for name, js_code in js_outputs:
            if args.output:
                out_path = Path(args.output)
                if len(js_outputs) > 1:
                    safe_name = re.sub(r"[^\w\-.]", "_", name)
                    out_path = out_path.parent / f"{safe_name}.js"
                out_path.write_text(js_code, encoding="utf-8")
                log.info("Saved: %s", out_path)
            else:
                print(f"// === {name} ===")
                print(js_code)
                print()
        return

    # Push to Figma via Desktop Bridge
    log.info("Starting Desktop Bridge on port %d...", args.port)
    log.info("Configure the Desktop Bridge Figma plugin to connect to ws://127.0.0.1:%d", args.port)

    sys.path.insert(0, str(Path(__file__).parent / "services" / "design-converter"))
    from adapters.figma.writer import _DesktopBridge

    bridge = _DesktopBridge(port=args.port, connect_timeout=60.0)
    try:
        bridge.start()
        for name, js_code in js_outputs:
            log.info("Pushing '%s' to Figma...", name)
            t0 = time.time()
            response = bridge.execute_code(js_code, timeout_ms=60000)
            elapsed = time.time() - t0

            result = response.get("result", {})
            if isinstance(result, dict) and result.get("success"):
                log.info(
                    "Created '%s' (nodeId=%s) in %.1fs",
                    result.get("nodeName", name),
                    result.get("nodeId", "?"),
                    elapsed,
                )
            else:
                error = (
                    result.get("error", "")
                    if isinstance(result, dict)
                    else response.get("error", str(response))
                )
                log.error("Failed to create '%s': %s", name, error)
    except TimeoutError as e:
        log.error("Bridge timeout: %s", e)
        sys.exit(1)
    except ConnectionError as e:
        log.error("Bridge connection error: %s", e)
        sys.exit(1)
    finally:
        bridge.close()

    log.info("Done.")


if __name__ == "__main__":
    main()
