"""
Unit tests for IR nodes (ir/nodes.py).

Tests cover:
- UNColor parsing and conversion
- Enum values and serialization
- UNNode dataclass defaults and validation
- UNTextRun validation
- Factory functions (make_frame, make_text, make_rect, etc.)
- Serialization roundtrip (un_node_to_dict / un_node_from_dict)
"""

import pytest
from design_converter.ir import (
    # Enums
    NodeType,
    LayoutMode,
    JustifyContent,
    AlignItems,
    SizingMode,
    TextAlign,
    TextTransform,
    TextAutoResize,
    GradientType,
    StrokeAlign,
    BlendMode,
    ImageFillMode,
    # Color
    UNColor,
    # Fills
    UNSolidFill,
    UNGradientFill,
    UNGradientStop,
    UNImageFill,
    # Strokes
    UNStroke,
    UNStrokeThickness,
    # Effects
    UNDropShadow,
    UNBlur,
    # Geometry
    UNPadding,
    UNCornerRadius,
    UNSize,
    # Typography
    UNTextStyle,
    UNTextRun,
    # Tokens
    UNVariableBinding,
    # Core
    UNNode,
    # Factories
    make_frame,
    make_text,
    make_rect,
    make_ellipse,
    make_path,
    make_gradient_fill,
    make_solid_fill,
    make_shadow,
    # Serialization
    un_node_to_dict,
    un_node_from_dict,
)


class TestUNColor:
    """Tests for UNColor parsing and conversion."""

    def test_from_hex_6char(self):
        """Parse 6-character hex color."""
        c = UNColor.from_hex("#FF0000")
        assert c.r == 1.0
        assert c.g == 0.0
        assert c.b == 0.0
        assert c.a == 1.0

    def test_from_hex_3char(self):
        """Parse 3-character shorthand hex color."""
        c = UNColor.from_hex("#F00")
        assert c.r == 1.0
        assert c.g == 0.0
        assert c.b == 0.0

    def test_from_hex_8char_with_alpha(self):
        """Parse 8-character hex with alpha."""
        c = UNColor.from_hex("#FF000080")
        assert c.r == 1.0
        assert c.g == 0.0
        assert c.b == 0.0
        assert c.a == pytest.approx(0.502, rel=0.01)  # 128/255

    def test_from_hex_invalid(self):
        """Invalid hex raises ValueError."""
        with pytest.raises(ValueError):
            UNColor.from_hex("#GGGGGG")

    def test_to_hex_no_alpha(self):
        """Convert to hex without alpha."""
        c = UNColor(1.0, 0.5, 0.0, 1.0)
        assert c.to_hex(include_alpha=False) == "#FF8000"

    def test_to_hex_with_alpha(self):
        """Convert to hex with alpha when < 255."""
        c = UNColor(1.0, 0.5, 0.0, 0.5)
        assert c.to_hex(include_alpha=True) == "#FF800080"

    def test_to_figma_rgb(self):
        """Convert to Figma-style dict."""
        c = UNColor(0.06, 0.37, 0.25)
        d = c.to_figma_rgb()
        assert d["r"] == 0.06
        assert d["g"] == 0.37
        assert d["b"] == 0.25
        assert "a" not in d

    def test_to_css_rgba(self):
        """Convert to CSS rgba string."""
        c = UNColor(1.0, 0.0, 0.0, 0.5)
        assert c.to_css_rgba() == "rgba(255,0,0,0.5)"


