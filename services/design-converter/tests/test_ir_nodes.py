"""
Unit tests for UNNode IR dataclasses, enums, and factory functions.

Run: python3 tests/test_ir_nodes.py
"""
import sys

# Add parent to path for imports
sys.path.insert(0, "/Users/william/Projects Parent Folder/DesignDev/services/design-converter")

from ir import (
    UNNode,
    NodeType,
    UNColor,
    UNSize,
    UNPadding,
    UNCornerRadius,
    UNTextRun,
    UNVariableBinding,
    UNSolidFill,
    UNStrokeThickness,
    UNDropShadow,
    LayoutMode,
    SizingMode,
    JustifyContent,
    AlignItems,
    TextAlign,
    TextTransform,
    BlendMode,
    make_frame,
    make_text,
    make_rect,
    make_ellipse,
    make_solid_fill,
    make_shadow,
    un_node_to_dict,
    un_node_from_dict,
)

# Simple test runner
passed = 0
failed = 0

def test(name):
    """Decorator to mark a test function."""
    def decorator(fn):
        global passed, failed
        try:
            fn()
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}")
            print(f"  {e}")
            failed += 1
    return decorator

def assert_eq(a, b, msg=""):
    """Simple assertion."""
    if a != b:
        raise AssertionError(f"{msg}: {a!r} != {b!r}")

def assert_true(cond, msg=""):
    """Assert condition is true."""
    if not cond:
        raise AssertionError(f"{msg}: {cond} is not True")

# ============================================
# Tests
# ============================================

class TestUNNodeDefaults:
    """Test UNNode has correct default values."""

    @test("UNNode: default type is FRAME")
    def _():
        node = UNNode()  # type defaults to FRAME
        assert_eq(node.type, NodeType.FRAME)

    @test("UNNode: default name is 'Node'")
    def _():
        node = UNNode(type=NodeType.FRAME)
        assert_eq(node.name, "Node")

    @test("UNNode: default geometry")
    def _():
        node = UNNode(type=NodeType.FRAME)
        assert_eq(node.x, 0.0)
        assert_eq(node.y, 0.0)
        assert_eq(node.width.value, 100.0)
        assert_eq(node.height.value, 100.0)
        assert_eq(node.rotation, 0.0)

    @test("UNNode: default layout")
    def _():
        node = UNNode(type=NodeType.FRAME)
        assert_eq(node.layout, LayoutMode.NONE)
        assert_eq(node.gap, 0.0)
        assert_eq(node.padding.top, 0.0)
        assert_eq(node.clip_content, False)

    @test("UNNode: default appearance")
    def _():
        node = UNNode(type=NodeType.FRAME)
        assert_eq(node.opacity, 1.0)
        assert_eq(node.blend_mode, BlendMode.NORMAL)
        assert_eq(node.visible, True)

    @test("UNNode: default empty lists")
    def _():
        node = UNNode(type=NodeType.FRAME)
        assert_eq(node.fills, [])
        assert_eq(node.strokes, [])
        assert_eq(node.effects, [])
        assert_eq(node.children, [])


class TestUNTextRun:
    """Test UNTextRun dataclass."""

    @test("UNTextRun: creates successfully")
    def _():
        run = UNTextRun(
            content="Hello",
            start=0,
            end=5
        )
        assert_eq(run.content, "Hello")
        assert_eq(run.start, 0)
        assert_eq(run.end, 5)

    @test("UNTextRun: start == end valid")
    def _():
        run = UNTextRun(content="", start=0, end=0)
        assert_eq(run.start, 0)
        assert_eq(run.end, 0)

    @test("UNTextRun: with style")
    def _():
        run = UNTextRun(
            content="Bold",
            start=0,
            end=4,
            font_weight="700",
            underline=True
        )
        assert_eq(run.font_weight, "700")
        assert_eq(run.underline, True)

    @test("UNTextRun: start > end raises")
    def _():
        try:
            UNTextRun(content="X", start=5, end=3)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass  # Expected


class TestUNColor:
    """Test UNColor dataclass."""

    @test("UNColor: default")
    def _():
        color = UNColor()
        assert_eq(color.r, 0.0)
        assert_eq(color.g, 0.0)
        assert_eq(color.b, 0.0)
        assert_eq(color.a, 1.0)

    @test("UNColor: from_hex #RGB")
    def _():
        color = UNColor.from_hex("#f00")
        assert_eq(color.r, 1.0)
        assert_eq(color.g, 0.0)
        assert_eq(color.b, 0.0)

    @test("UNColor: from_hex #RRGGBB")
    def _():
        color = UNColor.from_hex("#ff0000")
        assert_eq(color.r, 1.0)
        assert_eq(color.g, 0.0)
        assert_eq(color.b, 0.0)

    @test("UNColor: from_hex #RRGGBBAA")
    def _():
        color = UNColor.from_hex("#ff000080")
        assert_eq(color.r, 1.0)
        assert_eq(color.g, 0.0)
        assert_eq(color.b, 0.0)
        assert_true(abs(color.a - 0.5) < 0.01)


