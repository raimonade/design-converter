"""
utils/tokens.py — W3C Design Tokens Community Group (DTCG) 2025.10 exporter
============================================================================

Walk a UNNode tree and extract design tokens in DTCG format:

    {
      "color": {
        "brand/primary": {"$type": "color", "$value": "#FF5733FF", "$description": "..."},
        ...
      },
      "typography": {
        "heading/h1": {"$type": "typography", "$value": {...}, "$description": "..."},
        ...
      },
      "shadow": {
        "elevation/card": {"$type": "shadow", "$value": {...}, "$description": "..."},
        ...
      },
      "dimension": {
        "spacing/gap": {"$type": "dimension", "$value": "8px"},
        ...
      }
    }

DTCG spec reference: https://design-tokens.github.io/community-group/format/

Usage:
    from utils.tokens import extract_tokens, export_tokens_json

    tokens = extract_tokens(root_node)
    export_tokens_json(root_node, "tokens.json")
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lazy imports from IR (avoids circular at module level)
# ---------------------------------------------------------------------------

def _ir():
    from ir import (
        UNNode, UNSolidFill, UNGradientFill, UNImageFill,
        UNDropShadow, UNBlur, UNTextStyle, UNColor,
        NodeType, GradientType,
    )
    return UNNode, UNSolidFill, UNGradientFill, UNImageFill, UNDropShadow, UNBlur, UNTextStyle, UNColor, NodeType, GradientType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    """Convert a human name to a slug suitable for a token key."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "unnamed"


def _color_to_hex8(color: Any) -> str:
    """
    Convert a UNColor to 8-digit hex (#RRGGBBAA).
    DTCG 2025.10 uses 8-digit hex (alpha included).
    """
    r = max(0, min(255, round(color.r * 255)))
    g = max(0, min(255, round(color.g * 255)))
    b = max(0, min(255, round(color.b * 255)))
    a = max(0, min(255, round(color.a * 255)))
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


def _walk(node: Any) -> Iterator[Any]:
    """Depth-first walk of a UNNode tree, yielding every node."""
    yield node
    for child in getattr(node, "children", []):
        yield from _walk(child)


def _make_key(parts: List[str]) -> str:
    return "/".join(_slug(p) for p in parts if p)


# ---------------------------------------------------------------------------
# Per-token-type extractors
# ---------------------------------------------------------------------------

def _collect_colors(root: Any) -> Dict[str, Any]:
    """
    Extract DTCG color tokens from all solid fills in the tree.
    De-duplicates by hex value — same color produces the same token.
    """
    UNNode, UNSolidFill, *_ = _ir()

    seen: Dict[str, str] = {}    # hex8 → token_name
    tokens: Dict[str, Any] = {}

    for node in _walk(root):
        fills = getattr(node, "fills", []) or []
        for fill in fills:
            if not isinstance(fill, UNSolidFill):
                continue
            color = fill.color
            hex8 = _color_to_hex8(color)

            if hex8 in seen:
                continue            # already recorded this exact color

            # Build a meaningful name from the node context
            node_slug = _slug(getattr(node, "name", "layer"))
            token_name = _make_key([node_slug, "fill"])

            # Deduplicate token names
            base = token_name
            suffix = 1
            while token_name in tokens:
                token_name = f"{base}-{suffix}"
                suffix += 1

            seen[hex8] = token_name
            tokens[token_name] = {
                "$type": "color",
                "$value": hex8,
                "$description": f"Fill color from layer '{getattr(node, 'name', '')}'",
            }

    return tokens


def _collect_typography(root: Any) -> Dict[str, Any]:
    """
    Extract DTCG typography tokens from all TEXT nodes.
    De-duplicates by (family, size, weight, style) signature.
    """
    from ir import NodeType
    seen: Dict[str, str] = {}   # sig → token_name
    tokens: Dict[str, Any] = {}

    for node in _walk(root):
        if getattr(node, "type", None) != NodeType.TEXT:
            continue
        ts = getattr(node, "text_style", None)
        if ts is None:
            continue

        family = getattr(ts, "font_family", "Inter") or "Inter"
        size = getattr(ts, "font_size", 14) or 14
        weight = getattr(ts, "font_weight", "400") or "400"
        style = getattr(ts, "font_style", "normal") or "normal"
        line_h = getattr(ts, "line_height", None)
        ls = getattr(ts, "letter_spacing", 0) or 0

        sig = f"{family}|{size}|{weight}|{style}|{line_h}|{ls}"
        if sig in seen:
            continue

        node_slug = _slug(getattr(node, "name", "text"))
        token_name = _make_key([node_slug, "type"])

        base = token_name
        suffix = 1
        while token_name in tokens:
            token_name = f"{base}-{suffix}"
            suffix += 1

        seen[sig] = token_name

        value: Dict[str, Any] = {
            "fontFamily": family,
            "fontSize": f"{size}px",
            "fontWeight": weight,
            "fontStyle": style,
            "letterSpacing": f"{ls}px",
        }
        if line_h is not None:
            value["lineHeight"] = f"{line_h}px"

        tokens[token_name] = {
            "$type": "typography",
            "$value": value,
            "$description": f"Typography from layer '{getattr(node, 'name', '')}'",
        }

    return tokens