class TestEnums:
    """Tests for enum values."""

    def test_node_type_values(self):
        """NodeType enum has expected values."""
        assert NodeType.FRAME.value == "frame"
        assert NodeType.TEXT.value == "text"
        assert NodeType.RECTANGLE.value == "rectangle"
        assert NodeType.ELLIPSE.value == "ellipse"
        assert NodeType.PATH.value == "path"
        assert NodeType.GROUP.value == "group"
        assert NodeType.IMAGE.value == "image"

    def test_layout_mode_values(self):
        """LayoutMode enum has expected values."""
        assert LayoutMode.NONE.value == "none"
        assert LayoutMode.HORIZONTAL.value == "horizontal"
        assert LayoutMode.VERTICAL.value == "vertical"

    def test_blend_mode_dodge_burn(self):
        """BlendMode uses COLOR_DODGE/COLOR_BURN (not DODGE/BURN)."""
        assert BlendMode.DODGE.value == "color_dodge"
        assert BlendMode.BURN.value == "color_burn"

    def test_text_auto_resize_values(self):
        """TextAutoResize enum has expected values."""
        assert TextAutoResize.NONE.value == "none"
        assert TextAutoResize.WIDTH_HEIGHT.value == "width_height"
        assert TextAutoResize.HEIGHT.value == "height"


class TestUNTextRun:
    """Tests for UNTextRun validation."""

    def test_valid_run(self):
        """Valid text run creates successfully."""
        run = UNTextRun(content="Hello", start=0, end=5)
        assert run.content == "Hello"
        assert run.start == 0
        assert run.end == 5

    def test_start_greater_than_end_raises(self):
        """start > end raises ValueError."""
        with pytest.raises(ValueError, match="must be <="):
            UNTextRun(content="Test", start=5, end=2)

    def test_negative_start_raises(self):
        """Negative start raises ValueError."""
        with pytest.raises(ValueError, match="must be >= 0"):
            UNTextRun(content="Test", start=-1, end=4)

    def test_equal_start_end_is_valid(self):
        """Empty run (start == end) is valid."""
        run = UNTextRun(content="", start=5, end=5)
        assert run.start == run.end == 5


class TestUNPadding:
    """Tests for UNPadding helpers."""

    def test_all_factory(self):
        """UNPadding.all() sets all sides equal."""
        p = UNPadding.all(16)
        assert p.top == p.right == p.bottom == p.left == 16

    def test_xy_factory(self):
        """UNPadding.xy() sets horizontal/vertical pairs."""
        p = UNPadding.xy(20, 10)
        assert p.top == 10
        assert p.bottom == 10
        assert p.left == 20
        assert p.right == 20

    def test_to_list(self):
        """to_list returns [top, right, bottom, left]."""
        p = UNPadding(1, 2, 3, 4)
        assert p.to_list() == [1, 2, 3, 4]

    def test_is_zero(self):
        """is_zero returns True only when all are 0."""
        assert UNPadding(0, 0, 0, 0).is_zero()
        assert not UNPadding(1, 0, 0, 0).is_zero()


class TestUNCornerRadius:
    """Tests for UNCornerRadius helpers."""

    def test_all_factory(self):
        """UNCornerRadius.all() sets all corners equal."""
        r = UNCornerRadius.all(8)
        assert r.tl == r.tr == r.br == r.bl == 8

    def test_is_uniform(self):
        """is_uniform returns True when all corners equal."""
        assert UNCornerRadius.all(8).is_uniform()
        assert not UNCornerRadius(8, 8, 4, 8).is_uniform()

    def test_value_raises_if_not_uniform(self):
        """value() raises ValueError if corners differ."""
        r = UNCornerRadius(8, 4, 8, 4)
        with pytest.raises(ValueError, match="not uniform"):
            r.value()


class TestUNSize:
    """Tests for UNSize helpers."""

    def test_fixed_factory(self):
        """UNSize.fixed() creates FIXED mode."""
        s = UNSize.fixed(100)
        assert s.value == 100
        assert s.mode == SizingMode.FIXED

    def test_hug_factory(self):
        """UNSize.hug() creates HUG mode."""
        s = UNSize.hug()
        assert s.mode == SizingMode.HUG

    def test_fill_factory(self):
        """UNSize.fill() creates FILL mode."""
        s = UNSize.fill()
        assert s.mode == SizingMode.FILL


