"""
SVG Utilities
=============
Helpers for working with SVG geometry in the design converter.

Primary uses:
  - Paper JSX outputs SVG elements (circle, polyline, line) — convert to path d=
  - Pencil PATH nodes use SVG path geometry strings
  - Figma VECTOR nodes use SVG geometry
  - Normalise / transform path data for cross-tool compatibility

SVG path command reference (used throughout):
  M x y       — moveto (absolute)
  m dx dy     — moveto (relative)
  L x y       — lineto (absolute)
  l dx dy     — lineto (relative)
  H x         — horizontal lineto
  V y         — vertical lineto
  C cx1 cy1 cx2 cy2 x y  — cubic bezier
  Q cx cy x y             — quadratic bezier
  A rx ry x-rot large-arc sweep x y  — arc
  Z           — closepath
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple


def _f(value: float) -> str:
    """Format a float for SVG path: remove trailing zeros."""
    if value == int(value):
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# SVG primitive → path d= converters
# ---------------------------------------------------------------------------


def circle_to_path(cx: float, cy: float, r: float) -> str:
    """
    Convert SVG <circle cx cy r> to an equivalent SVG path d= string.
    Uses two arc commands (top-half + bottom-half) to form a full circle.

    Example: circle_to_path(11, 11, 8)
      → "M 3 11 A 8 8 0 1 0 19 11 A 8 8 0 1 0 3 11"
    """
    # Start at left-most point, arc to right-most, arc back
    x1 = cx - r
    x2 = cx + r
    # First arc: left → right (large arc, sweep=0 → CCW)
    # Second arc: right → left (large arc, sweep=0)
    return (
        f"M {_f(x1)} {_f(cy)} "
        f"A {_f(r)} {_f(r)} 0 1 0 {_f(x2)} {_f(cy)} "
        f"A {_f(r)} {_f(r)} 0 1 0 {_f(x1)} {_f(cy)}"
    )


def ellipse_to_path(cx: float, cy: float, rx: float, ry: float) -> str:
    """
    Convert SVG <ellipse cx cy rx ry> to SVG path d= string.
    """
    x1 = cx - rx
    x2 = cx + rx
    return (
        f"M {_f(x1)} {_f(cy)} "
        f"A {_f(rx)} {_f(ry)} 0 1 0 {_f(x2)} {_f(cy)} "
        f"A {_f(rx)} {_f(ry)} 0 1 0 {_f(x1)} {_f(cy)}"
    )


def polyline_to_path(points_str: str, closed: bool = False) -> str:
    """
    Convert SVG <polyline points="x1 y1 x2 y2 ..."> (or <polygon>) to path d=.

    Args:
        points_str: "7 10 12 15 17 10"  or  "7,10 12,15 17,10"
        closed: True for <polygon> (adds Z), False for <polyline>

    Returns SVG path d= string.
    """
    # Normalise: replace commas with spaces, split on whitespace
    tokens = re.sub(r"[,\s]+", " ", points_str.strip()).split()
    if len(tokens) < 4 or len(tokens) % 2 != 0:
        return ""

    coords = [float(t) for t in tokens]
    parts = [f"M {_f(coords[0])} {_f(coords[1])}"]
    for i in range(2, len(coords), 2):
        parts.append(f"L {_f(coords[i])} {_f(coords[i + 1])}")
    if closed:
        parts.append("Z")
    return " ".join(parts)


def polygon_to_path(points_str: str) -> str:
    """Convert SVG <polygon points=...> to closed path."""
    return polyline_to_path(points_str, closed=True)


def line_to_path(x1: float, y1: float, x2: float, y2: float) -> str:
    """
    Convert SVG <line x1 y1 x2 y2> to path d= string.
    """
    return f"M {_f(x1)} {_f(y1)} L {_f(x2)} {_f(y2)}"


def rect_to_path(
    x: float,
    y: float,
    width: float,
    height: float,
    rx: float = 0.0,
    ry: float = 0.0,
) -> str:
    """
    Convert SVG <rect> to path d= string.
    Handles rounded corners via rx/ry.
    """
    if rx == 0 and ry == 0:
        x2, y2 = x + width, y + height
        return (
            f"M {_f(x)} {_f(y)} "
            f"L {_f(x2)} {_f(y)} "
            f"L {_f(x2)} {_f(y2)} "
            f"L {_f(x)} {_f(y2)} Z"
        )

    # Clamp radii
    rx = min(rx, width / 2)
    ry = min(ry if ry else rx, height / 2)
    x2, y2 = x + width, y + height

    return (
        f"M {_f(x + rx)} {_f(y)} "
        f"L {_f(x2 - rx)} {_f(y)} "
        f"A {_f(rx)} {_f(ry)} 0 0 1 {_f(x2)} {_f(y + ry)} "
        f"L {_f(x2)} {_f(y2 - ry)} "
        f"A {_f(rx)} {_f(ry)} 0 0 1 {_f(x2 - rx)} {_f(y2)} "
        f"L {_f(x + rx)} {_f(y2)} "
        f"A {_f(rx)} {_f(ry)} 0 0 1 {_f(x)} {_f(y2 - ry)} "
        f"L {_f(x)} {_f(y + ry)} "
        f"A {_f(rx)} {_f(ry)} 0 0 1 {_f(x + rx)} {_f(y)} Z"
    )


# ---------------------------------------------------------------------------
# Compound path builder
# ---------------------------------------------------------------------------


def combine_paths(*path_strings: str) -> str:
    """
    Join multiple SVG path d= strings into one compound path.
    Each sub-path starts with its own M command, so they're independent.

    Example:
        combine_paths(
            "M 3 11 A 8 8 0 1 0 19 11 A 8 8 0 1 0 3 11",
            "M 21 21 L 16.65 16.65"
        )
        → "M 3 11 A 8 8 0 1 0 19 11 A 8 8 0 1 0 3 11 M 21 21 L 16.65 16.65"
    """
    return " ".join(p.strip() for p in path_strings if p.strip())


# ---------------------------------------------------------------------------
# Path normalisation & transformation
# ---------------------------------------------------------------------------


def scale_path(path_d: str, sx: float, sy: Optional[float] = None) -> str:
    """
    Scale all absolute coordinates in a path d= string.
    Only handles absolute M, L, C, Q, A commands (no relative).
    Sufficient for icon paths that start from known coordinates.

    Args:
        path_d: SVG path d= string
        sx: x scale factor
        sy: y scale factor (defaults to sx for uniform scaling)
    """
    if sy is None:
        sy = sx
    if sx == 1.0 and sy == 1.0:
        return path_d

    def scale_num(m: re.Match) -> str:
        # Called for every number token; we track context separately
        return m.group(0)  # placeholder — actual scaling below

    # Tokenise path into commands + number sequences
    tokens = re.findall(
        r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?[\d]*\.?[\d]+(?:[eE][-+]?\d+)?", path_d
    )
    result = []
    i = 0
    cmd = "M"
    while i < len(tokens):
        t = tokens[i]
        if re.match(r"^[MmLlHhVvCcSsQqTtAaZz]$", t):
            cmd = t
            result.append(t)
            i += 1
            continue

        # Number — context depends on current command
        try:
            val = float(t)
        except ValueError:
            result.append(t)
            i += 1
            continue

        cmd_upper = cmd.upper()

        if cmd_upper in ("M", "L", "T"):
            # pairs: x y x y ...
            if (i - _last_cmd_idx(tokens, i)) % 2 == 0:
                result.append(_f(val * sx))
            else:
                result.append(_f(val * sy))
        elif cmd_upper == "H":
            result.append(_f(val * sx))
        elif cmd_upper == "V":
            result.append(_f(val * sy))
        elif cmd_upper in ("C", "S", "Q"):
            # C: cx1 cy1 cx2 cy2 x y  (6 per segment)
            # S: cx2 cy2 x y  (4 per)
            # Q: cx cy x y  (4 per)
            seg_len = {"C": 6, "S": 4, "Q": 4}.get(cmd_upper, 2)
            pos_in_seg = (i - _last_cmd_idx(tokens, i)) % seg_len
            result.append(_f(val * (sx if pos_in_seg % 2 == 0 else sy)))
        elif cmd_upper == "A":
            # A rx ry x-rotation large-arc-flag sweep-flag x y  (7 per arc)
            pos_in_arc = (i - _last_cmd_idx(tokens, i)) % 7
            if pos_in_arc == 0:
                result.append(_f(val * sx))  # rx
            elif pos_in_arc == 1:
                result.append(_f(val * sy))  # ry
            elif pos_in_arc in (2, 3, 4):
                result.append(t)  # rotation, flags — don't scale
            elif pos_in_arc == 5:
                result.append(_f(val * sx))  # x
            elif pos_in_arc == 6:
                result.append(_f(val * sy))  # y
            else:
                result.append(t)
        else:
            result.append(t)
        i += 1

    return " ".join(result)


def _last_cmd_idx(tokens: List[str], current: int) -> int:
    """Find the index of the last command token before current."""
    for j in range(current - 1, -1, -1):
        if re.match(r"^[MmLlHhVvCcSsQqTtAaZz]$", tokens[j]):
            return j + 1
    return 0


def translate_path(path_d: str, dx: float, dy: float) -> str:
    """
    Apply a translation to all absolute M/L coordinates.
    Simple implementation for icon repositioning.
    """
    if dx == 0 and dy == 0:
        return path_d
    # Apply via SVG transform wrapper (preserves accuracy)
    return path_d  # For now return as-is; transform handled at render level


def normalise_path(path_d: str) -> str:
    """
    Clean up a path d= string:
    - Collapse multiple spaces
    - Remove redundant spaces around commands
    - Normalise decimal formatting
    """
    if not path_d:
        return ""
    # Collapse whitespace
    s = re.sub(r"\s+", " ", path_d.strip())
    # Ensure space after commands
    s = re.sub(r"([MmLlHhVvCcSsQqTtAaZz])", r"\1 ", s)
    # Collapse again
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# SVG element string parser  (from Paper JSX)
# ---------------------------------------------------------------------------


def parse_svg_element(tag: str, attrs: dict) -> Optional[str]:
    """
    Convert a parsed SVG element (tag name + attributes dict) to path d= string.

    Handles: circle, ellipse, line, polyline, polygon, path, rect

    Returns path d= string, or None if unrecognised / no geometry.
    """
    tag = tag.lower()

    if tag == "circle":
        cx = float(attrs.get("cx", 0))
        cy = float(attrs.get("cy", 0))
        r = float(attrs.get("r", 0))
        return circle_to_path(cx, cy, r) if r > 0 else None

    elif tag == "ellipse":
        cx = float(attrs.get("cx", 0))
        cy = float(attrs.get("cy", 0))
        rx = float(attrs.get("rx", 0))
        ry = float(attrs.get("ry", rx))
        return ellipse_to_path(cx, cy, rx, ry) if rx > 0 else None

    elif tag == "line":
        x1 = float(attrs.get("x1", 0))
        y1 = float(attrs.get("y1", 0))
        x2 = float(attrs.get("x2", 0))
        y2 = float(attrs.get("y2", 0))
        return line_to_path(x1, y1, x2, y2)

    elif tag == "polyline":
        pts = attrs.get("points", "")
        return polyline_to_path(pts) if pts else None

    elif tag == "polygon":
        pts = attrs.get("points", "")
        return polygon_to_path(pts) if pts else None

    elif tag == "path":
        return normalise_path(attrs.get("d", ""))

    elif tag == "rect":
        x = float(attrs.get("x", 0))
        y = float(attrs.get("y", 0))
        w = float(attrs.get("width", 0))
        h = float(attrs.get("height", 0))
        rx = float(attrs.get("rx", 0))
        ry = float(attrs.get("ry", 0))
        return rect_to_path(x, y, w, h, rx, ry) if w > 0 and h > 0 else None

    return None


# ---------------------------------------------------------------------------
# Bounding box estimation
# ---------------------------------------------------------------------------


def estimate_path_bounds(path_d: str) -> Tuple[float, float, float, float]:
    """
    Estimate the bounding box of a path from its coordinate values.
    This is approximate (ignores curve control points) but useful for
    determining icon dimensions.

    Returns: (min_x, min_y, max_x, max_y)
    """
    nums = re.findall(r"[-+]?[\d]*\.?[\d]+(?:[eE][-+]?\d+)?", path_d)
    if not nums:
        return (0, 0, 24, 24)  # Default icon size

    floats = [float(n) for n in nums]
    # Crude: treat alternating numbers as x/y
    xs = floats[0::2]
    ys = floats[1::2]
    if not xs or not ys:
        return (0, 0, 24, 24)

    return (min(xs), min(ys), max(xs), max(ys))


def path_dimensions(path_d: str) -> Tuple[float, float]:
    """
    Estimate width and height of a path from bounding box.
    Returns (width, height).
    """
    min_x, min_y, max_x, max_y = estimate_path_bounds(path_d)
    return (max(max_x - min_x, 1.0), max(max_y - min_y, 1.0))


# ---------------------------------------------------------------------------
# Common icon path library
# (pre-built paths for icons used frequently in design systems)
# ---------------------------------------------------------------------------

ICONS: dict = {
    # Lucide / Heroicons style (24×24 viewBox)
    "search": combine_paths(
        circle_to_path(11, 11, 8),
        "M 21 21 L 16.65 16.65",
    ),
    "send": "M 22 2 L 11 13 M 22 2 L 15 22 L 11 13 L 2 9 L 22 2 Z",
    "download": (
        "M 21 15 V 19 A 2 2 0 0 1 19 21 H 5 A 2 2 0 0 1 3 19 V 15 "
        "M 7 10 L 12 15 L 17 10 M 12 15 V 3"
    ),
    "upload": (
        "M 21 15 V 19 A 2 2 0 0 1 19 21 H 5 A 2 2 0 0 1 3 19 V 15 "
        "M 17 8 L 12 3 L 7 8 M 12 3 V 15"
    ),
    "swap": (
        "M 17 1 L 21 5 L 17 9 "
        "M 3 11 V 9 A 4 4 0 0 1 7 5 H 21 "
        "M 7 23 L 3 19 L 7 15 "
        "M 21 13 V 15 A 4 4 0 0 1 17 19 H 3"
    ),
    "dollar": "M 12 1 L 12 23 M 17 5 H 9.5 A 3.5 3.5 0 0 0 9.5 12 H 14.5 A 3.5 3.5 0 0 1 14.5 19 H 6",
    "home": (
        "M 3 9 L 12 2 L 21 9 V 20 A 1 1 0 0 1 20 21 H 15 V 16 H 9 V 21 H 4 "
        "A 1 1 0 0 1 3 20 Z"
    ),
    "chart_bar": "M 18 20 V 10 M 12 20 V 4 M 6 20 V 14",
    "wallet": (
        "M 21 12 H 3 A 2 2 0 0 1 1 10 V 6 A 2 2 0 0 1 3 4 H 19 A 2 2 0 0 1 21 6 V 10 "
        "M 21 12 V 18 A 2 2 0 0 1 19 20 H 3 A 2 2 0 0 1 1 18 V 12 "
        "M 16 16 H 16.01"
    ),
    "arrow_right": "M 5 12 H 19 M 12 5 L 19 12 L 12 19",
    "arrow_left": "M 19 12 H 5 M 12 5 L 5 12 L 12 19",
    "arrow_up": "M 12 19 V 5 M 5 12 L 12 5 L 19 12",
    "arrow_down": "M 12 5 V 19 M 19 12 L 12 19 L 5 12",
    "check": "M 20 6 L 9 17 L 4 12",
    "x": "M 18 6 L 6 18 M 6 6 L 18 18",
    "plus": "M 12 5 V 19 M 5 12 H 19",
    "minus": "M 5 12 H 19",
    "chevron_right": "M 9 18 L 15 12 L 9 6",
    "chevron_left": "M 15 18 L 9 12 L 15 6",
    "chevron_down": "M 6 9 L 12 15 L 18 9",
    "chevron_up": "M 18 15 L 12 9 L 6 15",
    "eye": combine_paths(
        "M 1 12 C 1 12 5 4 12 4 C 19 4 23 12 23 12 C 23 12 19 20 12 20 C 5 20 1 12 1 12",
        circle_to_path(12, 12, 3),
    ),
    "copy": (
        "M 20 9 H 11 A 2 2 0 0 0 9 11 V 20 A 2 2 0 0 0 11 22 H 20 "
        "A 2 2 0 0 0 22 20 V 11 A 2 2 0 0 0 20 9 Z "
        "M 5 15 H 4 A 2 2 0 0 1 2 13 V 4 A 2 2 0 0 1 4 2 H 13 "
        "A 2 2 0 0 1 15 4 V 5"
    ),
    "settings": combine_paths(
        circle_to_path(12, 12, 3),
        "M 19.4 15 A 1.65 1.65 0 0 0 21 13.35 V 10.65 A 1.65 1.65 0 0 0 19.4 9 "
        "L 18.6 8.7 A 1.65 1.65 0 0 1 18.3 6.3 L 18.7 5.7 "
        "A 1.65 1.65 0 0 0 18.7 3.4 L 17 1.7 "
        "A 1.65 1.65 0 0 0 14.7 1.7 L 14.1 2.1 "
        "A 1.65 1.65 0 0 1 11.7 1.8 L 11.4 1 "
        "A 1.65 1.65 0 0 0 9.75 0 H 7.05 "
        "A 1.65 1.65 0 0 0 5.4 1 L 5.1 1.8 "
        "A 1.65 1.65 0 0 1 2.7 2.1 L 2.1 1.7 "
        "A 1.65 1.65 0 0 0 -0.2 1.7 L -1.9 3.4 "
        "A 1.65 1.65 0 0 0 -1.9 5.7 L -1.5 6.3 "
        "A 1.65 1.65 0 0 1 -1.8 8.7 L -2.6 9 "
        "A 1.65 1.65 0 0 0 -4.2 10.65 V 13.35 "
        "A 1.65 1.65 0 0 0 -2.6 15 L -1.8 15.3",
    ),
    "bell": "M 18 8 A 6 6 0 0 0 6 8 C 6 15 3 17 3 17 H 21 C 21 17 18 15 18 8 M 13.73 21 A 2 2 0 0 1 10.27 21",
    "user": combine_paths(
        circle_to_path(12, 8, 4),
        "M 4 20 C 4 17.8 7.6 16 12 16 C 16.4 16 20 17.8 20 20",
    ),
    "qrcode": (
        "M 3 3 H 9 V 9 H 3 Z M 15 3 H 21 V 9 H 15 Z M 3 15 H 9 V 21 H 3 Z "
        "M 5 5 H 7 V 7 H 5 Z M 17 5 H 19 V 7 H 17 Z M 5 17 H 7 V 19 H 5 Z "
        "M 15 15 H 17 V 17 H 15 Z M 19 15 H 21 V 17 H 19 Z "
        "M 15 19 H 17 V 21 H 15 Z M 19 19 H 21 V 21 H 19 Z"
    ),
}


def get_icon(name: str) -> Optional[str]:
    """Return a pre-built SVG path for a named icon, or None."""
    return ICONS.get(name.lower().replace("-", "_").replace(" ", "_"))


# ---------------------------------------------------------------------------
# Stroke attribute helpers  (for Paper/Pencil path nodes)
# ---------------------------------------------------------------------------


def stroke_attrs_to_css(
    stroke: Optional[str],
    stroke_width: float = 2.0,
    stroke_linecap: str = "round",
    stroke_linejoin: str = "round",
) -> dict:
    """
    Build a CSS-style stroke dict from SVG stroke attributes.
    Used when converting Paper JSX SVG elements.
    """
    if not stroke or stroke == "none":
        return {}
    return {
        "stroke": stroke,
        "stroke-width": stroke_width,
        "stroke-linecap": stroke_linecap,
        "stroke-linejoin": stroke_linejoin,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
# Public aliases (the __init__.py public API uses these names)
# ---------------------------------------------------------------------------

normalize_svg_path = normalise_path
path_bbox = estimate_path_bounds
svg_tag_to_path = parse_svg_element


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== SVG converters ===")
    print("circle(11,11,8):", circle_to_path(11, 11, 8))
    print("line(12,1,12,23):", line_to_path(12, 1, 12, 23))
    print("polyline(7 10 12 15 17 10):", polyline_to_path("7 10 12 15 17 10"))
    print("polygon(17 1 21 5 17 9):", polygon_to_path("17 1 21 5 17 9"))
    print("rect(0,0,24,24,4):", rect_to_path(0, 0, 24, 24, 4))
    print()

    print("=== Icon library ===")
    for name in ("search", "send", "download", "swap", "dollar", "home"):
        path = get_icon(name)
        print(f"{name}: {(path or '')[:60]}...")
    print()

    print("=== parse_svg_element ===")
    print(parse_svg_element("circle", {"cx": "11", "cy": "11", "r": "8"}))
    print(parse_svg_element("polyline", {"points": "7 10 12 15 17 10"}))
    print(parse_svg_element("line", {"x1": "12", "y1": "1", "x2": "12", "y2": "23"}))
    print()

    print("=== bounds ===")
    p = get_icon("send") or ""
    print("send bounds:", estimate_path_bounds(p))
    print("send dims:", path_dimensions(p))
