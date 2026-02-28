"""
utils/color.py — Color Conversion Engine
=========================================
Single source of truth for all color operations in the design converter.

Formats handled:
  • #RGB  #RRGGBB  #RRGGBBAA  (hex, case-insensitive)
  • rgb() / rgba()             (0-255 or 0-100%)
  • hsl() / hsla()
  • oklab()                    ← Paper gradient stops
  • oklch()
  • CSS named colors           (full W3C set)
  • Figma {r,g,b} dicts        (0-1 normalized floats)
  • CSS gradient strings       (linear-gradient, radial-gradient)
  • Paper gradient strings     (linear-gradient(in oklab …))

Rotation conventions stored internally as CSS degrees:
  CSS:    0° = top→bottom,  90° = left→right,  180° = bottom→top
  Pencil: 0° = up (pointing up = end up),  CCW positive
  Figma:  uses a transform matrix (handle positions)

All public functions return plain Python strings/dicts/floats — no IR imports.
The adapters import this module and translate to UNColor where needed.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# CSS named colors (full W3C set)
# ---------------------------------------------------------------------------

NAMED_COLORS: Dict[str, str] = {
    "aliceblue": "#F0F8FF", "antiquewhite": "#FAEBD7", "aqua": "#00FFFF",
    "aquamarine": "#7FFFD4", "azure": "#F0FFFF", "beige": "#F5F5DC",
    "bisque": "#FFE4C4", "black": "#000000", "blanchedalmond": "#FFEBCD",
    "blue": "#0000FF", "blueviolet": "#8A2BE2", "brown": "#A52A2A",
    "burlywood": "#DEB887", "cadetblue": "#5F9EA0", "chartreuse": "#7FFF00",
    "chocolate": "#D2691E", "coral": "#FF7F50", "cornflowerblue": "#6495ED",
    "cornsilk": "#FFF8DC", "crimson": "#DC143C", "cyan": "#00FFFF",
    "darkblue": "#00008B", "darkcyan": "#008B8B", "darkgoldenrod": "#B8860B",
    "darkgray": "#A9A9A9", "darkgreen": "#006400", "darkgrey": "#A9A9A9",
    "darkkhaki": "#BDB76B", "darkmagenta": "#8B008B", "darkolivegreen": "#556B2F",
    "darkorange": "#FF8C00", "darkorchid": "#9932CC", "darkred": "#8B0000",
    "darksalmon": "#E9967A", "darkseagreen": "#8FBC8F", "darkslateblue": "#483D8B",
    "darkslategray": "#2F4F4F", "darkslategrey": "#2F4F4F",
    "darkturquoise": "#00CED1", "darkviolet": "#9400D3", "deeppink": "#FF1493",
    "deepskyblue": "#00BFFF", "dimgray": "#696969", "dimgrey": "#696969",
    "dodgerblue": "#1E90FF", "firebrick": "#B22222", "floralwhite": "#FFFAF0",
    "forestgreen": "#228B22", "fuchsia": "#FF00FF", "gainsboro": "#DCDCDC",
    "ghostwhite": "#F8F8FF", "gold": "#FFD700", "goldenrod": "#DAA520",
    "gray": "#808080", "green": "#008000", "greenyellow": "#ADFF2F",
    "grey": "#808080", "honeydew": "#F0FFF0", "hotpink": "#FF69B4",
    "indianred": "#CD5C5C", "indigo": "#4B0082", "ivory": "#FFFFF0",
    "khaki": "#F0E68C", "lavender": "#E6E6FA", "lavenderblush": "#FFF0F5",
    "lawngreen": "#7CFC00", "lemonchiffon": "#FFFACD", "lightblue": "#ADD8E6",
    "lightcoral": "#F08080", "lightcyan": "#E0FFFF", "lightgoldenrodyellow": "#FAFAD2",
    "lightgray": "#D3D3D3", "lightgreen": "#90EE90", "lightgrey": "#D3D3D3",
    "lightpink": "#FFB6C1", "lightsalmon": "#FFA07A", "lightseagreen": "#20B2AA",
    "lightskyblue": "#87CEFA", "lightslategray": "#778899", "lightslategrey": "#778899",
    "lightsteelblue": "#B0C4DE", "lightyellow": "#FFFFE0", "lime": "#00FF00",
    "limegreen": "#32CD32", "linen": "#FAF0E6", "magenta": "#FF00FF",
    "maroon": "#800000", "mediumaquamarine": "#66CDAA", "mediumblue": "#0000CD",
    "mediumorchid": "#BA55D3", "mediumpurple": "#9370DB", "mediumseagreen": "#3CB371",
    "mediumslateblue": "#7B68EE", "mediumspringgreen": "#00FA9A",
    "mediumturquoise": "#48D1CC", "mediumvioletred": "#C71585",
    "midnightblue": "#191970", "mintcream": "#F5FFFA", "mistyrose": "#FFE4E1",
    "moccasin": "#FFE4B5", "navajowhite": "#FFDEAD", "navy": "#000080",
    "oldlace": "#FDF5E6", "olive": "#808000", "olivedrab": "#6B8E23",
    "orange": "#FFA500", "orangered": "#FF4500", "orchid": "#DA70D6",
    "palegoldenrod": "#EEE8AA", "palegreen": "#98FB98", "paleturquoise": "#AFEEEE",
    "palevioletred": "#DB7093", "papayawhip": "#FFEFD5", "peachpuff": "#FFDAB9",
    "peru": "#CD853F", "pink": "#FFC0CB", "plum": "#DDA0DD",
    "powderblue": "#B0E0E6", "purple": "#800080", "rebeccapurple": "#663399",
    "red": "#FF0000", "rosybrown": "#BC8F8F", "royalblue": "#4169E1",
    "saddlebrown": "#8B4513", "salmon": "#FA8072", "sandybrown": "#F4A460",
    "seagreen": "#2E8B57", "seashell": "#FFF5EE", "sienna": "#A0522D",
    "silver": "#C0C0C0", "skyblue": "#87CEEB", "slateblue": "#6A5ACD",
    "slategray": "#708090", "slategrey": "#708090", "snow": "#FFFAFA",
    "springgreen": "#00FF7F", "steelblue": "#4682B4", "tan": "#D2B48C",
    "teal": "#008080", "thistle": "#D8BFD8", "tomato": "#FF6347",
    "transparent": "#00000000", "turquoise": "#40E0D0", "violet": "#EE82EE",
    "wheat": "#F5DEB3", "white": "#FFFFFF", "whitesmoke": "#F5F5F5",
    "yellow": "#FFFF00", "yellowgreen": "#9ACD32",
}


# ---------------------------------------------------------------------------
# OKLab → sRGB  (Björn Ottosson, https://bottosson.github.io/posts/oklab/)
# ---------------------------------------------------------------------------

def _oklab_to_linear_srgb(L: float, a: float, b: float) -> Tuple[float, float, float]:
    """OKLab → linear sRGB (may be out-of-gamut; callers must clamp)."""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r =  4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_ = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, b_


def _linear_to_srgb(c: float) -> float:
    """Apply sRGB gamma encoding, clamped to [0, 1]."""
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def oklab_to_hex(L: float, a: float, b: float, alpha: float = 1.0) -> str:
    """
    Convert OKLab (L, a, b) to #RRGGBB or #RRGGBBAA.
    L accepts both 0-1 and 0-100 (auto-detected via value > 1.5).
    """
    if L > 1.5:
        L /= 100.0
    r_lin, g_lin, b_lin = _oklab_to_linear_srgb(L, a, b)
    ri = round(_linear_to_srgb(r_lin) * 255)
    gi = round(_linear_to_srgb(g_lin) * 255)
    bi = round(_linear_to_srgb(b_lin) * 255)
    ai = round(max(0.0, min(1.0, alpha)) * 255)
    if ai < 255:
        return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"
    return f"#{ri:02X}{gi:02X}{bi:02X}"


def _oklch_to_oklab(L: float, C: float, H: float) -> Tuple[float, float, float]:
    h_rad = math.radians(H)
    return L, C * math.cos(h_rad), C * math.sin(h_rad)


# ---------------------------------------------------------------------------
# HSL helpers
# ---------------------------------------------------------------------------

def _hsl_to_hex(h: float, s: float, l: float, a: float = 1.0) -> str:
    """h: 0-360, s: 0-100, l: 0-100, a: 0-1."""
    s /= 100.0
    l /= 100.0
    c = (1.0 - abs(2 * l - 1)) * s
    x = c * (1.0 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2.0
    if   h < 60:  rf, gf, bf = c, x, 0.0
    elif h < 120: rf, gf, bf = x, c, 0.0
    elif h < 180: rf, gf, bf = 0.0, c, x
    elif h < 240: rf, gf, bf = 0.0, x, c
    elif h < 300: rf, gf, bf = x, 0.0, c
    else:         rf, gf, bf = c, 0.0, x
    ri = round((rf + m) * 255)
    gi = round((gf + m) * 255)
    bi = round((bf + m) * 255)
    ai = round(a * 255)
    if ai < 255:
        return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"
    return f"#{ri:02X}{gi:02X}{bi:02X}"


# ---------------------------------------------------------------------------
# Hex normalization
# ---------------------------------------------------------------------------

def normalize_hex(hex_str: str) -> str:
    """
    Normalize any hex color string to uppercase 8-digit #RRGGBBAA.
    Accepts: #RGB, #RGBA, #RRGGBB, #RRGGBBAA (with or without leading #).
    """
    h = hex_str.strip().lstrip("#").upper()
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2 + "FF"
    elif len(h) == 4:
        h = h[0]*2 + h[1]*2 + h[2]*2 + h[3]*2
    elif len(h) == 6:
        h = h + "FF"
    elif len(h) == 8:
        pass
    else:
        raise ValueError(f"Cannot normalize hex: {hex_str!r}")
    return f"#{h}"


def hex_to_rgba(hex_str: str) -> Tuple[float, float, float, float]:
    """Return (r, g, b, a) as 0-1 floats from any hex color string."""
    h = normalize_hex(hex_str).lstrip("#")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
        int(h[6:8], 16) / 255.0,
    )


def hex_get_alpha(hex_str: str) -> float:
    """Extract alpha as 0-1 float from any hex string."""
    _, _, _, a = hex_to_rgba(hex_str)
    return a


def hex_strip_alpha(hex_str: str) -> str:
    """Return #RRGGBB (alpha removed)."""
    h = normalize_hex(hex_str).lstrip("#")
    return f"#{h[0:6]}"