class TestUNStrokeThickness:
    """Tests for UNStrokeThickness helpers."""

    def test_uniform_factory(self):
        """uniform() sets .all field."""
        t = UNStrokeThickness.uniform(2.0)
        assert t.all == 2.0
        assert t.top is None

    def test_max_value(self):
        """max_value returns largest non-None value."""
        t = UNStrokeThickness(top=1, right=3, bottom=2, left=None, all=None)
        assert t.max_value() == 3

    def test_max_value_defaults_to_1(self):
        """max_value returns 1.0 if all None."""
        t = UNStrokeThickness()
        assert t.max_value() == 1.0


class TestFactoryFunctions:
    """Tests for factory helper functions."""

    def test_make_frame(self):
        """make_frame creates valid FRAME node."""
        node = make_frame("Card", 200, 150, fill_color="#FFFFFF")
        assert node.type == NodeType.FRAME
        assert node.name == "Card"
        assert node.width.value == 200
        assert node.height.value == 150
        assert len(node.fills) == 1
        assert isinstance(node.fills[0], UNSolidFill)

    def test_make_frame_with_layout(self):
        """make_frame supports layout options."""
        node = make_frame(
            "Row",
            300,
            50,
            layout=LayoutMode.HORIZONTAL,
            gap=8,
            padding=UNPadding.all(16),
        )
        assert node.layout == LayoutMode.HORIZONTAL
        assert node.gap == 8
        assert node.padding.top == 16

    def test_make_text(self):
        """make_text creates valid TEXT node."""
        node = make_text("Label", "Hello World", font_size=16, color="#333333")
        assert node.type == NodeType.TEXT
        assert node.text_content == "Hello World"
        assert node.text_style.font_size == 16
        assert len(node.fills) == 1

    def test_make_text_hug_by_default(self):
        """make_text uses HUG sizing by default."""
        node = make_text("Label", "Test")
        assert node.width.mode == SizingMode.HUG
        assert node.height.mode == SizingMode.HUG

    def test_make_text_fixed_width(self):
        """make_text with width uses HEIGHT auto-resize."""
        node = make_text("Label", "Test", width=200)
        assert node.width.mode == SizingMode.FIXED
        assert node.width.value == 200
        assert node.text_style.text_auto_resize == TextAutoResize.HEIGHT

    def test_make_rect(self):
        """make_rect creates valid RECTANGLE node."""
        node = make_rect("Box", 10, 20, 100, 50, fill_color="#FF0000")
        assert node.type == NodeType.RECTANGLE
        assert node.x == 10
        assert node.y == 20
        assert node.width.value == 100
        assert node.height.value == 50
        assert len(node.fills) == 1

    def test_make_rect_with_corner_radius(self):
        """make_rect supports corner radius."""
        node = make_rect("Rounded", 0, 0, 50, 50, corner_radius=8)
        assert node.corner_radius.tl == 8

    def test_make_ellipse(self):
        """make_ellipse creates valid ELLIPSE node."""
        node = make_ellipse("Circle", 0, 0, 100, 100, fill_color="#00FF00")
        assert node.type == NodeType.ELLIPSE
        assert node.width.value == 100
        assert node.height.value == 100

    def test_make_path(self):
        """make_path creates valid PATH node."""
        node = make_path(
            "Arrow",
            24,
            24,
            "M12 2L12 22M12 2L6 8M12 2L18 8",
            stroke_color="#000000",
            stroke_width=2,
        )
        assert node.type == NodeType.PATH
        assert node.geometry == "M12 2L12 22M12 2L6 8M12 2L18 8"
        assert len(node.strokes) == 1

    def test_make_gradient_fill(self):
        """make_gradient_fill creates UNGradientFill."""
        fill = make_gradient_fill(
            gradient_type=GradientType.LINEAR,
            rotation=90,
            stops=[
                UNGradientStop(UNColor.from_hex("#FF0000"), 0.0),
                UNGradientStop(UNColor.from_hex("#0000FF"), 1.0),
            ],
        )
        assert fill.gradient_type == GradientType.LINEAR
        assert fill.rotation == 90
        assert len(fill.stops) == 2

    def test_make_solid_fill(self):
        """make_solid_fill creates UNSolidFill from hex with alpha in color."""
        fill = make_solid_fill("#FF0000", opacity=0.5)
        assert isinstance(fill, UNSolidFill)
        assert fill.color.r == 1.0
        # Note: make_solid_fill sets alpha on the color, not on fill.opacity
        assert fill.color.a == 0.5

    def test_make_shadow(self):
        """make_shadow creates UNDropShadow."""
        shadow = make_shadow(
            color="#00000040",
            offset_x=0,
            offset_y=4,
            blur=8,
            spread=0,
        )
        assert shadow.type == "drop_shadow"
        assert shadow.offset_y == 4
        assert shadow.blur == 8


