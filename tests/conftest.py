"""
Pytest configuration and fixtures for design-converter tests.
"""

import pytest


@pytest.fixture
def sample_figma_frame():
    """Mock Figma frame node for testing."""
    return {
        "id": "1:2",
        "name": "Button",
        "type": "FRAME",
        "boundingBox": {"x": 100, "y": 200, "width": 120, "height": 40},
        "fills": [
            {
                "type": "SOLID",
                "color": {"r": 0.06, "g": 0.37, "b": 0.25, "a": 1.0},
                "opacity": 1.0,
            }
        ],
        "strokes": [],
        "effects": [],
        "layoutMode": "HORIZONTAL",
        "itemSpacing": 8,
        "paddingLeft": 16,
        "paddingRight": 16,
        "paddingTop": 8,
        "paddingBottom": 8,
        "primaryAxisAlignItems": "CENTER",
        "counterAxisAlignItems": "CENTER",
        "children": [],
    }


@pytest.fixture
def sample_figma_text():
    """Mock Figma text node with rich text runs."""
    return {
        "id": "1:3",
        "name": "Label",
        "type": "TEXT",
        "boundingBox": {"x": 116, "y": 210, "width": 88, "height": 20},
        "characters": "Hello World",
        "style": {
            "fontFamily": "Inter",
            "fontSize": 14,
            "fontWeight": 600,
            "textAlignHorizontal": "CENTER",
        },
        "characterStyleOverrides": [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
        "styleOverrideTable": {
            "1": {
                "fontSize": 16,
                "fills": [{"type": "SOLID", "color": {"r": 1, "g": 0, "b": 0, "a": 1}}],
            }
        },
        "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 1}}],
    }


@pytest.fixture
def sample_unnode_frame():
    """Sample UNNode FRAME for testing."""
    from design_converter.ir import (
        UNNode,
        NodeType,
        LayoutMode,
        JustifyContent,
        AlignItems,
        UNSolidFill,
        UNColor,
        UNPadding,
        UNCornerRadius,
        UNSize,
        SizingMode,
    )

    node = UNNode(
        type=NodeType.FRAME,
        id="test-1",
        name="TestButton",
        x=100,
        y=200,
        width=UNSize.fixed(120),
        height=UNSize.fixed(40),
        layout=LayoutMode.HORIZONTAL,
        gap=8,
        padding=UNPadding.xy(16, 8),
        justify_content=JustifyContent.CENTER,
        align_items=AlignItems.CENTER,
        corner_radius=UNCornerRadius.all(8),
    )
    node.fills.append(UNSolidFill(color=UNColor.from_hex("#0F5F40")))
    return node


@pytest.fixture
def sample_unnode_text():
    """Sample UNNode TEXT for testing."""
    from design_converter.ir import (
        UNNode,
        NodeType,
        UNTextStyle,
        TextAlign,
        TextAutoResize,
        TextTransform,
        UNSolidFill,
        UNColor,
        UNSize,
    )

    node = UNNode(
        type=NodeType.TEXT,
        id="test-2",
        name="TestLabel",
        x=116,
        y=210,
        width=UNSize.hug(),
        height=UNSize.hug(),
        text_content="Hello World",
        text_style=UNTextStyle(
            font_family="Inter",
            font_size=14,
            font_weight="600",
            text_align=TextAlign.CENTER,
            text_auto_resize=TextAutoResize.WIDTH_HEIGHT,
        ),
    )
    node.fills.append(UNSolidFill(color=UNColor.from_hex("#000000")))
    return node
