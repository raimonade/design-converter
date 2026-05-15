"""
Unit tests for Figma Reader (adapters/figma/reader.py).

Tests cover:
- Color conversion (_figma_color_to_un)
- Layout mode mapping
- Text style extraction
- Variable binding extraction
"""

import pytest
from design_converter.ir import (
    NodeType,
    LayoutMode,
    JustifyContent,
    AlignItems,
    TextAlign,
    BlendMode,
    UNColor,
    UNSolidFill,
)


class TestColorConversion:
    """Tests for _figma_color_to_un helper."""

    def test_basic_color(self):
        """Convert Figma color dict to UNColor."""
        from design_converter.adapters.figma.reader import _figma_color_to_un

        figma_color = {"r": 1.0, "g": 0.5, "b": 0.0}
        un_color = _figma_color_to_un(figma_color, opacity=0.8)

        assert un_color.r == 1.0
        assert un_color.g == 0.5
        assert un_color.b == 0.0
        assert un_color.a == 0.8

    def test_color_with_alpha_in_dict(self):
        """Color dict with alpha uses the alpha."""
        from design_converter.adapters.figma.reader import _figma_color_to_un

        figma_color = {"r": 1.0, "g": 0.0, "b": 0.0, "a": 0.5}
        un_color = _figma_color_to_un(figma_color)

        assert un_color.a == 0.5


class TestLayoutModeMapping:
    """Tests for layout mode mapping from Figma."""

    def test_horizontal_layout_value(self):
        """HORIZONTAL enum value is 'horizontal'."""
        assert LayoutMode.HORIZONTAL.value == "horizontal"

    def test_vertical_layout_value(self):
        """VERTICAL enum value is 'vertical'."""
        assert LayoutMode.VERTICAL.value == "vertical"

    def test_none_layout_value(self):
        """NONE enum value is 'none'."""
        assert LayoutMode.NONE.value == "none"


class TestJustifyContentMapping:
    """Tests for justify content mapping."""

    def test_justify_map(self):
        """Figma axis alignment maps to JustifyContent."""
        from design_converter.adapters.figma.reader import _JUSTIFY_MAP

        assert _JUSTIFY_MAP["MIN"] == JustifyContent.START
        assert _JUSTIFY_MAP["MAX"] == JustifyContent.END
        assert _JUSTIFY_MAP["CENTER"] == JustifyContent.CENTER
        assert _JUSTIFY_MAP["SPACE_BETWEEN"] == JustifyContent.SPACE_BETWEEN


class TestAlignItemsMapping:
    """Tests for align items mapping."""

    def test_align_map(self):
        """Figma counter axis alignment maps to AlignItems."""
        from design_converter.adapters.figma.reader import _ALIGN_MAP

        assert _ALIGN_MAP["MIN"] == AlignItems.START
        assert _ALIGN_MAP["MAX"] == AlignItems.END
        assert _ALIGN_MAP["CENTER"] == AlignItems.CENTER
        assert _ALIGN_MAP["STRETCH"] == AlignItems.STRETCH

    def test_baseline_falls_back_to_start(self):
        """BASELINE align falls back to START (not in IR enum)."""
        from design_converter.adapters.figma.reader import _ALIGN_MAP

        assert _ALIGN_MAP["BASELINE"] == AlignItems.START


class TestBlendModeMapping:
    """Tests for blend mode mapping."""

    def test_blend_mode_map(self):
        """Figma blend modes map to IR BlendMode enum."""
        from design_converter.adapters.figma.reader import _BLEND_MODE_MAP

        assert _BLEND_MODE_MAP["PASS_THROUGH"] == BlendMode.NORMAL
        assert _BLEND_MODE_MAP["COLOR_DODGE"] == BlendMode.DODGE
        assert _BLEND_MODE_MAP["COLOR_BURN"] == BlendMode.BURN
        assert _BLEND_MODE_MAP["NORMAL"] == BlendMode.NORMAL


class TestFigmaTypeMapping:
    """Tests for Figma node type to NodeType mapping."""

    def test_type_map(self):
        """Figma node types map to NodeType enum."""
        from design_converter.adapters.figma.reader import _FIGMA_TYPE_MAP

        assert _FIGMA_TYPE_MAP["FRAME"] == NodeType.FRAME
        assert _FIGMA_TYPE_MAP["TEXT"] == NodeType.TEXT
        assert _FIGMA_TYPE_MAP["RECTANGLE"] == NodeType.RECTANGLE
        assert _FIGMA_TYPE_MAP["ELLIPSE"] == NodeType.ELLIPSE
        assert _FIGMA_TYPE_MAP["GROUP"] == NodeType.GROUP
        assert _FIGMA_TYPE_MAP["VECTOR"] == NodeType.PATH
        assert _FIGMA_TYPE_MAP["COMPONENT"] == NodeType.COMPONENT
        assert _FIGMA_TYPE_MAP["INSTANCE"] == NodeType.INSTANCE
        assert _FIGMA_TYPE_MAP["SLICE"] is None  # Skip slice nodes


class TestFillConversion:
    """Tests for fill conversion from Figma."""

    def test_solid_fill_conversion(self):
        """Solid fill converts correctly."""
        from design_converter.adapters.figma.reader import _convert_fills

        figma_fills = [
            {
                "type": "SOLID",
                "color": {"r": 1.0, "g": 0.0, "b": 0.0},
                "opacity": 1.0,
                "visible": True,
            }
        ]

        un_fills = _convert_fills(figma_fills)
        assert len(un_fills) == 1
        assert isinstance(un_fills[0], UNSolidFill)
        assert un_fills[0].color.r == 1.0
        assert un_fills[0].color.g == 0.0

    def test_disabled_fill_skipped(self):
        """Disabled fill is skipped."""
        from design_converter.adapters.figma.reader import _convert_fills

        figma_fills = [
            {
                "type": "SOLID",
                "color": {"r": 1.0, "g": 0.0, "b": 0.0},
                "visible": False,
            }
        ]

        un_fills = _convert_fills(figma_fills)
        assert len(un_fills) == 0

    def test_none_fills_returns_empty(self):
        """None fills returns empty list."""
        from design_converter.adapters.figma.reader import _convert_fills

        un_fills = _convert_fills(None)
        assert un_fills == []


class TestTextAlignMapping:
    """Tests for text align mapping."""

    def test_text_align_map(self):
        """Figma text align maps to TextAlign."""
        from design_converter.adapters.figma.reader import _TEXT_ALIGN_MAP

        assert _TEXT_ALIGN_MAP["LEFT"] == TextAlign.LEFT
        assert _TEXT_ALIGN_MAP["CENTER"] == TextAlign.CENTER
        assert _TEXT_ALIGN_MAP["RIGHT"] == TextAlign.RIGHT
        assert _TEXT_ALIGN_MAP["JUSTIFIED"] == TextAlign.JUSTIFY
