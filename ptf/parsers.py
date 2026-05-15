from __future__ import annotations

import re
from typing import Optional

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


def parse_px(value: str | int | float | None) -> Optional[float]:
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
    color = parse_hex_color(hex_str)
    if color is None:
        return None, 1.0
    a = color.pop("a", 1.0)
    return color, a


def format_color(color: dict) -> str:
    return f"{{r:{color['r']:.4f},g:{color['g']:.4f},b:{color['b']:.4f}}}"


def map_font_family(raw: str) -> str:
    families = [f.strip().strip('"').strip("'") for f in raw.split(",")]
    for fam in families:
        mapped = FONT_FAMILY_MAP.get(fam.lower())
        if mapped:
            return mapped
    return "Inter"


def map_font_weight(weight: int | str) -> str:
    w = int(weight) if isinstance(weight, str) else weight
    return WEIGHT_STYLE_MAP.get(w, "Regular")


def parse_letter_spacing(value: str) -> Optional[str]:
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
        return f"{{value:{v},unit:'PIXELS'}}"
    except ValueError:
        return None


def parse_border_radius(styles: dict) -> Optional[str]:
    tl = parse_px(styles.get("borderTopLeftRadius"))
    tr = parse_px(styles.get("borderTopRightRadius"))
    br = parse_px(styles.get("borderBottomRightRadius"))
    bl = parse_px(styles.get("borderBottomLeftRadius"))

    uniform = parse_px(styles.get("borderRadius"))

    if uniform is not None and uniform > 0:
        if uniform >= 999:
            return "cornerRadius_pill"
        return f"cornerRadius_uniform_{uniform}"

    if any(v is not None and v > 0 for v in [tl, tr, br, bl]):
        return f"cornerRadius_individual_{tl or 0}_{tr or 0}_{br or 0}_{bl or 0}"

    return None


def parse_box_shadow(value: str) -> list[dict]:
    if not value:
        return []

    effects = []
    parts = re.split(r",\s*(?=#)", value.strip())
    for part in parts:
        part = part.strip()
        if not part:
            continue

        is_inset = "inset" in part
        part_clean = part.replace("inset", "").strip()

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
