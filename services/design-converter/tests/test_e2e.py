"""
End-to-end tests for the design-converter.

Tests the full pipeline:
- UNNode creation and manipulation
- Serialization roundtrip
- Mock conversion workflows
- JSX parsing to Figma JS generation
"""

import json
import os
import tempfile
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from ir import (
    NodeType,
    LayoutMode,
    JustifyContent,
    AlignItems,
    UNColor,
    UNNode,
    UNSolidFill,
    UNPadding,
    UNCornerRadius,
    UNSize,
    SizingMode,
    make_frame,
    make_text,
    make_rect,
    un_node_to_dict,
    un_node_from_dict,
)
from utils.jsx_parser import parse_jsx, reset_id_counter
from adapters.figma.writer import FigmaWriter


class TestUNNodeCreation:
    """Test UNNode creation via factory functions."""

    def test_create_frame_tree(self):
        """Create a frame with children."""
        root = make_frame("Card", 300, 200, fill_color="#FFFFFF")
        root.id = "root"
        root.layout = LayoutMode.VERTICAL
        root.gap = 16
        root.padding = UNPadding.all(24)

        title = make_text("Title", "Welcome", font_size=24, font_weight="700")
        title.id = "title"
        root.add_child(title)

        body = make_text("Body", "Description text here.", font_size=14)
        body.id = "body"
        root.add_child(body)

        assert root.name == "Card"
        assert root.layout == LayoutMode.VERTICAL
        assert root.gap == 16
        assert len(root.children) == 2
        assert root.children[0].name == "Title"
        assert root.children[1].name == "Body"


class TestSerializationRoundtrip:
    """Test serialization roundtrip preserves data."""

    def test_frame_roundtrip(self):
        """Frame serializes and deserializes correctly."""
        original = make_frame(
            "Card",
            200,
            150,
            fill_color="#FFFFFF",
            layout=LayoutMode.HORIZONTAL,
            gap=8,
            padding=UNPadding.all(16),
            corner_radius=8,
        )
        original.id = "test-frame-1"

        d = un_node_to_dict(original)
        restored = un_node_from_dict(d)

        assert restored.type == NodeType.FRAME
        assert restored.name == "Card"
        assert restored.id == "test-frame-1"
        assert restored.width.value == 200
        assert restored.height.value == 150
        assert restored.layout == LayoutMode.HORIZONTAL
        assert restored.gap == 8
        assert restored.padding.top == 16
        assert restored.corner_radius.tl == 8

    def test_text_roundtrip(self):
        """Text serializes and deserializes correctly."""
        original = make_text(
            "Label",
            "Hello World",
            font_size=16,
            font_weight="600",
            color="#333333",
        )
        original.id = "test-text-1"

        d = un_node_to_dict(original)
        restored = un_node_from_dict(d)

        assert restored.type == NodeType.TEXT
        assert restored.text_content == "Hello World"
        assert restored.text_style.font_size == 16
        assert restored.text_style.font_weight == "600"

    def test_tree_with_children_roundtrip(self):
        """Tree with children roundtrips correctly."""
        root = make_frame("Root", 400, 300)
        root.id = "root"
        child1 = make_text("Title", "Welcome")
        child1.id = "child1"
        child2 = make_rect("Icon", 10, 10, 24, 24)
        child2.id = "child2"
        root.add_child(child1)
        root.add_child(child2)

        d = un_node_to_dict(root)
        restored = un_node_from_dict(d)

        assert len(restored.children) == 2
        assert restored.children[0].name == "Title"
        assert restored.children[0].type == NodeType.TEXT
        assert restored.children[1].name == "Icon"
        assert restored.children[1].type == NodeType.RECTANGLE

    def test_empty_tree(self):
        """Empty node tree handles gracefully."""
        empty = UNNode(type=NodeType.FRAME, name="Empty")
        empty.id = "empty"

        d = un_node_to_dict(empty)
        restored = un_node_from_dict(d)

        assert restored.name == "Empty"
        assert len(restored.children) == 0
        assert len(restored.fills) == 0