def hex_set_alpha(hex_str: str, alpha: float) -> str:
    """Return hex with alpha replaced."""
    r, g, b, _ = hex_to_rgba(hex_str)
    ai = round(max(0.0, min(1.0, alpha)) * 255)
    ri, gi, bi = round(r*255), round(g*255), round(b*255)
    if ai < 255:
        return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"
    return f"#{ri:02X}{gi:02X}{bi:02X}"


# ---------------------------------------------------------------------------
# Figma ↔ hex
# ---------------------------------------------------------------------------

def figma_rgb_to_hex(color: Dict[str, float], opacity: float = 1.0) -> str:
    """
    Convert Figma paint color dict {r, g, b} (0-1 floats) + opacity → hex.
    Figma stores alpha separately as the paint's 'opacity' field.
    """
    ri = round(color.get("r", 0) * 255)
    gi = round(color.get("g", 0) * 255)
    bi = round(color.get("b", 0) * 255)
    ai = round(max(0.0, min(1.0, opacity)) * 255)
    if ai < 255:
        return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"
    return f"#{ri:02X}{gi:02X}{bi:02X}"


def hex_to_figma_rgb(hex_str: str) -> Dict[str, float]:
    """Return Figma-style {r, g, b} dict (0-1 floats, no alpha)."""
    r, g, b, _ = hex_to_rgba(hex_str)
    return {"r": round(r, 5), "g": round(g, 5), "b": round(b, 5)}