class TestUNNodeHelpers:
    """Tests for UNNode helper methods."""

    def test_add_child(self):
        """add_child appends to children and returns child."""
        parent = UNNode(type=NodeType.FRAME, name="Parent")
        child = UNNode(type=NodeType.TEXT, name="Child")
        result = parent.add_child(child)
        assert result is child
        assert len(parent.children) == 1

    def test_add_fill(self):
        """add_fill appends fill and returns self."""
        node = UNNode(type=NodeType.FRAME, name="Test")
        fill = UNSolidFill(color=UNColor.from_hex("#FF0000"))
        result = node.add_fill(fill)
        assert result is node
        assert len(node.fills) == 1

    def test_primary_fill_color(self):
        """primary_fill_color returns first enabled solid fill."""
        node = UNNode(type=NodeType.FRAME, name="Test")
        node.fills.append(UNSolidFill(color=UNColor.from_hex("#FF0000"), enabled=False))
        node.fills.append(UNSolidFill(color=UNColor.from_hex("#00FF00"), enabled=True))
        color = node.primary_fill_color()
        assert color is not None
        assert color.g == 1.0

    def test_primary_fill_color_returns_none_if_no_solid(self):
        """primary_fill_color returns None if no enabled solid fill."""
        node = UNNode(type=NodeType.FRAME, name="Test")
        node.fills.append(UNImageFill(url="http://example.com/img.png"))
        assert node.primary_fill_color() is None

    def test_is_container(self):
        """is_container returns True for FRAME, GROUP, COMPONENT, INSTANCE."""
        assert UNNode(type=NodeType.FRAME).is_container()
        assert UNNode(type=NodeType.GROUP).is_container()
        assert UNNode(type=NodeType.COMPONENT).is_container()
        assert UNNode(type=NodeType.INSTANCE).is_container()
        assert not UNNode(type=NodeType.TEXT).is_container()
        assert not UNNode(type=NodeType.RECTANGLE).is_container()

    def test_walk(self):
        """walk yields self and all descendants depth-first."""
        root = UNNode(type=NodeType.FRAME, name="Root")
        child1 = UNNode(type=NodeType.FRAME, name="Child1")
        child2 = UNNode(type=NodeType.TEXT, name="Child2")
        grandchild = UNNode(type=NodeType.TEXT, name="Grandchild")
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        names = [n.name for n in root.walk()]
        assert names == ["Root", "Child1", "Grandchild", "Child2"]

    def test_find_by_name(self):
        """find_by_name returns first matching node."""
        root = UNNode(type=NodeType.FRAME, name="Root")
        child = UNNode(type=NodeType.TEXT, name="Target")
        root.add_child(child)

        result = root.find_by_name("Target")
        assert result is child

    def test_find_by_id(self):
        """find_by_id returns first matching node."""
        root = UNNode(type=NodeType.FRAME, id="r1", name="Root")
        child = UNNode(type=NodeType.TEXT, id="t1", name="Target")
        root.add_child(child)

        result = root.find_by_id("t1")
        assert result is child