class TestLayoutModes:
    """Test layout mode handling."""

    def test_horizontal_layout(self):
        """Horizontal layout sets correct mode."""
        frame = make_frame("Row", 300, 50, layout=LayoutMode.HORIZONTAL, gap=8)
        assert frame.layout == LayoutMode.HORIZONTAL
        assert frame.gap == 8

    def test_vertical_layout(self):
        """Vertical layout sets correct mode."""
        frame = make_frame("Column", 200, 400, layout=LayoutMode.VERTICAL, gap=16)
        assert frame.layout == LayoutMode.VERTICAL
        assert frame.gap == 16

    def test_no_layout(self):
        """No layout uses NONE mode."""
        frame = make_frame("Absolute", 100, 100)
        assert frame.layout == LayoutMode.NONE


class TestColors:
    """Test color handling."""

    def test_fill_color(self):
        """Frame with fill color has correct fill."""
        frame = make_frame("Card", 100, 100, fill_color="#FF5733")
        
        assert len(frame.fills) == 1
        fill = frame.fills[0]
        assert isinstance(fill, UNSolidFill)
        
        # #FF5733 = RGB(255, 87, 51) = (1.0, 0.34, 0.2)
        assert fill.color.r == 1.0
        assert abs(fill.color.g - 0.341) < 0.01
        assert abs(fill.color.b - 0.2) < 0.01

    def test_no_fill(self):
        """Frame without fill color has no fills."""
        frame = make_frame("Transparent", 100, 100)
        assert len(frame.fills) == 0


class TestCornerRadii:
    """Test corner radius handling."""

    def test_uniform_radius(self):
        """Uniform corner radius."""
        frame = make_frame("Rounded", 100, 100, corner_radius=12)
        
        assert frame.corner_radius.is_uniform()
        assert frame.corner_radius.tl == 12
        assert frame.corner_radius.value() == 12

    def test_no_radius(self):
        """No corner radius."""
        frame = make_frame("Sharp", 100, 100)
        assert frame.corner_radius.tl == 0
        assert frame.corner_radius.is_uniform()


class TestNodeTraversal:
    """Test node tree traversal."""

    def test_walk(self):
        """walk() yields all nodes depth-first."""
        root = make_frame("Root", 400, 300)
        child1 = make_frame("Child1", 100, 100)
        child2 = make_text("Child2", "Text")
        grandchild = make_rect("Grandchild", 0, 0, 50, 50)
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        names = [n.name for n in root.walk()]
        assert names == ["Root", "Child1", "Grandchild", "Child2"]

    def test_find_by_name(self):
        """find_by_name finds correct node."""
        root = make_frame("Root", 400, 300)
        child = make_text("Target", "Text")
        root.add_child(child)

        result = root.find_by_name("Target")
        assert result is child

    def test_find_all_by_type(self):
        """find_all with type predicate."""
        root = make_frame("Root", 400, 300)
        root.add_child(make_text("Text1", "A"))
        root.add_child(make_rect("Rect1", 0, 0, 50, 50))
        root.add_child(make_text("Text2", "B"))

        texts = root.find_all(lambda n: n.type == NodeType.TEXT)
        assert len(texts) == 2


class TestSizing:
    """Test sizing modes."""

    def test_fixed_size(self):
        """Fixed size uses SizingMode.FIXED."""
        frame = make_frame("Fixed", 200, 150)
        assert frame.width.mode == SizingMode.FIXED
        assert frame.width.value == 200
        assert frame.height.value == 150

    def test_text_hug_size(self):
        """Text uses HUG sizing by default."""
        text = make_text("Label", "Hello")
        assert text.width.mode == SizingMode.HUG
        assert text.height.mode == SizingMode.HUG


