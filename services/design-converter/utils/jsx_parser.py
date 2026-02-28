"""
JSX / HTML Inline-Style Parser
================================
Parses Paper's ``get_jsx(mode="inline-styles")`` output into a UNNode tree.

Paper outputs React JSX with camelCase inline styles:

    <div style={{width: '390px', backgroundColor: '#050508', display: 'flex'}}>
        <span style={{fontSize: '16px', color: '#FFFFFF'}}>Hello</span>
    </div>

Strategy
--------
1. Normalize JSX → pseudo-HTML by converting ``style={{...}}`` → ``style="..."``
2. Use Python's ``html.parser`` to build a lightweight DOM tree
3. Map HTML/JSX tag names to UNNode types
4. Apply CSS from each element's style attribute via ``apply_css_to_node``
5. Recursively assemble the UNNode tree

Public API
----------
    parse_jsx(jsx_str, root_name="Screen") -> Optional[UNNode]
    parse_jsx_component(jsx_str, component_name="") -> Optional[UNNode]
    extract_jsx_from_component(jsx_str) -> str
"""

from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

# ── Path bootstrap so this file works when run directly ───────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ir.nodes import (
    AlignItems,
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
    UNStrokeThickness,
    UNTextStyle,
)

from utils.css import apply_css_to_node, merge_styles

# ===========================================================================
# Tag classification tables
# ===========================================================================

# Tags that map to FRAME (container nodes)
_BLOCK_TAGS: frozenset[str] = frozenset(
    {
        "div",
        "section",
        "article",
        "aside",
        "header",
        "footer",
        "main",
        "nav",
        "ul",
        "ol",
        "li",
        "form",
        "fieldset",
        "figure",
        "figcaption",
        "details",
        "summary",
        "dialog",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
        "colgroup",
        "col",
    }
)

# Tags that map to TEXT nodes
_TEXT_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "label",
        "a",
        "strong",
        "em",
        "b",
        "i",
        "small",
        "sub",
        "sup",
        "code",
        "pre",
        "blockquote",
        "abbr",
        "cite",
        "time",
        "mark",
        "del",
        "ins",
        "kbd",
        "samp",
        "var",
        "button",  # visually text-like in design tools
    }
)

# SVG container tags
_SVG_CONTAINER_TAGS: frozenset[str] = frozenset({"svg", "g", "defs", "symbol", "use"})

# SVG shape tags
_SVG_SHAPE_TAGS: frozenset[str] = frozenset(
    {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
)

# Image/media tags
_IMAGE_TAGS: frozenset[str] = frozenset({"img", "image", "picture", "video"})

# Tags we silently skip
_IGNORE_TAGS: frozenset[str] = frozenset(
    {
        "br",
        "hr",
        "input",
        "textarea",
        "select",
        "option",
        "optgroup",
        "meta",
        "link",
        "script",
        "style",
        "noscript",
        "template",
        "slot",
        "source",
        "track",
        "wbr",
    }
)

# Transparent wrapper tags that dissolve into their children
_TRANSPARENT_TAGS: frozenset[str] = frozenset(
    {"html", "body", "head", "root", "react.fragment", "fragment"}
)

# HTML void elements (no closing tag needed)
_VOID_ELEMENTS: frozenset[str] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
        # SVG shapes are also self-closing in JSX
        "path",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "rect",
        "use",
    }
)

# ===========================================================================
# camelCase → kebab-case
# ===========================================================================

_UPPER_RE = re.compile(r"([A-Z])")


def _camel_to_kebab(name: str) -> str:
    """``fontSize`` → ``font-size``, ``backgroundColor`` → ``background-color``."""
    # Handle vendor prefixes (WebkitTransform → -webkit-transform)
    if name.startswith("Webkit"):
        name = "webkit" + name[6:]
    elif name.startswith("Moz"):
        name = "moz" + name[3:]
    elif name.startswith("Ms"):
        name = "ms" + name[2:]
    return _UPPER_RE.sub(r"-\1", name).lower()