class TestSerialisation:
    """Test un_node_to_dict and un_node_from_dict."""

    @test("Serialisation: simple roundtrip")
    def _():
        original = UNNode(type=NodeType.FRAME, name="TestFrame", x=10, y=20)
        data = un_node_to_dict(original)
        restored = un_node_from_dict(data)
        assert_eq(restored.type, NodeType.FRAME)
        assert_eq(restored.name, "TestFrame")
        assert_eq(restored.x, 10)
        assert_eq(restored.y, 20)

    @test("Serialisation: with children")
    def _():
        child = UNNode(type=NodeType.TEXT, name="Child")
        parent = UNNode(type=NodeType.FRAME, name="Parent", children=[child])
        data = un_node_to_dict(parent)
        restored = un_node_from_dict(data)
        assert_eq(len(restored.children), 1)
        assert_eq(restored.children[0].name, "Child")
        assert_eq(restored.children[0].type, NodeType.TEXT)

    @test("Serialisation: with fills")
    def _():
        fill = UNSolidFill(color=UNColor(r=1.0, g=0.5, b=0.3, a=1.0))
        node = UNNode(type=NodeType.FRAME, fills=[fill])
        data = un_node_to_dict(node)
        restored = un_node_from_dict(data)
        assert_eq(len(restored.fills), 1)
        assert_eq(restored.fills[0].color.r, 1.0)

    @test("Serialisation: with text_runs")
    def _():
        run = UNTextRun(content="Bold", start=0, end=4, font_weight="700")
        node = UNNode(
            type=NodeType.TEXT,
            text_content="Bold text",
            text_runs=[run]
        )
        data = un_node_to_dict(node)
        restored = un_node_from_dict(data)
        assert_eq(len(restored.text_runs), 1)
        assert_eq(restored.text_runs[0].content, "Bold")
        assert_eq(restored.text_runs[0].font_weight, "700")


class TestFactoryFunctions:
    """Test factory helper functions."""

    @test("make_frame: basic")
    def _():
        node = make_frame("TestFrame", 200, 100)
        assert_eq(node.type, NodeType.FRAME)
        assert_eq(node.name, "TestFrame")
        assert_eq(node.width.value, 200)
        assert_eq(node.height.value, 100)

    @test("make_frame: with fill_color")
    def _():
        node = make_frame("RedFrame", 100, 100, fill_color="#ff0000")
        assert_eq(len(node.fills), 1)
        assert_eq(node.fills[0].color.r, 1.0)

    @test("make_frame: with layout")
    def _():
        node = make_frame(
            "FlexFrame", 200, 100,
            layout=LayoutMode.HORIZONTAL,
            gap=16
        )
        assert_eq(node.layout, LayoutMode.HORIZONTAL)
        assert_eq(node.gap, 16)

    @test("make_text: basic")
    def _():
        node = make_text("Label", "Hello World", font_size=14)
        assert_eq(node.type, NodeType.TEXT)
        assert_eq(node.name, "Label")
        assert_eq(node.text_content, "Hello World")

    @test("make_rect: basic")
    def _():
        node = make_rect("Box", 10, 20, 100, 50)
        assert_eq(node.type, NodeType.RECTANGLE)
        assert_eq(node.name, "Box")
        assert_eq(node.x, 10)
        assert_eq(node.y, 20)
        assert_eq(node.width.value, 100)
        assert_eq(node.height.value, 50)

    @test("make_ellipse: basic")
    def _():
        node = make_ellipse("Circle", 0, 0, 50, 50)
        assert_eq(node.type, NodeType.ELLIPSE)
        assert_eq(node.width.value, 50)
        assert_eq(node.height.value, 50)

    @test("make_solid_fill: basic")
    def _():
        fill = make_solid_fill("#ff0000ff")
        assert_eq(fill.color.r, 1.0)
        assert_eq(fill.color.g, 0.0)
        assert_eq(fill.color.b, 0.0)
        assert_eq(fill.color.a, 1.0)

    @test("make_shadow: basic")
    def _():
        shadow = make_shadow("#00000080", offset_x=0, offset_y=4, blur=8)
        assert_true(abs(shadow.color.a - 0.5) < 0.01)
        assert_eq(shadow.offset_y, 4)
        assert_eq(shadow.blur, 8)


class TestEnums:
    """Test enum values."""

    @test("NodeType values")
    def _():
        assert_eq(NodeType.FRAME.value, "frame")
        assert_eq(NodeType.TEXT.value, "text")
        assert_eq(NodeType.RECTANGLE.value, "rectangle")

    @test("LayoutMode values")
    def _():
        assert_eq(LayoutMode.NONE.value, "none")
        assert_eq(LayoutMode.HORIZONTAL.value, "horizontal")
        assert_eq(LayoutMode.VERTICAL.value, "vertical")

    @test("BlendMode values")
    def _():
        assert_eq(BlendMode.NORMAL.value, "normal")
        assert_eq(BlendMode.MULTIPLY.value, "multiply")
        assert_eq(BlendMode.DODGE.value, "color_dodge")


# Run all tests
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