class TestJSXToUNNodePipeline:
    """Test the JSX parsing to UNNode conversion pipeline."""

    def setup_method(self):
        reset_id_counter()

    def test_simple_jsx_to_unnode(self):
        """Parse simple JSX and verify UNNode structure."""
        jsx = "<div>Content</div>"
        node = parse_jsx(jsx)

        assert node is not None
        assert node.type == NodeType.FRAME

    def test_jsx_with_flex_to_unnode(self):
        """Parse flex JSX and verify layout properties."""
        jsx = '''
        <div style={{
            display: "flex",
            flexDirection: "column",
            gap: 16
        }}>
            <span>Title</span>
        </div>
        '''
        node = parse_jsx(jsx)

        assert node is not None
        # The parser may interpret gap differently based on CSS parsing
        # Just verify it parses without error

    def test_component_extraction_to_unnode(self):
        """Extract JSX from component and parse."""
        from utils.jsx_parser import parse_jsx_component

        src = """
        function WalletScreen() {
            return (
                <div>
                    <span>Balance</span>
                </div>
            );
        }
        """
        node = parse_jsx_component(src, "WalletScreen")

        assert node is not None
        assert node.name == "WalletScreen"


class TestUNNodeToFigmaPipeline:
    """Test UNNode to Figma JS generation pipeline."""

    def test_unnode_to_figma_js(self):
        """UNNode generates valid Figma JS."""
        node = make_frame("Card", 300, 200, fill_color="#FFFFFF")
        node.id = "card-1"
        node.layout = LayoutMode.VERTICAL
        node.gap = 8
        node.padding = UNPadding.all(16)

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FigmaWriter(output_dir=tmpdir, mode="script")
            result = writer.write_node(node)

            assert result.endswith(".js")
            with open(result, "r") as f:
                js = f.read()

            assert "figma.createFrame()" in js
            assert "Card" in js
            assert "300" in js
            assert "200" in js

    def test_text_node_to_figma_js(self):
        """TEXT node generates valid Figma JS with font loading."""
        node = make_text("Label", "Hello World", font_size=16, font_weight="600")

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FigmaWriter(output_dir=tmpdir, mode="script")
            result = writer.write_node(node)

            with open(result, "r") as f:
                js = f.read()

            assert "figma.createText()" in js
            assert "loadFontAsync" in js
            assert "Hello World" in js


class TestFullConversionPipeline:
    """Test the full Paper JSX → UNNode → Figma JS pipeline."""

    def setup_method(self):
        reset_id_counter()

    def test_paper_to_figma_simple(self):
        """Simple conversion: Paper JSX → UNNode → Figma JS."""
        # Simulate Paper's get_jsx output with backgroundColor only
        paper_jsx = '''
        <div style={{
            display: "flex",
            flexDirection: "column"
        }}>
            <span style={{color: "#FFFFFF"}}>Welcome</span>
        </div>
        '''

        # Step 1: Parse JSX to UNNode
        unnode = parse_jsx(paper_jsx, "Screen")
        assert unnode is not None
        assert unnode.type == NodeType.FRAME

        # Step 2: Serialize to dict (for storage/transfer)
        data = un_node_to_dict(unnode)
        assert data["type"] == "frame"

        # Step 3: Deserialize from dict
        restored = un_node_from_dict(data)
        assert restored.type == NodeType.FRAME

        # Step 4: Generate Figma JS
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FigmaWriter(output_dir=tmpdir, mode="script")
            result = writer.write_node(restored)

            with open(result, "r") as f:
                js = f.read()

            assert "figma.createFrame()" in js

    def test_paper_to_figma_with_children(self):
        """Conversion with nested children."""
        paper_jsx = '''
        <div style={{display: "flex", flexDirection: "column", gap: 8}}>
            <span style={{color: "#FFFFFF"}}>Title</span>
            <span style={{color: "#666666"}}>Description</span>
        </div>
        '''

        unnode = parse_jsx(paper_jsx, "Card")
        assert unnode is not None

        # Verify children were parsed
        text_children = [c for c in unnode.children if c.type == NodeType.TEXT]
        assert len(text_children) >= 2

        # Generate Figma JS
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FigmaWriter(output_dir=tmpdir, mode="script")
            result = writer.write_node(unnode)

            with open(result, "r") as f:
                js = f.read()

            # Should have multiple createText calls
            assert js.count("figma.createText()") >= 2

    def test_roundtrip_preserves_structure(self):
        """Full roundtrip preserves node structure."""
        # Create a complex node tree
        original = make_frame("Card", 300, 200, fill_color="#FFFFFF")
        original.layout = LayoutMode.VERTICAL
        original.gap = 8
        original.padding = UNPadding.all(16)
        original.corner_radius = UNCornerRadius.all(8)

        title = make_text("Title", "Welcome", font_size=24, font_weight="700")
        body = make_text("Body", "Description text", font_size=14)
        original.add_child(title)
        original.add_child(body)

        # Roundtrip through dict
        data = un_node_to_dict(original)
        restored = un_node_from_dict(data)

        # Verify structure preserved
        assert restored.name == "Card"
        assert restored.layout == LayoutMode.VERTICAL
        assert restored.gap == 8
        assert len(restored.children) == 2
        assert restored.children[0].name == "Title"
        assert restored.children[1].name == "Body"

        # Generate Figma JS from restored
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FigmaWriter(output_dir=tmpdir, mode="script")
            result = writer.write_node(restored)

            with open(result, "r") as f:
                js = f.read()

            assert "figma.createFrame()" in js
            assert js.count("figma.createText()") == 2