# CSS properties that accept bare numbers as px values
_PX_PROPERTIES: frozenset[str] = frozenset(
    {
        "width",
        "height",
        "min-width",
        "min-height",
        "max-width",
        "max-height",
        "top",
        "left",
        "right",
        "bottom",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "font-size",
        "line-height",
        "letter-spacing",
        "word-spacing",
        "border-radius",
        "border-top-left-radius",
        "border-top-right-radius",
        "border-bottom-left-radius",
        "border-bottom-right-radius",
        "border-width",
        "border-top-width",
        "border-right-width",
        "border-bottom-width",
        "border-left-width",
        "gap",
        "row-gap",
        "column-gap",
        "flex-basis",
        "outline-width",
        "outline-offset",
        "stroke-width",
        "r",
        "rx",
        "ry",
        "cx",
        "cy",
        "x",
        "y",
        "x1",
        "x2",
        "y1",
        "y2",
    }
)

# ===========================================================================
# JSX style-object → CSS string
# ===========================================================================

# Match: propName: 'value' | "value" | bareNumber | true | false
_STYLE_PAIR_RE = re.compile(
    r"(\w+)\s*:\s*"
    r"(?:"
    r"'([^'\\]*(?:\\.[^'\\]*)*)'|"  # single-quoted string
    r'"([^"\\]*(?:\\.[^"\\]*)*)"|'  # double-quoted string
    r"((?:\d+\.?\d*|\.\d+)(?:[a-z%]*)?)|"  # number (with optional unit)
    r"(true|false|null|undefined)"  # boolean/null literals
    r")",
    re.MULTILINE | re.DOTALL,
)

# Non-CSS React props to discard
_REACT_PROPS: frozenset[str] = frozenset(
    {
        "key",
        "ref",
        "className",
        "htmlFor",
        "dangerouslySetInnerHTML",
        "children",
        "defaultValue",
        "defaultChecked",
    }
)


def _jsx_style_obj_to_css(style_obj_str: str) -> str:
    """
    Convert the *contents* of a JSX style object to a CSS string.

    Input:  ``width: '390px', backgroundColor: '#fff', opacity: 0.8``
    Output: ``width: 390px; background-color: #fff; opacity: 0.8``
    """
    css_parts: list[str] = []

    for m in _STYLE_PAIR_RE.finditer(style_obj_str):
        prop_raw = m.group(1)

        if prop_raw in _REACT_PROPS:
            continue

        # Determine value
        val_single = m.group(2)
        val_double = m.group(3)
        val_num = m.group(4)
        val_bool = m.group(5)

        if val_single is not None:
            val = val_single
        elif val_double is not None:
            val = val_double
        elif val_num is not None:
            # Bare number — add px for dimension properties
            css_prop = _camel_to_kebab(prop_raw)
            if "." in val_num or val_num == "0":
                # float or zero — keep as-is for opacity/flex/etc.
                if css_prop in _PX_PROPERTIES and not any(
                    c.isalpha() or c == "%" for c in val_num
                ):
                    val = f"{val_num}px"
                else:
                    val = val_num
            else:
                if css_prop in _PX_PROPERTIES and not any(
                    c.isalpha() or c == "%" for c in val_num
                ):
                    val = f"{val_num}px"
                else:
                    val = val_num
            css_parts.append(f"{css_prop}: {val}")
            continue
        elif val_bool is not None:
            # Skip boolean props — they don't translate to CSS
            continue
        else:
            continue

        css_prop = _camel_to_kebab(prop_raw)
        css_parts.append(f"{css_prop}: {val}")

    return "; ".join(css_parts)


# ===========================================================================
# JSX → pseudo-HTML normalizer
# ===========================================================================


