"""
CSS / Tailwind → UNNode property parser
========================================
Handles two Paper-specific input formats:
  1. Tailwind class strings  (className="flex flex-col gap-[8px] bg-[#050508] ...")
  2. Inline JS style objects (style={{ backgroundColor: '#050508', ... }})

Outputs a flat dict of normalised CSS properties (kebab-case, px values as
floats) that the Paper reader then maps onto UNNode fields.

Key design rules
----------------
- No UNNode imports here — this is a pure string→dict transformation layer.
- All sizes are returned as raw floats (px) or the string "fill" / "hug".
- Colours are returned as raw hex strings; colour.py does deeper conversion.
- Every function is pure (no side effects, no I/O).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Tailwind spacing scale  (multiplier × 4 px)
# ---------------------------------------------------------------------------

_TW_SPACING: Dict[str, float] = {
    "px": 1,
    "0": 0,
    "0.5": 2,
    "1": 4,
    "1.5": 6,
    "2": 8,
    "2.5": 10,
    "3": 12,
    "3.5": 14,
    "4": 16,
    "5": 20,
    "6": 24,
    "7": 28,
    "8": 32,
    "9": 36,
    "10": 40,
    "11": 44,
    "12": 48,
    "14": 56,
    "16": 64,
    "20": 80,
    "24": 96,
    "28": 112,
    "32": 128,
    "36": 144,
    "40": 160,
    "44": 176,
    "48": 192,
    "52": 208,
    "56": 224,
    "60": 240,
    "64": 256,
    "72": 288,
    "80": 320,
    "96": 384,
}

# ---------------------------------------------------------------------------
# Tailwind font-size scale
# ---------------------------------------------------------------------------

_TW_FONT_SIZE: Dict[str, float] = {
    "xs": 12,
    "sm": 14,
    "base": 16,
    "lg": 18,
    "xl": 20,
    "2xl": 24,
    "3xl": 30,
    "4xl": 36,
    "5xl": 48,
    "6xl": 60,
    "7xl": 72,
    "8xl": 96,
    "9xl": 128,
}

# ---------------------------------------------------------------------------
# Tailwind font-weight scale
# ---------------------------------------------------------------------------

_TW_FONT_WEIGHT: Dict[str, str] = {
    "thin": "100",
    "extralight": "200",
    "light": "300",
    "normal": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700",
    "extrabold": "800",
    "black": "900",
}

# ---------------------------------------------------------------------------
# Tailwind border-radius scale
# ---------------------------------------------------------------------------

_TW_ROUNDED: Dict[str, float] = {
    "none": 0,
    "sm": 2,
    "": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
    "2xl": 16,
    "3xl": 24,
    "full": 9999,
}

# Border-radius side tokens → which corners they affect
_TW_ROUNDED_SIDES: Dict[str, List[str]] = {
    "t": ["tl", "tr"],
    "r": ["tr", "br"],
    "b": ["br", "bl"],
    "l": ["tl", "bl"],
    "tl": ["tl"],
    "tr": ["tr"],
    "br": ["br"],
    "bl": ["bl"],
}

# ---------------------------------------------------------------------------
# Named CSS colours (subset — extended as needed)
# ---------------------------------------------------------------------------

_NAMED_COLORS: Dict[str, str] = {
    "white": "#FFFFFF",
    "black": "#000000",
    "transparent": "#00000000",
    "red": "#FF0000",
    "green": "#008000",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "orange": "#FFA500",
    "purple": "#800080",
    "pink": "#FFC0CB",
    "gray": "#808080",
    "grey": "#808080",
    "inherit": "",
    "currentcolor": "",
}

# ---------------------------------------------------------------------------
# camelCase → kebab-case
# ---------------------------------------------------------------------------


def camel_to_kebab(name: str) -> str:
    """backgroundColor → background-color"""
    s = re.sub(r"([A-Z])", r"-\1", name)
    return s.lower().lstrip("-")


# ---------------------------------------------------------------------------
# Raw-value extraction helpers
# ---------------------------------------------------------------------------


def _parse_px(value: str) -> Optional[float]:
    """
    Extract a float from strings like '16px', '1.5rem', '24', '0.5'.
    rem is treated as ×16 for design purposes.
    Returns None if unparseable.
    """
    value = value.strip()
    m = re.match(r"^(-?[\d.]+)(px|rem|em|%)?$", value)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or "px"
    if unit == "rem":
        num *= 16
    return num


def _resolve_tw_spacing(token: str) -> Optional[float]:
    """Resolve a Tailwind spacing token like '4', '2.5', 'px' → float px."""
    # Custom value: [16px], [1.5rem], [24]
    m = re.match(r"^\[(-?[\d.]+)(px|rem|em)?\]$", token)
    if m:
        num = float(m.group(1))
        unit = m.group(2) or "px"
        if unit == "rem":
            num *= 16
        return num
    return _TW_SPACING.get(token)


def _resolve_color_token(token: str) -> Optional[str]:
    """
    Resolve a Tailwind color token.
    Handles:  [#050508]  [rgba(0,0,0,0.5)]  white  transparent
    Returns a hex/rgba string or None.
    """
    # Arbitrary value  [#hex]  [rgba(...)]
    m = re.match(r"^\[(.+)\]$", token)
    if m:
        inner = m.group(1).strip()
        # CSS hex
        if re.match(r"^#[0-9a-fA-F]{3,8}$", inner):
            return inner
        # rgba / rgb
        if inner.startswith("rgb"):
            return inner
        return inner  # return as-is, color.py will handle further
    # Named colour
    return _NAMED_COLORS.get(token.lower())


# ---------------------------------------------------------------------------
# Inline JS style object parser
# ---------------------------------------------------------------------------


def parse_inline_style(style_str: str) -> Dict[str, str]:
    """
    Parse a React/JSX inline style object string into a CSS dict.

    Input:  "{ backgroundColor: '#050508', translate: '-50% -50%',
               borderTopWidth: '0.5px', display: 'flex' }"
    Output: { "background-color": "#050508", "translate": "-50% -50%", ... }

    Handles:
      - camelCase keys → kebab-case
      - Quoted string values (single or double)
      - Numeric values  (e.g.  fontSize: 14 → "14")
      - Nested template strings (best-effort)
    """
    # Strip outer braces / extra whitespace
    s = style_str.strip()
    for wrapper in ("{{", "}}", "{", "}"):
        if s.startswith(wrapper[0]) and s.endswith(wrapper[-1]):
            s = s[len(wrapper[0]) : len(s) - len(wrapper[-1])].strip()
            break

    result: Dict[str, str] = {}

    # Tokenise key: value pairs respecting nested parens / brackets / quotes
    i = 0
    while i < len(s):
        # Skip whitespace and commas
        while i < len(s) and s[i] in " \t\n\r,":
            i += 1
        if i >= len(s):
            break

        # Read key (identifier)
        key_start = i
        while i < len(s) and s[i] not in ":= \t\n\r":
            i += 1
        key = s[key_start:i].strip().strip("\"'")
        if not key:
            i += 1
            continue

        # Skip to colon
        while i < len(s) and s[i] != ":":
            i += 1
        i += 1  # skip ':'

        # Skip whitespace
        while i < len(s) and s[i] in " \t\n\r":
            i += 1

        if i >= len(s):
            break

        # Read value — respect quotes, parens, brackets
        value = _read_value(s, i)
        i += len(value)
        value = value.strip().strip("\"',").strip("\"'")

        css_key = camel_to_kebab(key)
        result[css_key] = value

    return result


def _read_value(s: str, start: int) -> str:
    """
    Read a JS value token starting at `start`, respecting nesting.
    Returns the raw substring including any surrounding quotes.
    """
    depth_paren = 0
    depth_bracket = 0
    in_single = False
    in_double = False
    i = start
    while i < len(s):
        c = s[i]
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if c == "(":
                depth_paren += 1
            elif c == ")":
                if depth_paren > 0:
                    depth_paren -= 1
            elif c == "[":
                depth_bracket += 1
            elif c == "]":
                if depth_bracket > 0:
                    depth_bracket -= 1
            elif c == "," and depth_paren == 0 and depth_bracket == 0:
                break
            elif c == "\n" and depth_paren == 0 and depth_bracket == 0:
                # End of value on new line (no trailing comma)
                break
        i += 1
    return s[start:i]


# ---------------------------------------------------------------------------
# Tailwind class parser — single class
# ---------------------------------------------------------------------------


def parse_tailwind_class(cls: str) -> Dict[str, Any]:
    """
    Parse a single Tailwind utility class into CSS-like property dict.

    Returns a dict with normalised keys, e.g.:
      "bg-[#050508]"  → { "background-color": "#050508" }
      "text-[11px]"   → { "font-size": 11.0 }
      "rounded-3xl"   → { "border-radius-tl": 24, "border-radius-tr": 24,
                           "border-radius-br": 24, "border-radius-bl": 24 }
      "flex"          → { "display": "flex" }
      "flex-col"      → { "flex-direction": "column" }
      "gap-[19px]"    → { "gap": 19.0 }
      "p-5"           → { "padding-top": 20, ... }
      "mb-6"          → { "margin-bottom": 24 }
      "w-full"        → { "width": "fill" }
      "h-fit"         → { "height": "hug" }
      "font-bold"     → { "font-weight": "700" }
      "uppercase"     → { "text-transform": "uppercase" }
      "shrink-0"      → { "flex-shrink": 0 }
      "overflow-clip" → { "overflow": "hidden" }
    """

    c = cls.strip()
    if not c or c.startswith("!"):  # ignore important modifier
        return {}

    # ── Display / Layout ───────────────────────────────────────────────────
    if c == "flex":
        return {"display": "flex"}
    if c == "inline-flex":
        return {"display": "inline-flex"}
    if c == "block":
        return {"display": "block"}
    if c == "hidden":
        return {"display": "none"}
    if c == "flex-col":
        return {"flex-direction": "column"}
    if c == "flex-row":
        return {"flex-direction": "row"}
    if c == "flex-wrap":
        return {"flex-wrap": "wrap"}
    if c == "flex-nowrap":
        return {"flex-wrap": "nowrap"}
    if c == "flex-1":
        return {"flex": "1"}
    if c == "flex-auto":
        return {"flex": "auto"}
    if c == "flex-none":
        return {"flex": "none"}
    if c == "shrink-0":
        return {"flex-shrink": 0}
    if c == "shrink":
        return {"flex-shrink": 1}
    if c == "grow":
        return {"flex-grow": 1}
    if c == "grow-0":
        return {"flex-grow": 0}

    # ── Position ───────────────────────────────────────────────────────────
    if c in ("relative", "absolute", "fixed", "sticky"):
        return {"position": c}
    if c == "inset-0":
        return {"top": 0, "right": 0, "bottom": 0, "left": 0}

    # top / right / bottom / left / inset
    for side in ("top", "right", "bottom", "left"):
        if c.startswith(f"{side}-") or c.startswith(f"-{side}-"):
            neg = c.startswith("-")
            val_tok = c.lstrip("-").split("-", 1)[1]
            px = _resolve_tw_spacing(val_tok)
            if px is not None:
                return {side: -px if neg else px}

    # inset-x / inset-y
    m = re.match(r"^inset-([xy])-(.+)$", c)
    if m:
        axis, tok = m.group(1), m.group(2)
        px = _resolve_tw_spacing(tok)
        if px is not None:
            if axis == "x":
                return {"left": px, "right": px}
            return {"top": px, "bottom": px}

    # ── Justify / Align ────────────────────────────────────────────────────
    justify_map = {
        "justify-start": "flex-start",
        "justify-center": "center",
        "justify-end": "flex-end",
        "justify-between": "space-between",
        "justify-around": "space-around",
        "justify-evenly": "space-evenly",
    }
    if c in justify_map:
        return {"justify-content": justify_map[c]}

    align_map = {
        "items-start": "flex-start",
        "items-center": "center",
        "items-end": "flex-end",
        "items-stretch": "stretch",
        "items-baseline": "baseline",
    }
    if c in align_map:
        return {"align-items": align_map[c]}

    self_align_map = {
        "self-start": "flex-start",
        "self-center": "center",
        "self-end": "flex-end",
        "self-stretch": "stretch",
    }
    if c in self_align_map:
        return {"align-self": self_align_map[c]}

    # ── Gap ────────────────────────────────────────────────────────────────
    m = re.match(r"^gap-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"gap": px}

    m = re.match(r"^gap-x-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"column-gap": px}

    m = re.match(r"^gap-y-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"row-gap": px}

    # ── Width ──────────────────────────────────────────────────────────────
    if c == "w-full":
        return {"width": "fill"}
    if c in ("w-fit", "w-auto"):
        return {"width": "hug"}
    if c == "w-screen":
        return {"width": "100vw"}
    if c == "w-px":
        return {"width": 1.0}

    m = re.match(r"^w-(.+)$", c)
    if m:
        tok = m.group(1)
        px = _resolve_tw_spacing(tok)
        if px is not None:
            return {"width": px}
        # Fraction e.g. w-1/2
        frac = re.match(r"^(\d+)/(\d+)$", tok)
        if frac:
            return {"width": f"{int(frac.group(1)) * 100 // int(frac.group(2))}%"}

    # ── Height ─────────────────────────────────────────────────────────────
    if c == "h-full":
        return {"height": "fill"}
    if c in ("h-fit", "h-auto"):
        return {"height": "hug"}
    if c == "h-screen":
        return {"height": "100vh"}
    if c == "h-px":
        return {"height": 1.0}

    m = re.match(r"^h-(.+)$", c)
    if m:
        tok = m.group(1)
        px = _resolve_tw_spacing(tok)
        if px is not None:
            return {"height": px}

    # ── Size (width + height together) ────────────────────────────────────
    if c == "size-full":
        return {"width": "fill", "height": "fill"}
    if c in ("size-fit", "size-auto"):
        return {"width": "hug", "height": "hug"}

    m = re.match(r"^size-(.+)$", c)
    if m:
        tok = m.group(1)
        px = _resolve_tw_spacing(tok)
        if px is not None:
            return {"width": px, "height": px}

    # ── Padding ────────────────────────────────────────────────────────────
    # p-* (all sides)
    m = re.match(r"^p-(.+)$", c)
    if (
        m
        and not c.startswith("px-")
        and not c.startswith("py-")
        and not c.startswith("pt-")
        and not c.startswith("pr-")
        and not c.startswith("pb-")
        and not c.startswith("pl-")
    ):
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {
                "padding-top": px,
                "padding-right": px,
                "padding-bottom": px,
                "padding-left": px,
            }

    # px-* / py-*
    m = re.match(r"^px-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"padding-left": px, "padding-right": px}

    m = re.match(r"^py-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"padding-top": px, "padding-bottom": px}

    # pt- pr- pb- pl-
    for side, prop in [
        ("pt", "padding-top"),
        ("pr", "padding-right"),
        ("pb", "padding-bottom"),
        ("pl", "padding-left"),
    ]:
        m = re.match(rf"^{side}-(.+)$", c)
        if m:
            px = _resolve_tw_spacing(m.group(1))
            if px is not None:
                return {prop: px}

    # ── Margin ─────────────────────────────────────────────────────────────
    m = re.match(r"^m-(.+)$", c)
    if m and not any(
        c.startswith(p) for p in ("mx-", "my-", "mt-", "mr-", "mb-", "ml-")
    ):
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {
                "margin-top": px,
                "margin-right": px,
                "margin-bottom": px,
                "margin-left": px,
            }

    m = re.match(r"^mx-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"margin-left": px, "margin-right": px}

    m = re.match(r"^my-(.+)$", c)
    if m:
        px = _resolve_tw_spacing(m.group(1))
        if px is not None:
            return {"margin-top": px, "margin-bottom": px}

    for side, prop in [
        ("mt", "margin-top"),
        ("mr", "margin-right"),
        ("mb", "margin-bottom"),
        ("ml", "margin-left"),
    ]:
        m = re.match(rf"^{side}-(.+)$", c)
        if m:
            px = _resolve_tw_spacing(m.group(1))
            if px is not None:
                return {prop: px}

    # ── Background colour ──────────────────────────────────────────────────
    m = re.match(r"^bg-(.+)$", c)
    if m:
        tok = m.group(1)
        # Gradient classes
        if tok.startswith("gradient-to-"):
            return {"background-type": "gradient", "background-gradient-dir": tok}
        col = _resolve_color_token(tok)
        if col is not None:
            return {"background-color": col} if col else {}
        # Named Tailwind colour like bg-slate-500
        return {"background-color-token": tok}

    # ── Text colour ────────────────────────────────────────────────────────
    m = re.match(r"^text-(.+)$", c)
    if m:
        tok = m.group(1)
        # Font size  (text-sm, text-[11px] …)
        fs = _TW_FONT_SIZE.get(tok)
        if fs:
            return {"font-size": fs}
        px = _resolve_tw_spacing(tok)
        if px is not None:
            return {"font-size": px}
        # Alignment
        if tok in ("left", "center", "right", "justify"):
            return {"text-align": tok}
        # Colour
        col = _resolve_color_token(tok)
        if col is not None:
            return {"color": col} if col else {}
        return {"color-token": tok}

    # ── Font weight ────────────────────────────────────────────────────────
    m = re.match(r"^font-(.+)$", c)
    if m:
        tok = m.group(1)
        w = _TW_FONT_WEIGHT.get(tok)
        if w:
            return {"font-weight": w}
        # font-family token (font-sans, font-mono, etc.)
        family_map = {
            "sans": "Inter, system-ui, sans-serif",
            "mono": "SF Mono, monospace",
            "serif": "Georgia, serif",
        }
        if tok in family_map:
            return {"font-family": family_map[tok]}

    # ── Letter-spacing (tracking) ──────────────────────────────────────────
    m = re.match(r"^tracking-(.+)$", c)
    if m:
        tok = m.group(1)
        tracking_map = {
            "tighter": -0.8,
            "tight": -0.4,
            "normal": 0,
            "wide": 0.4,
            "wider": 0.8,
            "widest": 1.6,
        }
        if tok in tracking_map:
            return {"letter-spacing": tracking_map[tok]}
        px = _resolve_tw_spacing(tok)
        if px is not None:
            return {"letter-spacing": px}

    # ── Line-height (leading) ──────────────────────────────────────────────
    m = re.match(r"^leading-(.+)$", c)
    if m:
        tok = m.group(1)
        leading_map = {
            "none": 1.0,
            "tight": 1.25,
            "snug": 1.375,
            "normal": 1.5,
            "relaxed": 1.625,
            "loose": 2.0,
        }
        if tok in leading_map:
            return {"line-height-multiplier": leading_map[tok]}  # relative
        px = _resolve_tw_spacing(tok)
        if px is not None:
            return {"line-height": px}

    # ── Text transform ─────────────────────────────────────────────────────
    if c in ("uppercase", "lowercase", "capitalize", "normal-case"):
        return {"text-transform": "none" if c == "normal-case" else c}

    # ── Text decoration ────────────────────────────────────────────────────
    if c == "underline":
        return {"text-decoration": "underline"}
    if c == "line-through":
        return {"text-decoration": "line-through"}
    if c == "no-underline":
        return {"text-decoration": "none"}

    # ── Border-radius ─────────────────────────────────────────────────────
    # rounded / rounded-{size} / rounded-{side} / rounded-{side}-{size}
    m = re.match(r"^rounded(?:-([trlb]{1,2}))?(?:-(.+))?$", c)
    if m:
        side_tok = m.group(1) or ""
        size_tok = m.group(2) or ""

        # Resolve radius value
        if size_tok in _TW_ROUNDED:
            r = _TW_ROUNDED[size_tok]
        elif re.match(r"^\[.+\]$", size_tok):
            px = _resolve_tw_spacing(size_tok)
            r = px if px is not None else 4.0
        elif size_tok == "":
            r = _TW_ROUNDED[""]  # default 4px
        else:
            r = _TW_ROUNDED.get(size_tok, 4.0)

        if side_tok == "":
            # All corners
            return {
                "border-radius-tl": r,
                "border-radius-tr": r,
                "border-radius-br": r,
                "border-radius-bl": r,
            }
        corners = _TW_ROUNDED_SIDES.get(side_tok, [])
        return {f"border-radius-{corner}": r for corner in corners}

    # ── Border ────────────────────────────────────────────────────────────
    # border-{side}-{color}  /  border-{side}-{width}  /  border-{color}
    m = re.match(r"^border(?:-([trlb]))?(?:-(.+))?$", c)
    if m:
        side = m.group(1)  # t / r / b / l  or None
        tok = m.group(2)  # width token or colour token

        side_prop = {None: "", "t": "top", "r": "right", "b": "bottom", "l": "left"}
        sp = side_prop.get(side, "")

        if tok is None:
            # bare "border" → 1px stroke all sides
            return {"border-width": 1.0}

        # Solid / dashed style
        if tok in ("solid", "dashed", "dotted", "none"):
            prop = f"border-{sp}-style" if sp else "border-style"
            return {prop: tok}

        # Width token
        border_widths = {"0": 0, "1": 1, "2": 2, "4": 4, "8": 8}
        if tok in border_widths:
            prop = f"border-{sp}-width" if sp else "border-width"
            return {prop: float(border_widths[tok])}
        px = _resolve_tw_spacing(tok)
        if px is not None:
            prop = f"border-{sp}-width" if sp else "border-width"
            return {prop: px}

        # Colour
        col = _resolve_color_token(tok)
        if col is not None:
            prop = f"border-{sp}-color" if sp else "border-color"
            return {prop: col} if col else {}

    # ── Opacity ───────────────────────────────────────────────────────────
    m = re.match(r"^opacity-(\d+)$", c)
    if m:
        return {"opacity": int(m.group(1)) / 100.0}

    # ── Overflow ──────────────────────────────────────────────────────────
    if c in ("overflow-hidden", "overflow-clip"):
        return {"overflow": "hidden"}
    if c == "overflow-visible":
        return {"overflow": "visible"}
    if c == "overflow-auto":
        return {"overflow": "auto"}
    if c == "overflow-scroll":
        return {"overflow": "scroll"}

    # ── Object-fit ────────────────────────────────────────────────────────
    m = re.match(r"^object-(.+)$", c)
    if m:
        return {"object-fit": m.group(1)}

    # ── Z-index ───────────────────────────────────────────────────────────
    m = re.match(r"^z-(\d+)$", c)
    if m:
        return {"z-index": int(m.group(1))}

    # ── Cursor ────────────────────────────────────────────────────────────
    m = re.match(r"^cursor-(.+)$", c)
    if m:
        return {"cursor": m.group(1)}

    # ── Pointer events ───────────────────────────────────────────────────
    if c == "pointer-events-none":
        return {"pointer-events": "none"}
    if c == "pointer-events-auto":
        return {"pointer-events": "auto"}

    # ── Aspect ratio ─────────────────────────────────────────────────────
    m = re.match(r"^aspect-(.+)$", c)
    if m:
        tok = m.group(1)
        aspect_map = {"auto": "auto", "square": "1/1", "video": "16/9"}
        return {"aspect-ratio": aspect_map.get(tok, tok)}

    # ── Antialiased / font-smoothing ──────────────────────────────────────
    if c in ("antialiased", "subpixel-antialiased"):
        return {"font-smooth": "auto"}

    # ── Arbitrary properties  [property:value] ───────────────────────────
    m = re.match(r"^\[([a-zA-Z_-]+):(.+)\]$", c)
    if m:
        prop = camel_to_kebab(m.group(1))
        val = m.group(2).strip("'\"")
        return {prop: val}

    return {}


# ---------------------------------------------------------------------------
# Tailwind class string parser  (full className= value)
# ---------------------------------------------------------------------------


def parse_tailwind_classes(class_string: str) -> Dict[str, Any]:
    """
    Parse a full Tailwind className string into a merged CSS property dict.

    Input:  "flex flex-col items-center gap-[19px] bg-[#050508] p-5 rounded-3xl"
    Output: {
        "display": "flex",
        "flex-direction": "column",
        "align-items": "center",
        "gap": 19.0,
        "background-color": "#050508",
        "padding-top": 20, "padding-right": 20, ...
        "border-radius-tl": 24, ...
    }

    Later classes override earlier ones (standard Tailwind cascade).
    """
    result: Dict[str, Any] = {}
    for cls in class_string.split():
        props = parse_tailwind_class(cls)
        result.update(props)
    return result


# ---------------------------------------------------------------------------
# Merge: Tailwind + inline style → single CSS dict
# ---------------------------------------------------------------------------


def merge_styles(
    class_string: str = "",
    inline_style: str = "",
) -> Dict[str, Any]:
    """
    Merge Tailwind classes + inline style object into one CSS dict.
    Inline styles take precedence over Tailwind classes.
    """
    result = parse_tailwind_classes(class_string)
    if inline_style:
        inline = parse_inline_style(inline_style)
        # Convert camelCase inline keys to kebab and normalise values
        for key, val in inline.items():
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# CSS dict → UNNode property mapper
# ---------------------------------------------------------------------------


def apply_css_to_node(css: Dict[str, Any], node: Any) -> None:
    """
    Apply a merged CSS property dict onto a UNNode in-place.

    Imports UNNode types lazily to avoid circular deps.
    `node` is a UNNode instance — typed as Any here to keep this module
    free of ir/ imports at the module level.
    """
    from design_converter.ir.nodes import (
        AlignItems,
        GradientType,
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
        UNPadding,
        UNSize,
        UNSolidFill,
        UNStroke,
        UNStrokeThickness,
        UNTextStyle,
    )
    from design_converter.utils.color import (
        build_pencil_gradient,
        parse_css_color,
        parse_paper_background_image,
    )

    # ── Display / Layout ───────────────────────────────────────────────────
    disp = css.get("display", "")
    flex_dir = css.get("flex-direction", "")

    if disp == "flex" or disp == "inline-flex":
        if flex_dir == "column":
            node.layout = LayoutMode.VERTICAL
        else:
            node.layout = LayoutMode.HORIZONTAL
    elif disp == "none":
        node.visible = False

    # ── Justify-content ───────────────────────────────────────────────────
    jc_map = {
        "flex-start": JustifyContent.START,
        "start": JustifyContent.START,
        "center": JustifyContent.CENTER,
        "flex-end": JustifyContent.END,
        "end": JustifyContent.END,
        "space-between": JustifyContent.SPACE_BETWEEN,
        "space-around": JustifyContent.SPACE_AROUND,
    }
    if "justify-content" in css:
        node.justify_content = jc_map.get(css["justify-content"], JustifyContent.START)

    # ── Align-items ───────────────────────────────────────────────────────
    ai_map = {
        "flex-start": AlignItems.START,
        "start": AlignItems.START,
        "center": AlignItems.CENTER,
        "flex-end": AlignItems.END,
        "end": AlignItems.END,
        "stretch": AlignItems.STRETCH,
    }
    if "align-items" in css:
        node.align_items = ai_map.get(css["align-items"], AlignItems.START)

    # ── Gap ───────────────────────────────────────────────────────────────
    if "gap" in css:
        node.gap = float(css["gap"])

    # ── Width / Height ────────────────────────────────────────────────────
    if "width" in css:
        w = css["width"]
        if w == "fill":
            node.width = UNSize.fill()
        elif w == "hug":
            node.width = UNSize.hug()
        elif isinstance(w, (int, float)):
            node.width = UNSize.fixed(float(w))
        elif isinstance(w, str) and w.endswith("px"):
            node.width = UNSize.fixed(float(w[:-2]))

    if "height" in css:
        h = css["height"]
        if h == "fill":
            node.height = UNSize.fill()
        elif h == "hug":
            node.height = UNSize.hug()
        elif isinstance(h, (int, float)):
            node.height = UNSize.fixed(float(h))
        elif isinstance(h, str) and h.endswith("px"):
            node.height = UNSize.fixed(float(h[:-2]))

    # ── Padding ───────────────────────────────────────────────────────────
    # All-sides shorthand
    all_p = css.get("padding-top") is not None or css.get("padding") is not None
    if all_p or any(f"padding-{s}" in css for s in ("top", "right", "bottom", "left")):
        pt = float(css.get("padding-top", css.get("padding", 0)) or 0)
        pr = float(css.get("padding-right", css.get("padding", 0)) or 0)
        pb = float(css.get("padding-bottom", css.get("padding", 0)) or 0)
        pl = float(css.get("padding-left", css.get("padding", 0)) or 0)
        node.padding = UNPadding(top=pt, right=pr, bottom=pb, left=pl)

    # ── Background colour / gradient ──────────────────────────────────────
    if "background-color" in css:
        hex_c = parse_css_color(str(css["background-color"]))
        col = UNColor.from_hex(hex_c)
        node.fills = [UNSolidFill(color=col, opacity=col.a)]

    if "background-image" in css:
        grad = parse_paper_background_image(str(css["background-image"]))
        if grad:
            from design_converter.utils.color import css_rotation_to_pencil

            stops = [
                UNGradientStop(
                    color=UNColor.from_hex(s.color),
                    position=s.position,
                )
                for s in grad.stops
            ]
            gtype_map = {
                "linear": GradientType.LINEAR,
                "radial": GradientType.RADIAL,
                "angular": GradientType.ANGULAR,
            }
            node.fills = [
                UNGradientFill(
                    gradient_type=gtype_map.get(
                        grad.gradient_type, GradientType.LINEAR
                    ),
                    rotation=grad.rotation,
                    stops=stops,
                    opacity=grad.opacity,
                )
            ]

    # ── Text colour ────────────────────────────────────────────────────────
    if "color" in css and node.type == NodeType.TEXT:
        hex_c = parse_css_color(str(css["color"]))
        node.fills = [UNSolidFill(color=UNColor.from_hex(hex_c))]

    # ── Opacity ───────────────────────────────────────────────────────────
    if "opacity" in css:
        node.opacity = float(css["opacity"])

    # ── Overflow / clip ───────────────────────────────────────────────────
    if css.get("overflow") == "hidden":
        node.clip_content = True

    # ── Border-radius ─────────────────────────────────────────────────────
    tl = css.get("border-radius-tl")
    tr = css.get("border-radius-tr")
    br = css.get("border-radius-br")
    bl = css.get("border-radius-bl")
    if any(v is not None for v in (tl, tr, br, bl)):
        node.corner_radius = UNCornerRadius(
            tl=float(tl or 0),
            tr=float(tr or 0),
            br=float(br or 0),
            bl=float(bl or 0),
        )

    # ── Strokes (borders) ─────────────────────────────────────────────────
    def _make_stroke(
        color_hex: str, width: float, side: Optional[str] = None
    ) -> UNStroke:
        t = (
            UNStrokeThickness(**{side: width})  # type: ignore[arg-type]
            if side
            else UNStrokeThickness.uniform(width)
        )
        return UNStroke(
            fill=UNSolidFill(color=UNColor.from_hex(color_hex)),
            thickness=t,
            align=StrokeAlign.INSIDE,
        )

    for side_key, side_name in [
        ("border-top", "top"),
        ("border-right", "right"),
        ("border-bottom", "bottom"),
        ("border-left", "left"),
    ]:
        color_key = f"{side_key}-color"
        width_key = f"{side_key}-width"
        if color_key in css or width_key in css:
            color = parse_css_color(str(css.get(color_key, "#000000")))
            width = float(css.get(width_key, 1.0))
            node.strokes.append(_make_stroke(color, width, side_name))

    # All-sides border
    if "border-color" in css and "border-top-color" not in css:
        color = parse_css_color(str(css["border-color"]))
        width = float(css.get("border-width", 1.0))
        node.strokes.append(_make_stroke(color, width))

    # Arbitrary border-top-width  (Paper's [border-top-width:0.5px] pattern)
    if "border-top-width" in css and "border-top-color" not in css:
        width = float(str(css["border-top-width"]).replace("px", ""))
        existing_color = "#000000"
        # Look for a border-top-color that may have already been set
        for s in node.strokes:
            if isinstance(s.thickness.top, float):
                break
        node.strokes.append(_make_stroke(existing_color, width, "top"))

    # ── Box / text shadow ─────────────────────────────────────────────────
    for shadow_prop in ("box-shadow", "text-shadow"):
        if shadow_prop in css:
            shadow_str = str(css[shadow_prop])
            shadows = _parse_shadow_string(shadow_str)
            node.effects.extend(shadows)

    # ── Text style fields ─────────────────────────────────────────────────
    if node.type == NodeType.TEXT:
        ts = node.text_style
        if "font-size" in css:
            ts.font_size = float(css["font-size"])
        if "font-weight" in css:
            ts.font_weight = str(css["font-weight"])
        if "font-family" in css:
            ts.font_family = str(css["font-family"]).split(",")[0].strip().strip("\"'")
        if "letter-spacing" in css:
            ts.letter_spacing = float(str(css["letter-spacing"]).replace("px", ""))
        if "line-height" in css:
            val = css["line-height"]
            if isinstance(val, (int, float)):
                ts.line_height = float(val)
            elif isinstance(val, str) and val.endswith("px"):
                ts.line_height = float(val[:-2])
        if "line-height-multiplier" in css:
            mult = float(css["line-height-multiplier"])
            ts.line_height = ts.font_size * mult
        if "text-align" in css:
            align_map = {
                "left": TextAlign.LEFT,
                "center": TextAlign.CENTER,
                "right": TextAlign.RIGHT,
                "justify": TextAlign.JUSTIFY,
            }
            ts.text_align = align_map.get(str(css["text-align"]), TextAlign.LEFT)
        if "text-transform" in css:
            tt_map = {
                "uppercase": TextTransform.UPPERCASE,
                "lowercase": TextTransform.LOWERCASE,
                "capitalize": TextTransform.CAPITALIZE,
                "none": TextTransform.NONE,
            }
            ts.text_transform = tt_map.get(
                str(css["text-transform"]), TextTransform.NONE
            )
        if "text-decoration" in css:
            ts.text_decoration = str(css["text-decoration"])

        # Auto-resize heuristic
        if node.width.mode == SizingMode.HUG and node.height.mode == SizingMode.HUG:
            ts.text_auto_resize = TextAutoResize.WIDTH_HEIGHT
        elif node.width.mode == SizingMode.FIXED and node.height.mode == SizingMode.HUG:
            ts.text_auto_resize = TextAutoResize.HEIGHT
        else:
            ts.text_auto_resize = TextAutoResize.NONE

    # ── Position (absolute x/y) ───────────────────────────────────────────
    if "left" in css and isinstance(css["left"], (int, float)):
        node.x = float(css["left"])
    if "top" in css and isinstance(css["top"], (int, float)):
        node.y = float(css["top"])

    # ── Visibility ────────────────────────────────────────────────────────
    if css.get("display") == "none" or css.get("visibility") == "hidden":
        node.visible = False

    # ── Rotation ─────────────────────────────────────────────────────────
    if "rotate" in css:
        try:
            node.rotation = float(str(css["rotate"]).replace("deg", ""))
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Shadow string parser
# ---------------------------------------------------------------------------


def _parse_shadow_string(shadow_str: str) -> list:
    """
    Parse CSS box-shadow / text-shadow string into UNDropShadow list.
    Handles multiple shadows separated by commas.
    e.g. "#8B5CF633 0px 5px 10px, #8B5CF633 0px 0px 40px"
    """
    from design_converter.ir.nodes import UNColor, UNDropShadow

    shadows = []
    parts = _split_shadow_parts(shadow_str)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Extract colour (hex or functional notation)
        color = "#00000040"  # default
        color_match = re.search(r"(#[0-9a-fA-F]{3,8})", part)
        if color_match:
            color = color_match.group(1)
            part = part.replace(color_match.group(0), "").strip()

        rgba_match = re.search(r"rgba?\([^)]+\)", part)
        if rgba_match:
            from design_converter.utils.color import parse_css_color

            color = parse_css_color(rgba_match.group(0))
            part = part.replace(rgba_match.group(0), "").strip()

        # Parse remaining numbers: offset-x offset-y blur [spread]
        nums = re.findall(r"-?[\d.]+", part)
        ox = float(nums[0]) if len(nums) > 0 else 0.0
        oy = float(nums[1]) if len(nums) > 1 else 4.0
        blur = float(nums[2]) if len(nums) > 2 else 0.0
        spread = float(nums[3]) if len(nums) > 3 else 0.0

        inner = "inset" in part.lower()

        try:
            shadow = UNDropShadow(
                color=UNColor.from_hex(color),
                offset_x=ox,
                offset_y=oy,
                blur=blur,
                spread=spread,
                inner=inner,
            )
            shadows.append(shadow)
        except Exception:
            pass

    return shadows


def _split_shadow_parts(shadow_str: str) -> List[str]:
    """Split shadow string by commas, respecting parentheses."""
    parts = []
    depth = 0
    current: List[str] = []
    for ch in shadow_str:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


# ---------------------------------------------------------------------------
# UNNode → CSS dict  (reverse direction — for Paper writer)
# ---------------------------------------------------------------------------


def node_to_css(node: Any) -> Dict[str, str]:
    """
    Convert a UNNode back to a flat CSS property dict (kebab-case, string values).
    Used by the Paper writer to generate HTML inline styles.
    """
    from design_converter.ir.nodes import (
        AlignItems,
        GradientType,
        JustifyContent,
        LayoutMode,
        NodeType,
        SizingMode,
        TextAlign,
        TextTransform,
        UNGradientFill,
        UNSolidFill,
    )
    from design_converter.utils.color import ParsedGradient, ParsedGradientStop, build_css_gradient

    css: Dict[str, str] = {}

    # Layout
    if node.layout == LayoutMode.HORIZONTAL:
        css["display"] = "flex"
        css["flex-direction"] = "row"
    elif node.layout == LayoutMode.VERTICAL:
        css["display"] = "flex"
        css["flex-direction"] = "column"

    if node.layout != LayoutMode.NONE:
        if node.gap:
            css["gap"] = f"{node.gap}px"
        jc = {
            JustifyContent.START: "flex-start",
            JustifyContent.CENTER: "center",
            JustifyContent.END: "flex-end",
            JustifyContent.SPACE_BETWEEN: "space-between",
            JustifyContent.SPACE_AROUND: "space-around",
        }.get(node.justify_content, "flex-start")
        if jc != "flex-start":
            css["justify-content"] = jc
        ai = {
            AlignItems.START: "flex-start",
            AlignItems.CENTER: "center",
            AlignItems.END: "flex-end",
            AlignItems.STRETCH: "stretch",
        }.get(node.align_items, "flex-start")
        if ai != "flex-start":
            css["align-items"] = ai

    # Size
    if node.width.mode == SizingMode.FIXED:
        css["width"] = f"{node.width.value}px"
    elif node.width.mode == SizingMode.FILL:
        css["width"] = "100%"
    elif node.width.mode == SizingMode.HUG:
        css["width"] = "fit-content"

    if node.height.mode == SizingMode.FIXED:
        css["height"] = f"{node.height.value}px"
    elif node.height.mode == SizingMode.FILL:
        css["height"] = "100%"
    elif node.height.mode == SizingMode.HUG:
        css["height"] = "fit-content"

    # Padding
    p = node.padding
    if not p.is_zero():
        if p.top == p.right == p.bottom == p.left:
            css["padding"] = f"{p.top}px"
        else:
            css["padding"] = f"{p.top}px {p.right}px {p.bottom}px {p.left}px"

    # Fill / background
    for fill in node.fills:
        if isinstance(fill, UNSolidFill) and fill.enabled:
            col = fill.color
            if col.a < 1.0:
                css["background-color"] = col.to_css_rgba()
            else:
                css["background-color"] = col.to_hex(include_alpha=False)
            break
        elif isinstance(fill, UNGradientFill) and fill.enabled:
            pg = ParsedGradient(
                gradient_type=fill.gradient_type.value,
                rotation=fill.rotation,
                stops=[
                    ParsedGradientStop(color=s.color.to_hex(), position=s.position)
                    for s in fill.stops
                ],
                opacity=fill.opacity,
            )
            css["background-image"] = build_css_gradient(pg)
            break

    # Corner radius
    cr = node.corner_radius
    if cr.is_uniform():
        if cr.tl > 0:
            css["border-radius"] = f"{cr.tl}px"
    else:
        css["border-radius"] = cr.to_css()

    # Opacity
    if node.opacity < 1.0:
        css["opacity"] = str(round(node.opacity, 3))

    # Clip
    if node.clip_content:
        css["overflow"] = "hidden"

    # Strokes → borders
    for stroke in node.strokes:
        if not stroke.enabled:
            continue
        t = stroke.thickness
        if isinstance(stroke.fill, UNSolidFill):
            color = stroke.fill.color.to_hex(include_alpha=True)
        else:
            color = "#000000"
        thick = t.max_value()
        if t.all is not None:
            css["border"] = f"{thick}px solid {color}"
        else:
            for side, val in [
                ("top", t.top),
                ("right", t.right),
                ("bottom", t.bottom),
                ("left", t.left),
            ]:
                if val is not None:
                    css[f"border-{side}"] = f"{val}px solid {color}"

    # Effects → box-shadow
    shadows = []
    for effect in node.effects:
        from design_converter.ir.nodes import UNDropShadow

        if isinstance(effect, UNDropShadow) and effect.enabled:
            col = effect.color.to_css_rgba()
            inset = "inset " if effect.inner else ""
            shadows.append(
                f"{inset}{effect.offset_x}px {effect.offset_y}px "
                f"{effect.blur}px {effect.spread}px {col}"
            )
    if shadows:
        prop = "text-shadow" if node.type == NodeType.TEXT else "box-shadow"
        css[prop] = ", ".join(shadows)

    # Text
    if node.type == NodeType.TEXT:
        ts = node.text_style
        css.update(ts.to_css())
        # Override color from fills
        for fill in node.fills:
            if isinstance(fill, UNSolidFill) and fill.enabled:
                css["color"] = fill.color.to_hex(include_alpha=False)
                if "background-color" in css:
                    del css["background-color"]
                break

    # Position (absolute)
    if node.x != 0:
        css["left"] = f"{node.x}px"
    if node.y != 0:
        css["top"] = f"{node.y}px"

    return css


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Tailwind parser ===")
    tests = [
        "flex flex-col items-center gap-[19px] bg-[#050508] p-5 rounded-3xl",
        "text-[11px] font-semibold tracking-[1.5px] uppercase text-[#71717A]",
        "w-[390px] h-[844px] overflow-clip",
        "border-t-[#626187] [border-top-width:0.5px]",
        "mb-6 pb-3 w-full",
        "flex justify-between items-center shrink-0",
    ]
    for t in tests:
        result = parse_tailwind_classes(t)
        print(f"\n  '{t[:50]}'")
        for k, v in result.items():
            print(f"    {k}: {v}")

    print("\n=== Inline style parser ===")
    s = "{ translate: '-50% -50%', backgroundColor: '#050508', display: 'flex' }"
    print(parse_inline_style(s))