class TestSerialization:
    """Tests for un_node_to_dict / un_node_from_dict."""

    def test_frame_roundtrip(self):
        """FRAME node serializes and deserializes correctly."""
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
        assert len(restored.fills) == 1

    def test_text_roundtrip(self):
        """TEXT node serializes and deserializes correctly."""
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

    def test_text_runs_roundtrip(self):
        """TEXT node with runs serializes and deserializes correctly."""
        node = UNNode(
            type=NodeType.TEXT,
            id="test-runs",
            name="RichText",
            text_content="Hello World",
        )
        node.text_runs.append(
            UNTextRun(
                content="Hello",
                start=0,
                end=5,
                fill=UNColor.from_hex("#FF0000"),
                font_size=16,
            )
        )

        d = un_node_to_dict(node)
        restored = un_node_from_dict(d)

        assert len(restored.text_runs) == 1
        run = restored.text_runs[0]
        assert run.content == "Hello"
        assert run.start == 0
        assert run.end == 5
        assert run.fill is not None
        assert run.fill.r == 1.0
        assert run.font_size == 16

    def test_children_roundtrip(self):
        """Node tree with children serializes correctly."""
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

    def test_effects_roundtrip(self):
        """Node with effects serializes correctly."""
        node = make_frame("Card", 200, 150)
        node.effects.append(
            UNDropShadow(
                color=UNColor.from_hex("#00000040"),
                offset_x=0,
                offset_y=4,
                blur=8,
                spread=0,
            )
        )
        node.effects.append(UNBlur(radius=10, background=True))

        d = un_node_to_dict(node)
        restored = un_node_from_dict(d)

        assert len(restored.effects) == 2
        assert isinstance(restored.effects[0], UNDropShadow)
        assert restored.effects[0].blur == 8
        assert isinstance(restored.effects[1], UNBlur)
        assert restored.effects[1].background is True

    def test_gradient_fill_roundtrip(self):
        """Node with gradient fill serializes correctly."""
        node = UNNode(type=NodeType.FRAME, name="Gradient")
        node.fills.append(
            UNGradientFill(
                gradient_type=GradientType.LINEAR,
                rotation=45,
                stops=[
                    UNGradientStop(UNColor.from_hex("#FF0000"), 0.0),
                    UNGradientStop(UNColor.from_hex("#0000FF"), 1.0),
                ],
            )
        )

        d = un_node_to_dict(node)
        restored = un_node_from_dict(d)

        assert len(restored.fills) == 1
        fill = restored.fills[0]
        assert isinstance(fill, UNGradientFill)
        assert fill.rotation == 45
        assert len(fill.stops) == 2
        assert fill.stops[0].color.r == 1.0
        assert fill.stops[1].color.b == 1.0


class TestUNVariableBinding:
    """Tests for UNVariableBinding dataclass."""

    def test_binding_fields(self):
        """UNVariableBinding has correct fields."""
        b = UNVariableBinding(
            property="fill.0.color",
            variable="$--primary",
            tool_id="figma:var-123",
        )
        assert b.property == "fill.0.color"
        assert b.variable == "$--primary"
        assert b.tool_id == "figma:var-123"

    def test_binding_tool_id_optional(self):
        """tool_id is optional."""
        b = UNVariableBinding(property="fontSize", variable="typography/body")
        assert b.tool_id is None


class TestUNTextStyle:
    """Tests for UNTextStyle methods."""

    def test_figma_font_name_regular(self):
        """figma_font_name maps weight to Figma style name."""
        ts = UNTextStyle(font_family="Inter", font_weight="400", font_style="normal")
        fn = ts.figma_font_name()
        assert fn["family"] == "Inter"
        assert fn["style"] == "Regular"

    def test_figma_font_name_semibold_italic(self):
        """figma_font_name handles italic style."""
        ts = UNTextStyle(font_family="Inter", font_weight="600", font_style="italic")
        fn = ts.figma_font_name()
        assert fn["style"] == "SemiBold Italic"

    def test_to_css(self):
        """to_css returns CSS properties dict."""
        ts = UNTextStyle(
            font_family="Roboto",
            font_size=16,
            font_weight="500",
            line_height=24,
            letter_spacing=0.5,
            text_align=TextAlign.CENTER,
        )
        css = ts.to_css()
        assert css["font-family"] == "Roboto"
        assert css["font-size"] == "16px"
        assert css["font-weight"] == "500"
        assert css["line-height"] == "24px"
        assert css["letter-spacing"] == "0.5px"
        assert css["text-align"] == "center"