def hex_to_figma_color_with_alpha(hex_str: str) -> Dict[str, float]:
    """Return Figma-style {r, g, b, a} dict."""
    r, g, b, a = hex_to_rgba(hex_str)
    return {"r": round(r, 5), "g": round(g, 5), "b": round(b, 5), "a": round(a, 5)}


# ---------------------------------------------------------------------------
# Generic CSS color string parser
# ---------------------------------------------------------------------------

def parse_css_color(color_str: str) -> Optional[str]:
    """
    Parse any CSS color string → normalized #RRGGBBAA hex string.
    Returns None for unrecognized or non-color strings (e.g. 'none', 'inherit').

    Supports:
      Named colors, #hex, rgb(), rgba(), hsl(), hsla(), oklab(), oklch()
    """
    s = color_str.strip()
    if not s:
        return None

    lo = s.lower()

    # Special keywords
    if lo in ("none", "inherit", "initial", "unset", "currentcolor"):
        return None
    if lo == "transparent":
        return "#00000000"

    # Named color
    if lo in NAMED_COLORS:
        return normalize_hex(NAMED_COLORS[lo])

    # Hex
    if s.startswith("#"):
        try:
            return normalize_hex(s)
        except ValueError:
            return None

    # Normalize spaces around parens
    lo_s = re.sub(r'\s+', ' ', lo)

    # rgb() / rgba() — comma and space-separated, percentage channels
    m = re.match(
        r'rgba?\(\s*([^\)]+)\s*\)', lo_s
    )
    if m:
        args = m.group(1)
        # Determine separator: comma or space (CSS Level 4)
        if ',' in args:
            parts = [p.strip() for p in args.split(',')]
        else:
            # "R G B / A" syntax
            parts = re.split(r'\s+(?!/)', args)
            slash_idx = next((i for i, p in enumerate(parts) if '/' in p), None)
            if slash_idx is not None:
                # Rejoin and split on /
                rejoined = ' '.join(parts)
                main, _, alpha_part = rejoined.partition('/')
                parts = main.split() + [alpha_part.strip()]

        def _channel(v: str) -> int:
            v = v.strip()
            if v.endswith('%'):
                return round(float(v[:-1]) / 100.0 * 255)
            val = float(v)
            return round(val) if val > 1.0 else round(val * 255)

        def _alpha(v: str) -> float:
            v = v.strip()
            if v.endswith('%'):
                return float(v[:-1]) / 100.0
            return float(v)

        try:
            ri = _channel(parts[0])
            gi = _channel(parts[1])
            bi = _channel(parts[2])
            ai = round(_alpha(parts[3]) * 255) if len(parts) > 3 else 255
            ri = max(0, min(255, ri))
            gi = max(0, min(255, gi))
            bi = max(0, min(255, bi))
            ai = max(0, min(255, ai))
            if ai < 255:
                return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"
            return f"#{ri:02X}{gi:02X}{bi:02X}"
        except (ValueError, IndexError):
            pass

    # hsl() / hsla()
    m = re.match(
        r'hsla?\(\s*([^\)]+)\s*\)', lo_s
    )
    if m:
        args = [p.strip() for p in re.split(r'[,/\s]+', m.group(1)) if p.strip()]
        try:
            h_deg = float(args[0].rstrip('deg'))
            s_pct = float(args[1].rstrip('%'))
            l_pct = float(args[2].rstrip('%'))
            a_val = float(args[3].rstrip('%')) / (100.0 if '%' in args[3] else 1.0) \
                    if len(args) > 3 else 1.0
            return normalize_hex(_hsl_to_hex(h_deg, s_pct, l_pct, a_val))
        except (ValueError, IndexError):
            pass

    # oklab()  — Paper's gradient stop format
    # Handles: oklab(84.4% -0.183 0.078)  and  oklab(0.844 -0.183 0.078)
    # Also:    oklab(84.4% -0.183 0.078 / 0.5)
    m = re.match(
        r'oklab\(\s*([\d.]+)(%?)\s+([-\d.]+)\s+([-\d.]+)'
        r'(?:\s*/\s*([\d.]+%?))?\s*\)',
        lo_s
    )
    if m:
        L_raw = float(m.group(1))
        L = L_raw / 100.0 if m.group(2) == '%' else L_raw
        a_val = float(m.group(3))
        b_val = float(m.group(4))
        alpha = 1.0
        if m.group(5):
            av = m.group(5).strip()
            alpha = float(av.rstrip('%')) / 100.0 if '%' in av else float(av)
        return oklab_to_hex(L, a_val, b_val, alpha)

    # oklch()
    m = re.match(
        r'oklch\(\s*([\d.]+)(%?)\s+([\d.]+)\s+([\d.]+)'
        r'(?:\s*/\s*([\d.]+%?))?\s*\)',
        lo_s
    )
    if m:
        L_raw = float(m.group(1))
        L = L_raw / 100.0 if m.group(2) == '%' else L_raw
        C = float(m.group(3))
        H = float(m.group(4))
        L2, a2, b2 = _oklch_to_oklab(L, C, H)
        alpha = 1.0
        if m.group(5):
            av = m.group(5).strip()
            alpha = float(av.rstrip('%')) / 100.0 if '%' in av else float(av)
        return oklab_to_hex(L2, a2, b2, alpha)

    return None


