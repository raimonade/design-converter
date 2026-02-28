"""
End-to-end tests for design-converter pipeline.

Run: python3 tests/test_e2e.py
"""
import sys

# Add parent to path for imports
sys.path.insert(0, "/Users/william/Projects Parent Folder/DesignDev/services/design-converter")

from ir import (
    UNNode,
    NodeType,
    UNColor,
    UNSolidFill,
    UNTextRun,
    UNPadding,
    LayoutMode,
    make_frame,
    make_text,
    un_node_to_dict,
    un_node_from_dict,
)
from adapters.base import BaseReader, BaseWriter

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
# Mock Data
# ============================================

def create_mock_component_tree():
    """Create a mock component tree (like a button)."""
    # Background frame
    bg_fill = UNSolidFill(color=UNColor.from_hex("#3b82f6"))  # Blue
    bg = make_frame(
        "Button-Bg", 120, 40,
        fill_color="#3b82f6",
        corner_radius=8
    )

    # Text label
    text_run = UNTextRun(content="Click Me", start=0, end=9)
    label = UNNode(
        type=NodeType.TEXT,
        name="Label",
        text_content="Click Me",
        text_runs=[text_run]
    )

    # Button container
    button = make_frame(
        "Button", 120, 40,
        layout=LayoutMode.HORIZONTAL,
        gap=8,
        padding=UNPadding(top=10, right=16, bottom=10, left=16)
    )
    button.children = [bg, label]

    return button


# ============================================
# Tests
# ============================================

class TestMockDataCreation:
    """Test mock data creation helpers."""

    @test("Mock: create component tree")
    def _():
        tree = create_mock_component_tree()
        assert_eq(tree.name, "Button")
        assert_eq(len(tree.children), 2)

    @test("Mock: tree has fills")
    def _():
        tree = create_mock_component_tree()
        bg = tree.children[0]
        assert_true(len(bg.fills) > 0)

    @test("Mock: tree has text")
    def _():
        tree = create_mock_component_tree()
        label = tree.children[1]
        assert_eq(label.type, NodeType.TEXT)
        assert_true(len(label.text_runs) > 0)


class TestIRoundTrip:
    """Test IR serialisation round-trip."""

    @test("Roundtrip: simple frame")
    def _():
        node = make_frame("Test", 100, 100, fill_color="#ff0000")
        data = un_node_to_dict(node)
        restored = un_node_from_dict(data)
        assert_eq(restored.name, node.name)
        assert_eq(restored.width.value, node.width.value)

        assert_eq(len(restored.fills), len(node.fills))

    @test("Roundtrip: complex tree")
    def _():
        tree = create_mock_component_tree()
        data = un_node_to_dict(tree)
        restored = un_node_from_dict(data)

        # Check structure preserved
        assert_eq(restored.name, "Button")
        assert_eq(len(restored.children), 2)
        assert_eq(restored.children[0].name, "Button-Bg")
        assert_eq(restored.children[1].name, "Label")

    @test("Roundtrip: layout preserved")
    def _():
        tree = create_mock_component_tree()
        data = un_node_to_dict(tree)
        restored = un_node_from_dict(data)

        assert_eq(restored.layout, LayoutMode.HORIZONTAL)
        assert_eq(restored.gap, 8)
        assert_eq(restored.padding.top, 10)

    @test("Roundtrip: text_runs preserved")
    def _():
        tree = create_mock_component_tree()
        data = un_node_to_dict(tree)
        restored = un_node_from_dict(data)

        label = restored.children[1]
        assert_eq(len(label.text_runs), 1)
        assert_eq(label.text_runs[0].content, "Click Me")


class TestPipelineIntegrity:
    """Test pipeline data flow integrity."""

    @test("Pipeline: color values unchanged")
    def _():
        tree = create_mock_component_tree()
        data = un_node_to_dict(tree)
        restored = un_node_from_dict(data)

        # Check blue color preserved (#3b82f6)
        bg = restored.children[0]
        fill_color = bg.fills[0].color
        # Use approximate comparison for float precision
        assert_true(abs(fill_color.r - 0.23) < 0.01, f"R should be ~0.23, got {fill_color.r}")
        assert_true(abs(fill_color.g - 0.51) < 0.01, f"G should be ~0.51, got {fill_color.g}")
        assert_true(abs(fill_color.b - 0.96) < 0.01, f"B should be ~0.96, got {fill_color.b}")

    @test("Pipeline: children order preserved")
    def _():
        tree = create_mock_component_tree()
        data = un_node_to_dict(tree)
        restored = un_node_from_dict(data)

        # First child should be bg, second should be label
        assert_eq(restored.children[0].type, NodeType.FRAME)
        assert_eq(restored.children[1].type, NodeType.TEXT)

    @test("Pipeline: corner radius preserved")
    def _():
        tree = create_mock_component_tree()
        data = un_node_to_dict(tree)
        restored = un_node_from_dict(data)

        bg = restored.children[0]
        assert_eq(bg.corner_radius.tl, 8)  # top-left is 'tl'

    @test("Pipeline: can handle large trees")
    def _():
        # Create a tree with many children
        root = make_frame("Root", 800, 600)
        for i in range(20):
            child = make_frame(f"Child{i}", 100, 100)
            root.children.append(child)

        data = un_node_to_dict(root)
        restored = un_node_from_dict(data)

        assert_eq(len(restored.children), 20)


# Run all tests
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