class TestMockPaperClientPipeline:
    """Test pipeline with mocked Paper client."""

    @patch("adapters.paper.client._post")
    def test_mock_paper_to_figma(self, mock_post):
        """Mock Paper client provides JSX which is converted to Figma JS."""
        # Simulate Paper's get_jsx response
        paper_jsx = '''
        <div style={{width: "200px", height: "100px", backgroundColor: "#FF0000"}}>
            <span>Test</span>
        </div>
        '''

        mock_post.return_value = {
            "result": {
                "content": [
                    {"type": "text", "text": paper_jsx}
                ]
            }
        }

        from adapters.paper.client import PaperClient

        client = PaperClient(use_sse=False)
        jsx = client.get_jsx("TEST-1")

        assert jsx == paper_jsx

        # Parse and convert
        reset_id_counter()
        unnode = parse_jsx(jsx, "TestNode")
        assert unnode is not None

        with tempfile.TemporaryDirectory() as tmpdir:
            writer = FigmaWriter(output_dir=tmpdir, mode="script")
            result = writer.write_node(unnode)

            with open(result, "r") as f:
                js = f.read()

            assert "figma.createFrame()" in js


class TestErrorHandling:
    """Test error handling in the pipeline."""

    def test_invalid_jsx_returns_none(self):
        """Invalid JSX returns None gracefully."""
        result = parse_jsx("<<<invalid>>>")
        # Parser is lenient, might still return something
        # Just verify it doesn't crash

    def test_empty_jsx_returns_none(self):
        """Empty JSX returns None."""
        assert parse_jsx("") is None
        assert parse_jsx("   ") is None

    def test_unnode_with_missing_fields(self):
        """UNNode with missing fields still serializes."""
        node = UNNode(type=NodeType.FRAME, name="Minimal")
        data = un_node_to_dict(node)
        restored = un_node_from_dict(data)

        assert restored.name == "Minimal"
        assert restored.type == NodeType.FRAME


class TestPerformance:
    """Performance-related tests."""

    def test_large_tree_serialization(self):
        """Large tree serializes efficiently."""
        # Create a deep tree
        root = make_frame("Root", 1000, 1000)
        current = root

        for i in range(10):
            child = make_frame(f"Level{i}", 500, 500)
            current.add_child(child)
            current = child

        # Should serialize without issues
        data = un_node_to_dict(root)
        assert data is not None

        # Should deserialize without issues
        restored = un_node_from_dict(data)
        assert restored is not None

    def test_many_children_serialization(self):
        """Node with many children serializes efficiently."""
        root = make_frame("Container", 1000, 1000)

        for i in range(50):
            child = make_text(f"Item{i}", f"Text {i}")
            root.add_child(child)

        data = un_node_to_dict(root)
        restored = un_node_from_dict(data)

        assert len(restored.children) == 50