def _replace_style_blocks(jsx: str) -> str:
    """
    Replace ``style={{...}}`` with ``style="css_string"``.

    Handles nested braces and quoted strings inside the object.
    """
    result: list[str] = []
    i = 0
    n = len(jsx)
    marker = "style={{"

    while i < n:
        idx = jsx.find(marker, i)
        if idx == -1:
            result.append(jsx[i:])
            break

        result.append(jsx[i:idx])

        # Walk forward to find the matching closing }}
        start = idx + len(marker)
        depth = 2  # already inside {{ → depth 2
        j = start

        while j < n and depth > 0:
            ch = jsx[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            elif ch in ('"', "'", "`"):
                # Skip quoted string
                quote = ch
                j += 1
                while j < n:
                    if jsx[j] == "\\" and quote != "`":
                        j += 2
                        continue
                    if jsx[j] == quote:
                        break
                    j += 1
            j += 1

        # inner is between {{ and }}
        inner = jsx[start : j - 2] if j >= 2 else jsx[start:j]
        css = _jsx_style_obj_to_css(inner)
        result.append(f'style="{css}"')
        i = j

    return "".join(result)


def _normalize_jsx(jsx: str) -> str:
    """
    Convert JSX markup to something ``html.parser`` can process.

    Steps:
    1. Replace ``style={{...}}`` → ``style="..."``
    2. Replace ``className=`` → ``class=``
    3. Remove React event handlers (``onClick={...}``, etc.)
    4. Replace remaining ``prop={expr}`` → ``prop=""``
    5. Replace JSX comments ``{/* ... */}`` → empty
    6. Replace ``<>`` / ``</>`` fragments → ``<div>`` / ``</div>``
    """
    # 1. Style blocks
    result = _replace_style_blocks(jsx)

    # 2. Fragment shorthand  <>  </>
    result = re.sub(r"<>", "<div>", result)
    result = re.sub(r"</>", "</div>", result)

    # 3. JSX comments {/* ... */}
    result = re.sub(r"\{/\*.*?\*/\}", "", result, flags=re.DOTALL)

    # 4. className → class
    result = re.sub(r"\bclassName=", "class=", result)

    # 5. htmlFor → for
    result = re.sub(r"\bhtmlFor=", "for=", result)

    # 6. Remove event handlers: onXxx={...}
    result = re.sub(r"\bon[A-Z]\w*=\{[^{}]*\}", "", result)

    # 7. Replace remaining {expression} attributes with empty string
    # e.g. src={imageUrl}  →  src=""
    result = re.sub(r"(\w[\w-]*)=\{[^{}]*\}", r'\1=""', result)

    # 8. Remove any leftover bare {expressions} not inside attributes
    result = re.sub(r"\{(?![^{}]*=>)[^{}]*\}", "", result)

    return result


# ===========================================================================
# Lightweight DOM tree
# ===========================================================================


class _DomNode:
    """Minimal DOM node produced by the parser."""

    __slots__ = ("tag", "attrs", "children", "text_parts", "parent")

    def __init__(self, tag: str, attrs: dict[str, str]) -> None:
        self.tag: str = tag.lower().strip()
        self.attrs: dict[str, str] = attrs
        self.children: list["_DomNode"] = []
        self.text_parts: list[str] = []
        self.parent: Optional["_DomNode"] = None

    @property
    def text(self) -> str:
        return " ".join(p.strip() for p in self.text_parts if p.strip())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<_DomNode <{self.tag}> children={len(self.children)}>"


# ===========================================================================
# HTML → DOM parser
# ===========================================================================


class _DomBuilder(HTMLParser):
    """Build a _DomNode tree from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _DomNode("root", {})
        self._stack: list[_DomNode] = [self.root]

    # ── Internal ──────────────────────────────────────────────────────────

    @property
    def _current(self) -> _DomNode:
        return self._stack[-1]

    def _push(self, node: _DomNode) -> None:
        self._current.children.append(node)
        node.parent = self._current
        self._stack.append(node)

    def _pop_to(self, tag: str) -> None:
        """Pop the stack until we find the matching open tag."""
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                self._stack = self._stack[:i]
                return

    # ── HTMLParser overrides ───────────────────────────────────────────────

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lc = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        node = _DomNode(tag_lc, attr_dict)
        self._current.children.append(node)
        node.parent = self._current
        if tag_lc not in _VOID_ELEMENTS:
            self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag_lc = tag.lower()
        if len(self._stack) > 1:
            self._pop_to(tag_lc)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Self-closing tag ``<path d="..." />``."""
        tag_lc = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        node = _DomNode(tag_lc, attr_dict)
        self._current.children.append(node)
        node.parent = self._current
        # Do NOT push — it's self-closing

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped and len(self._stack) > 1:
            self._current.text_parts.append(stripped)


# ===========================================================================
# Auto-incrementing ID generator
# ===========================================================================

_counter = 0


def _new_id(prefix: str = "jsx") -> str:
    global _counter
    _counter += 1
    return f"{prefix}-{_counter:04d}"


def reset_id_counter() -> None:
    """Reset the ID counter — useful in tests."""
    global _counter
    _counter = 0


# ===========================================================================
# DOM node → NodeType inference
# ===========================================================================


def _infer_node_type(dom: _DomNode) -> Optional[NodeType]:
    """
    Map a DOM tag to a UNNode NodeType.

    Returns ``None`` for nodes that should be silently dropped.
    """
    tag = dom.tag

    if tag in _IGNORE_TAGS:
        return None

    if tag in _IMAGE_TAGS:
        return NodeType.IMAGE

    if tag in _SVG_CONTAINER_TAGS:
        return NodeType.FRAME

    if tag == "path" or tag in ("line", "polyline", "polygon"):
        return NodeType.PATH

    if tag in ("circle", "ellipse"):
        return NodeType.ELLIPSE

    if tag == "rect":
        return NodeType.RECTANGLE

    if tag in _TEXT_TAGS:
        # Only treat as TEXT if no block-level children
        has_block_children = any(c.tag in _BLOCK_TAGS for c in dom.children)
        if not has_block_children:
            return NodeType.TEXT
        # Degrade to FRAME if it wraps block content
        return NodeType.FRAME

    if tag in _BLOCK_TAGS:
        return NodeType.FRAME

    # Unknown tag — treat as FRAME
    return NodeType.FRAME


# ===========================================================================
# CSS dict parser helper
# ===========================================================================


def _parse_css_for_dom(dom: _DomNode) -> dict[str, Any]:
    """Extract and merge inline style + class from a _DomNode."""
    style_str = dom.attrs.get("style", "")
    class_str = dom.attrs.get("class", "")
    return merge_styles(class_str, style_str)


# ===========================================================================
# DOM → UNNode recursive converter
# ===========================================================================


def _collect_text(dom: _DomNode) -> str:
    """
    Collect all visible text content from a DOM subtree.
    Used for TEXT nodes that may wrap nested inline elements.
    """
    parts: list[str] = [dom.text] if dom.text else []
    for child in dom.children:
        if child.tag in _TEXT_TAGS or child.tag in _IGNORE_TAGS:
            parts.append(_collect_text(child))
    return " ".join(p for p in parts if p).strip()


def _dom_to_un_node(dom: _DomNode, depth: int = 0) -> Optional[UNNode]:
    """
    Recursively convert a ``_DomNode`` subtree into a ``UNNode`` tree.

    Returns ``None`` for nodes that produce no useful design content.
    """
    tag = dom.tag

    # ── Transparent wrappers ──────────────────────────────────────────────
    if tag in _TRANSPARENT_TAGS:
        valid_children = [
            child
            for child in dom.children
            if (child_node := _dom_to_un_node(child, depth)) is not None
            and (child_node,)  # noqa: B023 — just checking truthiness
        ]
        # Re-convert (the comprehension above drops results)
        converted: list[UNNode] = []
        for child in dom.children:
            n = _dom_to_un_node(child, depth)
            if n is not None:
                converted.append(n)

        if len(converted) == 1:
            return converted[0]
        if not converted:
            return None
        wrapper = UNNode(
            type=NodeType.FRAME,
            id=_new_id("root"),
            name="Root",
            source_tool="paper",
        )
        wrapper.children.extend(converted)
        return wrapper

    # ── Ignored tags ──────────────────────────────────────────────────────
    if tag in _IGNORE_TAGS:
        return None

    # ── Infer type ────────────────────────────────────────────────────────
    ntype = _infer_node_type(dom)
    if ntype is None:
        return None

    # ── CSS parsing ───────────────────────────────────────────────────────
    css = _parse_css_for_dom(dom)

    # ── Build base UNNode ─────────────────────────────────────────────────
    # Determine a human-readable name
    node_name = (
        dom.attrs.get("data-name")
        or dom.attrs.get("data-layer")
        or dom.attrs.get("aria-label")
        or dom.attrs.get("id")
        or dom.attrs.get("alt")
        or (dom.text[:32] if dom.text else "")
        or tag
    )

    node = UNNode(
        type=ntype,
        id=_new_id(tag),
        name=node_name[:64],
        source_tool="paper",
        source_id=dom.attrs.get("id", ""),
    )

    # Apply CSS properties to the node
    apply_css_to_node(css, node)

    # ── Type-specific post-processing ─────────────────────────────────────

    if ntype == NodeType.TEXT:
        content = _collect_text(dom)
        if not content:
            return None
        node.text_content = content
        node.name = content[:32]
        return node

    if ntype == NodeType.IMAGE:
        node.image_url = (
            dom.attrs.get("src")
            or dom.attrs.get("href")
            or dom.attrs.get("data-src")
            or ""
        )
        node.image_mode = ImageFillMode.FILL
        node.name = dom.attrs.get("alt", "Image") or "Image"
        return node

    if ntype == NodeType.PATH:
        node.geometry = dom.attrs.get("d", "")
        fill_raw = dom.attrs.get("fill", "")
        stroke_raw = dom.attrs.get("stroke", "")
        if fill_raw and fill_raw not in ("none", "transparent", ""):
            try:
                from utils.color import parse_css_color

                hex_c = parse_css_color(fill_raw)
                node.fills = [UNSolidFill(color=UNColor.from_hex(hex_c))]
            except Exception:
                pass
        if stroke_raw and stroke_raw not in ("none", ""):
            try:
                from utils.color import parse_css_color

                hex_c = parse_css_color(stroke_raw)
                sw = float(dom.attrs.get("stroke-width", "1") or "1")
                node.strokes = [
                    UNStroke(
                        fill=UNSolidFill(color=UNColor.from_hex(hex_c)),
                        thickness=UNStrokeThickness.uniform(sw),
                    )
                ]
            except Exception:
                pass
        return node

    if ntype == NodeType.ELLIPSE:
        # <circle cx r> or <ellipse cx cy rx ry>
        try:
            cx = float(dom.attrs.get("cx", 0))
            cy = float(dom.attrs.get("cy", 0))
            r = float(dom.attrs.get("r", 0))
            rx = float(dom.attrs.get("rx", r))
            ry = float(dom.attrs.get("ry", r))
            if rx > 0 and ry > 0:
                node.width = UNSize.fixed(rx * 2)
                node.height = UNSize.fixed(ry * 2)
                node.x = cx - rx
                node.y = cy - ry
        except (ValueError, TypeError):
            pass
        return node

    if ntype == NodeType.RECTANGLE:
        # SVG <rect x y width height rx ry>
        try:
            x = float(dom.attrs.get("x", 0))
            y = float(dom.attrs.get("y", 0))
            w = float(dom.attrs.get("width", node.width.value or 0))
            h = float(dom.attrs.get("height", node.height.value or 0))
            corner = float(dom.attrs.get("rx", dom.attrs.get("ry", 0)))
            node.x = x
            node.y = y
            if w:
                node.width = UNSize.fixed(w)
            if h:
                node.height = UNSize.fixed(h)
            if corner:
                node.corner_radius = UNCornerRadius.all(corner)
        except (ValueError, TypeError):
            pass
        return node

    # ── FRAME / GROUP: recurse into children ──────────────────────────────

    for child_dom in dom.children:
        child_node = _dom_to_un_node(child_dom, depth + 1)
        if child_node is not None:
            node.children.append(child_node)

    # If the container has direct text but no text child yet, inject one
    if dom.text and ntype == NodeType.FRAME:
        # Only if we don't already have a text child from children
        has_text_child = any(c.type == NodeType.TEXT for c in node.children)
        if not has_text_child:
            text_node = UNNode(
                type=NodeType.TEXT,
                id=_new_id("text"),
                name=dom.text[:32],
                text_content=dom.text,
                source_tool="paper",
            )
            node.children.insert(0, text_node)

    return node


# ===========================================================================
# JSX component return-value extractor
# ===========================================================================


def extract_jsx_from_component(jsx_str: str) -> str:
    """
    Extract the root JSX element from a React function component string.

    Handles:
    - Bare JSX:                 ``<div>...</div>``
    - Parenthesized return:     ``return ( <div>...</div> );``
    - Unparenthesized return:   ``return <div>...</div>;``
    - Arrow body:               ``() => ( <div>...</div> )``
    - Named export:             ``export default function Comp() { ... }``

    Returns the original string unchanged if no component wrapper is detected.
    """
    # 1. Try return ( <jsx> )
    m = re.search(
        r"\breturn\s*\(\s*([\s\S]+?)\s*\)\s*;?\s*\}",
        jsx_str,
    )
    if m:
        candidate = m.group(1).strip()
        if candidate.startswith("<"):
            return candidate

    # 2. Try return <jsx>; (no parens)
    m = re.search(r"\breturn\s+(<[\s\S]+?>[\s\S]+?</\w+>)\s*;", jsx_str)
    if m:
        return m.group(1).strip()

    # 3. Try arrow => ( <jsx> )
    m = re.search(r"=>\s*\(\s*([\s\S]+?)\s*\)\s*;?\s*$", jsx_str, re.MULTILINE)
    if m:
        candidate = m.group(1).strip()
        if candidate.startswith("<"):
            return candidate

    # 4. Try arrow => <jsx> (no parens)
    m = re.search(r"=>\s*(<[\s\S]+?>[\s\S]+?</\w+>)\s*;?\s*$", jsx_str, re.MULTILINE)
    if m:
        return m.group(1).strip()

    return jsx_str


# ===========================================================================
# Public API
# ===========================================================================


def parse_jsx(jsx_str: str, root_name: str = "Screen") -> Optional[UNNode]:
    """
    Parse a JSX string (typically from Paper's ``get_jsx`` tool) and return
    a ``UNNode`` tree.

    Parameters
    ----------
    jsx_str:
        The raw JSX string.  May contain ``style={{...}}`` attribute syntax,
        ``className=``, event handlers, and other React-specific syntax.
    root_name:
        Name to assign to the root node if the result needs a synthetic wrapper.

    Returns
    -------
    A ``UNNode`` root node, or ``None`` if the input contains no parseable
    design content.

    Examples
    --------
    >>> tree = parse_jsx('<div style={{width: "390px", height: "844px"}}></div>')
    >>> tree.width.value
    390.0
    """
    if not jsx_str or not jsx_str.strip():
        return None

    # Normalize JSX → HTML
    html_str = _normalize_jsx(jsx_str)

    # Build DOM tree
    builder = _DomBuilder()
    try:
        builder.feed(html_str)
    except Exception:
        pass  # html.parser is lenient; swallow parse errors

    # Convert DOM → UNNode
    root = _dom_to_un_node(builder.root)

    if root is not None:
        # Give the root a meaningful name
        if not root.name or root.name in ("root", "Root", "div", "section"):
            root.name = root_name
        root.name = root_name if root.name in ("root", "Root") else root.name
    return root


def parse_jsx_component(
    jsx_str: str,
    component_name: str = "",
) -> Optional[UNNode]:
    """
    Parse a React function component string and return a ``UNNode`` tree.

    Extracts the JSX markup from the component's return value before parsing,
    so this works on full component source files as well as bare JSX snippets.

    Parameters
    ----------
    jsx_str:
        Full or partial React component source.  May be a bare JSX string,
        a function component body, or an arrow component expression.
    component_name:
        Name to assign to the root node (defaults to ``"Component"``).

    Returns
    -------
    A ``UNNode`` root node, or ``None``.

    Examples
    --------
    >>> src = '''
    ... function WalletScreen() {
    ...   return (
    ...     <div style={{width: '390px', height: '844px', backgroundColor: '#050508'}}>
    ...       <span style={{color: '#fff', fontSize: '24px'}}>Wallet</span>
    ...     </div>
    ...   );
    ... }
    ... '''
    >>> tree = parse_jsx_component(src, "WalletScreen")
    >>> tree.name
    'WalletScreen'
    """
    name = component_name or "Component"
    jsx = extract_jsx_from_component(jsx_str)
    return parse_jsx(jsx, root_name=name)