def _collect_shadows(root: Any) -> Dict[str, Any]:
    """
    Extract DTCG shadow tokens from UNDropShadow effects.
    """
    from ir import UNDropShadow
    seen: set = set()
    tokens: Dict[str, Any] = {}

    for node in _walk(root):
        effects = getattr(node, "effects", []) or []
        for effect in effects:
            if not isinstance(effect, UNDropShadow):
                continue
            color = effect.color
            hex8 = _color_to_hex8(color)
            ox = getattr(effect, "offset_x", 0)
            oy = getattr(effect, "offset_y", 0)
            blur = getattr(effect, "blur", 0) or 0
            spread = getattr(effect, "spread", 0) or 0

            sig = f"{hex8}|{ox}|{oy}|{blur}|{spread}"
            if sig in seen:
                continue
            seen.add(sig)

            node_slug = _slug(getattr(node, "name", "layer"))
            token_name = _make_key([node_slug, "shadow"])

            base = token_name
            suffix = 1
            while token_name in tokens:
                token_name = f"{base}-{suffix}"
                suffix += 1

            tokens[token_name] = {
                "$type": "shadow",
                "$value": {
                    "color": hex8,
                    "offsetX": f"{ox}px",
                    "offsetY": f"{oy}px",
                    "blur": f"{blur}px",
                    "spread": f"{spread}px",
                },
                "$description": f"Drop shadow from layer '{getattr(node, 'name', '')}'",
            }

    return tokens


def _collect_dimensions(root: Any) -> Dict[str, Any]:
    """
    Extract DTCG dimension tokens from frame gap values.
    These are layout spacing tokens — only emitted when non-zero.
    """
    seen: set = set()
    tokens: Dict[str, Any] = {}

    for node in _walk(root):
        gap = getattr(node, "gap", 0) or 0
        if gap <= 0:
            continue
        if gap in seen:
            continue
        seen.add(gap)

        node_slug = _slug(getattr(node, "name", "frame"))
        token_name = _make_key([node_slug, "gap"])

        base = token_name
        suffix = 1
        while token_name in tokens:
            token_name = f"{base}-{suffix}"
            suffix += 1

        tokens[token_name] = {
            "$type": "dimension",
            "$value": f"{gap}px",
            "$description": f"Gap/spacing from layer '{getattr(node, 'name', '')}'",
        }

    return tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_tokens(root: Any) -> Dict[str, Dict[str, Any]]:
    """
    Walk a UNNode tree and return a DTCG 2025.10-format token dict.

    Structure:
        {
          "color":      { "token/name": {"$type":"color", "$value":"#...", ...} },
          "typography": { "token/name": {"$type":"typography", "$value":{...}, ...} },
          "shadow":     { "token/name": {"$type":"shadow", "$value":{...}, ...} },
          "dimension":  { "token/name": {"$type":"dimension", "$value":"Npx", ...} },
        }
    """
    return {
        "color": _collect_colors(root),
        "typography": _collect_typography(root),
        "shadow": _collect_shadows(root),
        "dimension": _collect_dimensions(root),
    }


def export_tokens_json(root: Any, output_path: str, *, indent: int = 2) -> Dict[str, int]:
    """
    Extract tokens from `root` and write DTCG JSON to `output_path`.

    Returns a summary dict with counts per category.

    Example:
        counts = export_tokens_json(un_tree, "tokens.json")
        # {"color": 12, "typography": 4, "shadow": 3, "dimension": 7}
    """
    tokens = extract_tokens(root)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(tokens, fh, indent=indent, ensure_ascii=False)
    return {k: len(v) for k, v in tokens.items()}


def tokens_to_css_vars(tokens: Dict[str, Dict[str, Any]], *, prefix: str = "un") -> str:
    """
    Convert a DTCG color + dimension token dict to a CSS :root { --var: value; } block.

    Only color and dimension tokens are converted (typography and shadow are complex
    and are best handled by individual CSS properties).
    """
    lines: List[str] = [":root {"]
    for token_name, token in tokens.get("color", {}).items():
        var = f"--{prefix}-{token_name.replace('/', '-')}"
        lines.append(f"  {var}: {token['$value']};")
    for token_name, token in tokens.get("dimension", {}).items():
        var = f"--{prefix}-{token_name.replace('/', '-')}"
        lines.append(f"  {var}: {token['$value']};")
    lines.append("}")
    return "\n".join(lines)