# ---------------------------------------------------------------------------
# Gradient parsing
# ---------------------------------------------------------------------------

def _split_top_level(s: str, sep: str = ',') -> List[str]:
    """Split string by sep, respecting nested parentheses."""
    parts: List[str] = []
    depth = 0
    current: List[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif s[i:i+len(sep)] == sep and depth == 0:
            parts.append(''.join(current).strip())
            current = []
            i += len(sep)
            continue
        else:
            current.append(ch)
        i += 1
    if current:
        parts.append(''.join(current).strip())
    return parts


def _parse_angle_token(token: str) -> Optional[float]:
    """
    Parse angle from a CSS gradient token → degrees (CSS convention).
    Returns None if the token is not an angle.
    """
    t = token.strip().lower()
    m = re.match(r'^([-\d.]+)(deg|grad|rad|turn)$', t)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if unit == 'deg':   return val
        if unit == 'grad':  return val * 0.9
        if unit == 'rad':   return math.degrees(val)
        if unit == 'turn':  return val * 360.0
    # "to <direction>" keywords
    direction_map = {
        'to top':          0.0,
        'to right':        90.0,
        'to bottom':       180.0,
        'to left':         270.0,
        'to top right':    45.0,
        'to bottom right': 135.0,
        'to bottom left':  225.0,
        'to top left':     315.0,
    }
    return direction_map.get(t)


def _parse_color_stop(token: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single gradient color stop:
      "#FF0000 25%"  →  {"color": "#FF0000FF", "position": 0.25}
      "oklab(84.4% -0.183 0.078) 0%"  →  {"color": "#...", "position": 0.0}
      "transparent"  →  {"color": "#00000000", "position": None}
    Returns None if the token cannot be parsed as a color stop.
    """
    token = token.strip()
    if not token:
        return None

    # Try to extract trailing position: "… 50%" or "… 0.5"
    pos: Optional[float] = None
    # Match trailing percentage (after the color part, which may have parens)
    m = re.search(r'\s+([\d.]+)%\s*$', token)
    if m:
        pos = float(m.group(1)) / 100.0
        token = token[:m.start()].strip()
    else:
        # Match trailing bare float 0-1 (only if no % and looks like position)
        m2 = re.search(r'\s+(0(?:\.\d+)|1(?:\.0+)?)$', token)
        if m2:
            pos = float(m2.group(1))
            token = token[:m2.start()].strip()

    hex_color = parse_css_color(token)
    if hex_color is None:
        return None
    return {"color": hex_color, "position": pos}


def _fill_positions(stops: List[Dict[str, Any]]) -> None:
    """Interpolate missing stop positions in-place (like CSS spec)."""
    n = len(stops)
    if n == 0:
        return
    if stops[0]["position"] is None:
        stops[0]["position"] = 0.0
    if stops[-1]["position"] is None:
        stops[-1]["position"] = 1.0

    i = 0
    while i < n:
        if stops[i]["position"] is None:
            j = i + 1
            while j < n and stops[j]["position"] is None:
                j += 1
            p_start = stops[i - 1]["position"]
            p_end = stops[j]["position"] if j < n else 1.0
            span = j - i + 1
            for k in range(i, j):
                t = (k - i + 1) / span
                stops[k]["position"] = p_start + t * (p_end - p_start)
        i += 1


def parse_gradient_css(css: str) -> Optional[Dict[str, Any]]:
    """
    Parse a CSS gradient string into a normalized dict:

    {
        "type":     "linear" | "radial" | "angular",
        "rotation": float,    # CSS degrees (only meaningful for linear)
        "stops": [
            {"color": "#RRGGBBAA", "position": 0.0},
            ...
        ],
        "opacity": 1.0,
    }

    Handles:
      - linear-gradient(180deg, #000 0%, #fff 100%)
      - linear-gradient(to bottom right, red, blue)
      - linear-gradient(in oklab 135deg, oklab(84.4% -0.183 0.078) 0%, ...)
      - radial-gradient(circle, #fff 0%, #000 100%)

    Returns None if input is not a gradient.
    """
    s = css.strip()
    lo = s.lower()

    if lo.startswith('linear-gradient'):
        grad_type = 'linear'
    elif lo.startswith('radial-gradient'):
        grad_type = 'radial'
    elif lo.startswith('conic-gradient'):
        grad_type = 'angular'
    else:
        return None

    # Extract inner content
    paren_open = s.index('(')
    inner = s[paren_open + 1 : -1].strip()

    tokens = _split_top_level(inner)
    if not tokens:
        return None

    rotation = 180.0       # default: top → bottom
    stop_start = 0

    # Skip "in <colorspace>" modifier (e.g. "in oklab", "in srgb")
    if tokens[0].strip().lower().startswith('in '):
        tokens.pop(0)

    if tokens:
        first = tokens[0].strip()
        angle = _parse_angle_token(first)
        if angle is not None:
            rotation = angle
            stop_start = 1
        elif grad_type == 'radial':
            # Skip shape/size/position tokens
            keywords = {'circle', 'ellipse', 'closest-side', 'closest-corner',
                        'farthest-side', 'farthest-corner'}
            if any(k in first.lower() for k in keywords):
                stop_start = 1

    # Parse color stops
    raw_stops = tokens[stop_start:]
    stops: List[Dict[str, Any]] = []
    for raw in raw_stops:
        stop = _parse_color_stop(raw)
        if stop:
            stops.append(stop)

    if not stops:
        return None

    _fill_positions(stops)

    return {
        "type": grad_type,
        "rotation": rotation,
        "stops": stops,
        "opacity": 1.0,
    }


# ---------------------------------------------------------------------------
# Figma paint → normalized dict
# ---------------------------------------------------------------------------

def figma_paint_to_dict(paint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convert a Figma paint object → normalized dict used by the converter.

    Solid:    {"type": "solid", "color": "#RRGGBB", "opacity": float}
    Gradient: {"type": "linear"|"radial", "rotation": float,
               "stops": [...], "opacity": float}
    Image:    {"type": "image", "url": "", "mode": "fill"|"fit"|"stretch"}
    """
    if not paint.get("visible", True):
        return None

    opacity = float(paint.get("opacity", 1.0))
    ptype = paint.get("type", "")

    if ptype == "SOLID":
        color = paint.get("color", {})
        r = int(round(color.get("r", 0) * 255))
        g = int(round(color.get("g", 0) * 255))
        b = int(round(color.get("b", 0) * 255))
        a = color.get("a", 1.0) * opacity
        return {
            "type": "solid",
            "color": f"#{r:02X}{g:02X}{b:02X}",
            "opacity": round(a, 4),
        }

    if ptype in ("GRADIENT_LINEAR", "GRADIENT_RADIAL", "GRADIENT_ANGULAR", "GRADIENT_DIAMOND"):
        grad_map = {
            "GRADIENT_LINEAR": "linear",
            "GRADIENT_RADIAL": "radial",
            "GRADIENT_ANGULAR": "angular",
            "GRADIENT_DIAMOND": "diamond",
        }
        grad_type = grad_map[ptype]

        raw_stops = paint.get("gradientStops", [])
        stops: List[Dict[str, Any]] = []
        for stop in raw_stops:
            c = stop.get("color", {})
            r = int(round(c.get("r", 0) * 255))
            g = int(round(c.get("g", 0) * 255))
            b = int(round(c.get("b", 0) * 255))
            a = c.get("a", 1.0)
            stops.append({
                "position": stop.get("position", 0.0),
                "color": f"#{r:02X}{g:02X}{b:02X}",
                "opacity": round(a, 4),
            })

        # Extract rotation from gradientTransform matrix.
        transform = paint.get("gradientTransform", [[1, 0, 0], [0, 1, 0]])
        rotation = 0.0
        try:
            # transform = [[a, b, c], [d, e, f]]
            # For linear: angle from (a, d) vector.
            a_val = transform[0][0]
            d_val = transform[1][0]
            rotation = round(math.degrees(math.atan2(d_val, a_val)), 2)
        except Exception:
            pass

        return {
            "type": grad_type,
            "rotation": rotation,
            "stops": stops,
            "opacity": round(opacity, 4),
        }

    if ptype == "IMAGE":
        mode_map = {
            "FILL": "fill",
            "FIT": "fit",
            "STRETCH": "stretch",
            "TILE": "tile",
        }
        scale_mode = paint.get("scaleMode", "FILL")
        return {
            "type": "image",
            "url": "",
            "mode": mode_map.get(scale_mode, "fill"),
            "opacity": round(opacity, 4),
        }

    # Unknown paint type — return None so callers can skip it.
    return None


# ---------------------------------------------------------------------------
# Name aliases  (existing functions had internal names; public API uses these)
# ---------------------------------------------------------------------------

def figma_color_to_hex(color: Dict[str, float], opacity: float = 1.0) -> str:
    """Convert Figma {r,g,b[,a]} (0-1) dict to #RRGGBB or #RRGGBBAA."""
    return figma_rgb_to_hex(color, opacity)


def hex_to_figma_color(hex_str: str) -> Dict[str, float]:
    """Convert #RRGGBB[AA] to Figma {r,g,b,a} (0-1) dict."""
    return hex_to_figma_rgb(hex_str)


def parse_css_gradient(css: str) -> Optional[Dict[str, Any]]:
    """Parse CSS gradient string → normalized dict.  Alias of parse_gradient_css."""
    return parse_gradient_css(css)


# ---------------------------------------------------------------------------
# Hex / float conversions
# ---------------------------------------------------------------------------

def hex_to_rgb_float(hex_str: str) -> Tuple[float, float, float]:
    """Return (r, g, b) in 0-1 range from a hex color string."""
    r, g, b, _ = hex_to_rgba(normalize_hex(hex_str))
    return r, g, b


def rgb_float_to_hex(r: float, g: float, b: float, a: float = 1.0) -> str:
    """Convert 0-1 RGB(A) floats to #RRGGBB or #RRGGBBAA."""
    ri = max(0, min(255, round(r * 255)))
    gi = max(0, min(255, round(g * 255)))
    bi = max(0, min(255, round(b * 255)))
    if a < 1.0:
        ai = max(0, min(255, round(a * 255)))
        return f"#{ri:02X}{gi:02X}{bi:02X}{ai:02X}"
    return f"#{ri:02X}{gi:02X}{bi:02X}"


# ---------------------------------------------------------------------------
# Rotation conversion helpers
# ---------------------------------------------------------------------------

def css_rotation_to_pencil(degrees: float) -> float:
    """
    CSS linear-gradient angle → Pencil rotation value.

    CSS:    0°   = gradient goes top→bottom
            90°  = left→right
    Pencil: 0°   = up (same origin convention as CSS 0°)
            CCW positive.

    The mapping is a simple negation to account for CW vs CCW conventions,
    with 0° aligning at "top" for both.
    """
    return -degrees % 360


def pencil_rotation_to_css(pencil_angle: float) -> float:
    """Pencil rotation → CSS gradient angle (inverse of css_rotation_to_pencil)."""
    return -pencil_angle % 360


def figma_gradient_to_css_rotation(transform: List[List[float]]) -> float:
    """
    Extract the rotation angle (CSS degrees) from a Figma 2×3 gradient transform.

    Figma stores gradients as a [[a,b,c],[d,e,f]] matrix where
    (a, d) is the direction vector of the gradient axis.
    Returns the CSS angle in degrees (0° = top→bottom).
    """
    try:
        a = transform[0][0]
        d = transform[1][0]
        # atan2(d, a) gives the angle from the x-axis.
        # We convert to CSS angle convention (0° = top → bottom = CSS 180°).
        raw = math.degrees(math.atan2(d, a))
        # Shift to CSS 0° = from-top convention.
        return (raw + 90) % 360
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Gradient builders
# ---------------------------------------------------------------------------

def build_css_gradient(
    grad_type: str,
    rotation: float,
    stops: List[Dict[str, Any]],
) -> str:
    """
    Build a CSS gradient string from a normalized gradient dict.

    Parameters
    ----------
    grad_type : "linear" | "radial" | "angular" | "diamond"
    rotation  : Angle in CSS degrees (0° = top→bottom)
    stops     : List of {"position": float, "color": "#RRGGBB", "opacity": float}
    """
    stop_strs: List[str] = []
    for stop in stops:
        color = stop.get("color", "#000000")
        opacity = stop.get("opacity", 1.0)
        pos = stop.get("position", 0.0)
        if opacity < 1.0:
            # Inline rgba
            r, g, b = hex_to_rgb_float(color)
            color_str = f"rgba({round(r*255)},{round(g*255)},{round(b*255)},{opacity:.3f})"
        else:
            color_str = color
        stop_strs.append(f"{color_str} {round(pos * 100, 2)}%")

    stops_css = ", ".join(stop_strs)

    if grad_type == "radial":
        return f"radial-gradient(ellipse at center, {stops_css})"
    # linear, angular, diamond all fall back to linear-gradient
    return f"linear-gradient({rotation}deg, {stops_css})"


def build_pencil_gradient(
    grad_type: str,
    rotation: float,
    stops: List[Dict[str, Any]],
) -> str:
    """
    Build a Pencil-compatible gradient string.

    Pencil accepts standard CSS linear-gradient syntax with its own
    rotation convention (CCW positive, 0° = up).
    """
    pencil_angle = css_rotation_to_pencil(rotation)
    return build_css_gradient(grad_type, pencil_angle, stops)


def build_figma_gradient_stops(
    stops: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert normalized stop list → Figma gradientStops format.

    Input:  [{"position": float, "color": "#RRGGBB", "opacity": float}]
    Output: [{"position": float, "color": {r, g, b, a}}]
    """
    result: List[Dict[str, Any]] = []
    for stop in stops:
        color = stop.get("color", "#000000")
        opacity = float(stop.get("opacity", 1.0))
        figma_c = hex_to_figma_color(color)
        figma_c["a"] = opacity
        result.append({
            "position": stop.get("position", 0.0),
            "color": figma_c,
        })
    return result


# ---------------------------------------------------------------------------
# Accessibility / contrast helpers
# ---------------------------------------------------------------------------

def relative_luminance(hex_str: str) -> float:
    """
    Calculate the WCAG relative luminance of a color.
    Returns a value in [0, 1] where 0 is black and 1 is white.
    """
    r, g, b = hex_to_rgb_float(normalize_hex(hex_str))

    def _linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    """
    WCAG 2.1 contrast ratio between two hex colors.
    Returns a value from 1 (no contrast) to 21 (black on white).
    """
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_dark_color(hex_str: str) -> bool:
    """Return True if the color is perceived as dark (luminance < 0.5)."""
    return relative_luminance(hex_str) < 0.18


def suggest_text_color(background_hex: str) -> str:
    """Return '#FFFFFF' or '#000000' depending on which has better contrast."""
    lum = relative_luminance(background_hex)
    return "#FFFFFF" if lum < 0.18 else "#000000"


# ---------------------------------------------------------------------------
# Paper-specific parsing
# ---------------------------------------------------------------------------

def parse_paper_background_image(value: str) -> Optional[Dict[str, Any]]:
    """
    Parse a Paper Design background-image CSS value.

    Handles:
      - linear-gradient(...)
      - linear-gradient(in oklab, ...)
      - radial-gradient(...)
      - url("...")

    Returns a normalized dict or None if parsing fails.
    """
    value = value.strip()

    if value.startswith("url("):
        # Image reference.
        inner = value[4:].rstrip(")")
        inner = inner.strip("\"'")
        return {"type": "image", "url": inner, "mode": "fill", "opacity": 1.0}

    # Gradient — strip "in oklab" colorspace hint that Paper emits.
    normalized = re.sub(
        r"\(\s*in\s+oklab\s*,\s*",
        "(",
        value,
        flags=re.IGNORECASE,
    )
    return parse_css_gradient(normalized)
