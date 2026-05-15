"""
ir — Intermediate Representation (Universal Node Tree)
=======================================================
Public surface of the UNT layer. Import everything you need from here.

Usage:
    from design_converter.ir import UNNode, NodeType, make_frame, make_text, UNColor
"""

from .nodes import (
    AlignItems,
    BlendMode,
    GradientType,
    ImageFillMode,
    JustifyContent,
    LayoutMode,
    # ── Enums ──────────────────────────────────────────────────────────────
    NodeType,
    SizingMode,
    StrokeAlign,
    TextAlign,
    TextAutoResize,
    TextTransform,
    UNBlur,
    # ── Color ──────────────────────────────────────────────────────────────
    UNColor,
    UNCornerRadius,
    # ── Effects ────────────────────────────────────────────────────────────
    UNDropShadow,
    UNEffect,
    UNFill,
    UNGradientFill,
    UNGradientStop,
    UNImageFill,
    # ── Core Node ──────────────────────────────────────────────────────────
    UNNode,
    # ── Geometry ───────────────────────────────────────────────────────────
    UNPadding,
    UNSize,
    # ── Fills ──────────────────────────────────────────────────────────────
    UNSolidFill,
    UNStroke,
    # ── Strokes ────────────────────────────────────────────────────────────
    UNStrokeThickness,
    # ── Typography ─────────────────────────────────────────────────────────
    UNTextStyle,
    UNTextRun,
    # ── Tokens ─────────────────────────────────────────────────────────────
    UNVariableBinding,
    make_ellipse,
    # ── Factory helpers ────────────────────────────────────────────────────
    make_frame,
    make_gradient_fill,
    make_path,
    make_rect,
    make_shadow,
    make_solid_fill,
    make_text,
    un_node_from_dict,
    # ── Serialisation ──────────────────────────────────────────────────────
    un_node_to_dict,
)

__all__ = [
    # Enums
    "NodeType",
    "LayoutMode",
    "JustifyContent",
    "AlignItems",
    "SizingMode",
    "TextAlign",
    "TextTransform",
    "TextAutoResize",
    "GradientType",
    "StrokeAlign",
    "BlendMode",
    "ImageFillMode",
    # Color
    "UNColor",
    # Fills
    "UNSolidFill",
    "UNGradientStop",
    "UNGradientFill",
    "UNImageFill",
    "UNFill",
    # Strokes
    "UNStrokeThickness",
    "UNStroke",
    # Effects
    "UNDropShadow",
    "UNBlur",
    "UNEffect",
    # Geometry
    "UNPadding",
    "UNCornerRadius",
    "UNSize",
    # Typography
    "UNTextStyle",
    "UNTextRun",
    # Tokens
    "UNVariableBinding",
    # Core
    "UNNode",
    # Factories
    "make_frame",
    "make_text",
    "make_rect",
    "make_ellipse",
    "make_path",
    "make_gradient_fill",
    "make_solid_fill",
    "make_shadow",
    # Serialisation
    "un_node_to_dict",
    "un_node_from_dict",
]
