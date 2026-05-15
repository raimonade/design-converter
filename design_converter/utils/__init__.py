"""
Design Converter — Utils Package
=================================
Pure utility functions used by all adapters.
No tool-specific logic lives here.
"""

from .color import (
    build_css_gradient,
    build_figma_gradient_stops,
    build_pencil_gradient,
    contrast_ratio,
    css_rotation_to_pencil,
    figma_color_to_hex,
    figma_gradient_to_css_rotation,
    hex_get_alpha,
    hex_set_alpha,
    hex_strip_alpha,
    hex_to_figma_color,
    hex_to_rgb_float,
    is_dark_color,
    normalize_hex,
    oklab_to_hex,
    parse_css_color,
    parse_css_gradient,
    parse_paper_background_image,
    pencil_rotation_to_css,
    relative_luminance,
    rgb_float_to_hex,
    suggest_text_color,
)
from .css import (
    apply_css_to_node,
    camel_to_kebab,
    merge_styles,
    node_to_css,
    parse_inline_style,
    parse_tailwind_class,
    parse_tailwind_classes,
)
from .tokens import (
    export_tokens_json,
    extract_tokens,
    tokens_to_css_vars,
)
from .svg import (
    circle_to_path,
    ellipse_to_path,
    line_to_path,
    normalize_svg_path,
    path_bbox,
    polyline_to_path,
    rect_to_path,
    scale_path,
    svg_tag_to_path,
    translate_path,
)

__all__ = [
    # color
    "oklab_to_hex",
    "parse_css_color",
    "parse_css_gradient",
    "parse_paper_background_image",
    "normalize_hex",
    "hex_to_rgb_float",
    "rgb_float_to_hex",
    "figma_color_to_hex",
    "hex_to_figma_color",
    "hex_get_alpha",
    "hex_set_alpha",
    "hex_strip_alpha",
    "css_rotation_to_pencil",
    "pencil_rotation_to_css",
    "figma_gradient_to_css_rotation",
    "build_pencil_gradient",
    "build_css_gradient",
    "build_figma_gradient_stops",
    "relative_luminance",
    "contrast_ratio",
    "is_dark_color",
    "suggest_text_color",
    # css
    "camel_to_kebab",
    "parse_inline_style",
    "parse_tailwind_class",
    "parse_tailwind_classes",
    "merge_styles",
    "apply_css_to_node",
    "node_to_css",
    # svg
    "circle_to_path",
    "ellipse_to_path",
    "line_to_path",
    "polyline_to_path",
    "rect_to_path",
    "normalize_svg_path",
    "svg_tag_to_path",
    "path_bbox",
    "scale_path",
    "translate_path",
    # tokens
    "extract_tokens",
    "export_tokens_json",
    "tokens_to_css_vars",
]
