"""
Universal Node Tree (UNT) — Intermediate Representation
========================================================
Modeled after Figma's node architecture (the industry standard).
Every design tool maps to/from this tree — Paper, Pencil, Figma.

Philosophy:
  - Everything is a node (like Figma SceneNode)
  - Fills / strokes / effects are first-class lists
  - Layout is flex-inspired (matches auto-layout in all three tools)
  - Variables/tokens are tracked as bindings for round-trip fidelity
  - No tool-specific concepts leak into this layer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    FRAME = "frame"  # Container — Figma FRAME/GROUP, Pencil frame, Paper div
    TEXT = "text"  # Text node
    RECTANGLE = "rectangle"  # Solid rectangle
    ELLIPSE = "ellipse"  # Ellipse / circle
    PATH = "path"  # Vector path (SVG geometry)
    LINE = "line"  # Straight line
    GROUP = "group"  # Non-layout group
    IMAGE = "image"  # Raster image fill node
    COMPONENT = "component"  # Figma component definition
    INSTANCE = "instance"  # Figma component instance


class LayoutMode(str, Enum):
    NONE = "none"  # Absolute / no auto-layout
    HORIZONTAL = "horizontal"  # Flex row
    VERTICAL = "vertical"  # Flex column


class JustifyContent(str, Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    SPACE_BETWEEN = "space_between"
    SPACE_AROUND = "space_around"


class AlignItems(str, Enum):
    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"


class SizingMode(str, Enum):
    FIXED = "fixed"  # Absolute pixel value
    HUG = "hug"  # Fit content
    FILL = "fill"  # Fill parent


class TextAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class TextTransform(str, Enum):
    NONE = "none"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    CAPITALIZE = "capitalize"


class TextAutoResize(str, Enum):
    NONE = "none"  # Fixed width+height
    WIDTH_HEIGHT = "width_height"  # Hug both axes (auto)
    HEIGHT = "height"  # Fixed width, grow height


class GradientType(str, Enum):
    LINEAR = "linear"
    RADIAL = "radial"
    ANGULAR = "angular"
    DIAMOND = "diamond"


class StrokeAlign(str, Enum):
    INSIDE = "inside"
    CENTER = "center"
    OUTSIDE = "outside"


class BlendMode(str, Enum):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    DODGE = "color_dodge"
    BURN = "color_burn"
    HARD_LIGHT = "hard_light"
    SOFT_LIGHT = "soft_light"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    HUE = "hue"
    SATURATION = "saturation"
    COLOR = "color"
    LUMINOSITY = "luminosity"


class ImageFillMode(str, Enum):
    FILL = "fill"
    FIT = "fit"
    STRETCH = "stretch"
    TILE = "tile"
    CROP = "crop"


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------


@dataclass
class UNColor:
    """
    Normalized RGBA color.
    All channels are 0.0–1.0 floats (like Figma's internal format).
    Use UNColor.from_hex() / .to_hex() for string interchange.
    """

    r: float = 0.0
    g: float = 0.0
    b: float = 0.0
    a: float = 1.0

    @classmethod
    def from_hex(cls, hex_str: str) -> "UNColor":
        """Parse #RGB / #RRGGBB / #RRGGBBAA hex strings."""
        h = hex_str.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "FF"
        if len(h) != 8:
            raise ValueError(f"Invalid hex color: {hex_str!r}")
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        a = int(h[6:8], 16) / 255.0
        return cls(r=r, g=g, b=b, a=a)

    def to_hex(self, include_alpha: bool = True) -> str:
        """Return #RRGGBBAA or #RRGGBB string."""
        r = round(self.r * 255)
        g = round(self.g * 255)
        b = round(self.b * 255)
        a = round(self.a * 255)
        if include_alpha and a < 255:
            return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
        return f"#{r:02X}{g:02X}{b:02X}"

    def to_figma_rgb(self) -> Dict[str, float]:
        """Return Figma-style {r, g, b} dict (0-1 floats, no alpha)."""
        return {"r": round(self.r, 4), "g": round(self.g, 4), "b": round(self.b, 4)}

    def to_css_rgba(self) -> str:
        r = round(self.r * 255)
        g = round(self.g * 255)
        b = round(self.b * 255)
        return f"rgba({r},{g},{b},{round(self.a, 3)})"

    def __repr__(self) -> str:
        return f"UNColor({self.to_hex()})"


# ---------------------------------------------------------------------------
# Fills
# ---------------------------------------------------------------------------


@dataclass
class UNSolidFill:
    type: Literal["solid"] = "solid"
    color: UNColor = field(default_factory=UNColor)
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    enabled: bool = True


@dataclass
class UNGradientStop:
    color: UNColor = field(default_factory=UNColor)
    position: float = 0.0  # 0.0 – 1.0


@dataclass
class UNGradientFill:
    """
    Linear / Radial / Angular gradient.
    rotation: degrees, CSS convention (0° = top→bottom, 90° = left→right, 135° = TL→BR)
    For Pencil: CCW from up (0°=up, 90°=left, 180°=down, 270°=right)
    Conversion handled in adapters.
    """

    type: Literal["gradient"] = "gradient"
    gradient_type: GradientType = GradientType.LINEAR
    rotation: float = 180.0  # CSS degrees; 180=top-to-bottom
    stops: List[UNGradientStop] = field(default_factory=list)
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    enabled: bool = True


@dataclass
class UNImageFill:
    type: Literal["image"] = "image"
    url: str = ""  # URL or relative path
    mode: ImageFillMode = ImageFillMode.FILL
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    enabled: bool = True


# Union type for any fill
UNFill = Union[UNSolidFill, UNGradientFill, UNImageFill]


# ---------------------------------------------------------------------------
# Strokes
# ---------------------------------------------------------------------------


@dataclass
class UNStrokeThickness:
    """Per-side stroke thickness. Use .uniform() for all-sides."""

    top: Optional[float] = None
    right: Optional[float] = None
    bottom: Optional[float] = None
    left: Optional[float] = None
    all: Optional[float] = None  # Set this for uniform stroke

    @classmethod
    def uniform(cls, thickness: float) -> "UNStrokeThickness":
        return cls(all=thickness)

    def to_pencil(self) -> Union[float, Dict]:
        """Pencil accepts a number (uniform) or {top, right, bottom, left}."""
        if self.all is not None:
            return self.all
        d: Dict[str, float] = {}
        if self.top is not None:
            d["top"] = self.top
        if self.right is not None:
            d["right"] = self.right
        if self.bottom is not None:
            d["bottom"] = self.bottom
        if self.left is not None:
            d["left"] = self.left
        return d if d else 1.0

    def max_value(self) -> float:
        vals = [
            v
            for v in [self.all, self.top, self.right, self.bottom, self.left]
            if v is not None
        ]
        return max(vals) if vals else 1.0


@dataclass
class UNStroke:
    fill: UNFill = field(default_factory=lambda: UNSolidFill(color=UNColor(0, 0, 0)))
    thickness: UNStrokeThickness = field(
        default_factory=lambda: UNStrokeThickness.uniform(1.0)
    )
    align: StrokeAlign = StrokeAlign.CENTER
    cap: str = "none"  # "none" | "round" | "square"
    join: str = "miter"  # "miter" | "bevel" | "round"
    dash_pattern: List[float] = field(default_factory=list)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Effects (shadows, blurs)
# ---------------------------------------------------------------------------


@dataclass
class UNDropShadow:
    type: Literal["drop_shadow"] = "drop_shadow"
    color: UNColor = field(default_factory=lambda: UNColor(0, 0, 0, 0.25))
    offset_x: float = 0.0
    offset_y: float = 4.0
    blur: float = 8.0
    spread: float = 0.0
    inner: bool = False
    blend_mode: BlendMode = BlendMode.NORMAL
    enabled: bool = True


@dataclass
class UNBlur:
    type: Literal["blur"] = "blur"
    radius: float = 8.0
    background: bool = False  # True = backdrop blur
    enabled: bool = True


UNEffect = Union[UNDropShadow, UNBlur]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


@dataclass
class UNPadding:
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0

    @classmethod
    def all(cls, v: float) -> "UNPadding":
        return cls(v, v, v, v)

    @classmethod
    def xy(cls, horizontal: float, vertical: float) -> "UNPadding":
        return cls(top=vertical, right=horizontal, bottom=vertical, left=horizontal)

    @classmethod
    def sides(
        cls, top: float = 0, right: float = 0, bottom: float = 0, left: float = 0
    ) -> "UNPadding":
        return cls(top=top, right=right, bottom=bottom, left=left)

    def to_list(self) -> List[float]:
        """[top, right, bottom, left]"""
        return [self.top, self.right, self.bottom, self.left]

    def to_css(self) -> str:
        if self.top == self.right == self.bottom == self.left:
            return f"{self.top}px"
        if self.top == self.bottom and self.right == self.left:
            return f"{self.top}px {self.right}px"
        return f"{self.top}px {self.right}px {self.bottom}px {self.left}px"

    def is_zero(self) -> bool:
        return self.top == self.right == self.bottom == self.left == 0.0

    def to_pencil(self) -> Union[float, List[float]]:
        """Pencil: single number or [top,right,bottom,left]."""
        if self.top == self.right == self.bottom == self.left:
            return self.top
        return self.to_list()


@dataclass
class UNCornerRadius:
    tl: float = 0.0  # top-left
    tr: float = 0.0  # top-right
    br: float = 0.0  # bottom-right
    bl: float = 0.0  # bottom-left

    @classmethod
    def all(cls, r: float) -> "UNCornerRadius":
        return cls(r, r, r, r)

    @classmethod
    def sides(
        cls, tl: float = 0, tr: float = 0, br: float = 0, bl: float = 0
    ) -> "UNCornerRadius":
        return cls(tl=tl, tr=tr, br=br, bl=bl)

    def is_uniform(self) -> bool:
        return self.tl == self.tr == self.br == self.bl

    def value(self) -> float:
        """Returns uniform value; raises if not uniform."""
        if not self.is_uniform():
            raise ValueError("Corner radius is not uniform")
        return self.tl

    def to_pencil(self) -> Union[float, List[float]]:
        """Pencil accepts number or [tl, tr, br, bl]."""
        if self.is_uniform():
            return self.tl
        return [self.tl, self.tr, self.br, self.bl]

    def to_css(self) -> str:
        if self.is_uniform():
            return f"{self.tl}px"
        return f"{self.tl}px {self.tr}px {self.br}px {self.bl}px"


@dataclass
class UNSize:
    value: float = 0.0
    mode: SizingMode = SizingMode.FIXED

    @classmethod
    def fixed(cls, px: float) -> "UNSize":
        return cls(value=px, mode=SizingMode.FIXED)

    @classmethod
    def hug(cls, fallback: float = 0.0) -> "UNSize":
        return cls(value=fallback, mode=SizingMode.HUG)

    @classmethod
    def fill(cls, fallback: float = 0.0) -> "UNSize":
        return cls(value=fallback, mode=SizingMode.FILL)

    def to_pencil(self) -> Union[float, str]:
        if self.mode == SizingMode.FIXED:
            return self.value
        if self.mode == SizingMode.HUG:
            return f"fit_content({int(self.value)})" if self.value else "fit_content"
        if self.mode == SizingMode.FILL:
            return (
                f"fill_container({int(self.value)})" if self.value else "fill_container"
            )
        return self.value

    def to_css(self) -> str:
        if self.mode == SizingMode.FIXED:
            return f"{self.value}px"
        if self.mode == SizingMode.HUG:
            return "fit-content"
        if self.mode == SizingMode.FILL:
            return "100%"
        return f"{self.value}px"

    def to_figma(self) -> Dict[str, Any]:
        """Returns Figma sizing mode dict fragment."""
        if self.mode == SizingMode.HUG:
            return {"primaryAxisSizingMode": "AUTO"}
        if self.mode == SizingMode.FILL:
            return {"layoutAlign": "STRETCH", "layoutGrow": 1}
        return {}


# ---------------------------------------------------------------------------
# Text style
# ---------------------------------------------------------------------------


@dataclass
class UNTextStyle:
    font_family: str = "Inter"
    font_size: float = 14.0
    font_weight: str = "400"  # CSS weight string: "400", "600", "700", etc.
    font_style: str = "normal"  # "normal" | "italic"
    line_height: Optional[float] = None  # px; None = auto
    letter_spacing: float = 0.0  # px
    text_align: TextAlign = TextAlign.LEFT
    text_transform: TextTransform = TextTransform.NONE
    text_auto_resize: TextAutoResize = TextAutoResize.WIDTH_HEIGHT
    text_decoration: str = "none"  # "none" | "underline" | "line-through"

    def figma_font_name(self) -> Dict[str, str]:
        """Map font_weight + font_style → Figma {family, style}."""
        weight_map = {
            "100": "Thin",
            "200": "ExtraLight",
            "300": "Light",
            "400": "Regular",
            "500": "Medium",
            "600": "SemiBold",
            "700": "Bold",
            "800": "ExtraBold",
            "900": "Black",
        }
        style_suffix = " Italic" if self.font_style == "italic" else ""
        weight_name = weight_map.get(str(self.font_weight), "Regular")
        return {"family": self.font_family, "style": f"{weight_name}{style_suffix}"}

    def to_css(self) -> Dict[str, str]:
        css: Dict[str, str] = {
            "font-family": self.font_family,
            "font-size": f"{self.font_size}px",
            "font-weight": str(self.font_weight),
            "font-style": self.font_style,
            "text-align": self.text_align.value,
        }
        if self.line_height is not None:
            css["line-height"] = f"{self.line_height}px"
        if self.letter_spacing != 0:
            css["letter-spacing"] = f"{self.letter_spacing}px"
        if self.text_transform != TextTransform.NONE:
            css["text-transform"] = self.text_transform.value
        if self.text_decoration != "none":
            css["text-decoration"] = self.text_decoration
        return css


# ---------------------------------------------------------------------------
# Rich text runs
# ---------------------------------------------------------------------------


@dataclass
class UNTextRun:
    """
    A styled range within a text node's content string.

    Mirrors Figma's characterStyleOverrides / styleOverrideTable mechanism.
    Each run covers [start, end) characters within UNNode.text_content.
    Only override properties need to be set — unset fields inherit from
    the node's UNTextStyle.
    """

    content: str = ""              # Substring of text_content
    start: int = 0                 # Start character index (inclusive)
    end: int = 0                   # End character index (exclusive)

    # Style overrides — None means "inherit from node's text_style"
    fill: Optional["UNColor"] = None
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None  # "400", "700", etc.
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    letter_spacing: Optional[float] = None
    text_transform: Optional[TextTransform] = None

    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"UNTextRun.start ({self.start}) must be <= end ({self.end})")
        if self.start < 0:
            raise ValueError(f"UNTextRun.start must be >= 0, got {self.start}")


# ---------------------------------------------------------------------------
# Variable bindings (design tokens)
# ---------------------------------------------------------------------------


@dataclass
class UNVariableBinding:
    """Maps a node property to a named design token/variable."""

    property: str  # e.g. "fill.0.color", "fontSize", "width"
    variable: str  # e.g. "$--primary", "colors/brand/500"
    tool_id: Optional[str] = None  # Tool-specific variable ID for round-trips


# ---------------------------------------------------------------------------
# Core Node
# ---------------------------------------------------------------------------


@dataclass
class UNNode:
    """
    Universal Node — the single representation shared across all design tools.

    Mirrors Figma's SceneNode structure:
      - id, name, type are always present
      - x, y are absolute when layout=NONE, ignored in flex parents
      - width/height use UNSize for fixed/hug/fill semantics
      - fills, strokes, effects are ordered lists (bottom to top, like Figma)
      - children is only meaningful for FRAME/GROUP/COMPONENT
      - text_style / text_content only for TEXT nodes
      - geometry only for PATH nodes
    """

    # ── Identity ───────────────────────────────────────────────────────────
    type: NodeType = NodeType.FRAME
    id: str = ""
    name: str = "Node"

    # ── Position (ignored when parent has flex layout) ─────────────────────
    x: float = 0.0
    y: float = 0.0

    # ── Size ───────────────────────────────────────────────────────────────
    width: UNSize = field(default_factory=lambda: UNSize.fixed(100.0))
    height: UNSize = field(default_factory=lambda: UNSize.fixed(100.0))

    # ── Visual ─────────────────────────────────────────────────────────────
    fills: List[UNFill] = field(default_factory=list)
    strokes: List[UNStroke] = field(default_factory=list)
    effects: List[UNEffect] = field(default_factory=list)
    opacity: float = 1.0
    visible: bool = True
    blend_mode: BlendMode = BlendMode.NORMAL
    clip_content: bool = False  # Clip children to bounds
    rotation: float = 0.0  # Degrees, counter-clockwise

    # ── Shape ──────────────────────────────────────────────────────────────
    corner_radius: UNCornerRadius = field(default_factory=UNCornerRadius)

    # ── Layout (auto-layout / flexbox) ─────────────────────────────────────
    layout: LayoutMode = LayoutMode.NONE
    gap: float = 0.0
    padding: UNPadding = field(default_factory=UNPadding)
    justify_content: JustifyContent = JustifyContent.START
    align_items: AlignItems = AlignItems.START
    layout_wrap: bool = False  # Flex wrap
    layout_include_stroke: bool = False

    # ── Text (NodeType.TEXT only) ───────────────────────────────────────────
    text_content: str = ""
    text_style: UNTextStyle = field(default_factory=UNTextStyle)
    # Rich text runs — per-character style overrides (Figma: characterStyleOverrides)
    text_runs: List["UNTextRun"] = field(default_factory=list)

    # ── Path / Vector (NodeType.PATH only) ─────────────────────────────────
    geometry: str = ""  # SVG path d= string
    fill_rule: str = "nonzero"  # "nonzero" | "evenodd"

    # ── Ellipse (NodeType.ELLIPSE only) ────────────────────────────────────
    inner_radius: float = 0.0  # 0 = solid, 1 = hollow ring
    start_angle: float = 0.0  # Degrees
    sweep_angle: float = 360.0  # Degrees (360 = full ellipse)

    # ── Image (NodeType.IMAGE) ─────────────────────────────────────────────
    image_url: str = ""
    image_mode: ImageFillMode = ImageFillMode.FILL

    # ── Component / Instance (Figma) ───────────────────────────────────────
    component_id: str = ""  # For INSTANCE: which component it references
    component_props: Dict[str, Any] = field(default_factory=dict)

    # ── Design Tokens ──────────────────────────────────────────────────────
    variable_bindings: Dict[str, UNVariableBinding] = field(default_factory=dict)

    # ── Editor state ───────────────────────────────────────────────────────
    locked: bool = False  # Layer is locked in the editor (cannot be selected)

    # ── Children ───────────────────────────────────────────────────────────
    children: List["UNNode"] = field(default_factory=list)

    # ── Source metadata (for debugging + round-trips) ──────────────────────
    source_tool: str = ""  # "paper" | "pencil" | "figma"
    source_id: str = ""  # Original ID from source tool
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Helpers ────────────────────────────────────────────────────────────

    def add_child(self, node: "UNNode") -> "UNNode":
        self.children.append(node)
        return node

    def add_fill(self, fill: UNFill) -> "UNNode":
        self.fills.append(fill)
        return self

    def add_stroke(self, stroke: UNStroke) -> "UNNode":
        self.strokes.append(stroke)
        return self

    def add_effect(self, effect: UNEffect) -> "UNNode":
        self.effects.append(effect)
        return self

    def primary_fill_color(self) -> Optional[UNColor]:
        """Return the first enabled solid fill color, or None."""
        for f in self.fills:
            if isinstance(f, UNSolidFill) and f.enabled:
                return f.color
        return None

    def is_container(self) -> bool:
        return self.type in (
            NodeType.FRAME,
            NodeType.GROUP,
            NodeType.COMPONENT,
            NodeType.INSTANCE,
        )

    def walk(self):
        """Depth-first generator over self + all descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, pred) -> Optional["UNNode"]:
        """Return first node matching predicate, or None."""
        for node in self.walk():
            if pred(node):
                return node
        return None

    def find_all(self, pred) -> List["UNNode"]:
        return [n for n in self.walk() if pred(n)]

    def find_by_name(self, name: str) -> Optional["UNNode"]:
        return self.find(lambda n: n.name == name)

    def find_by_id(self, node_id: str) -> Optional["UNNode"]:
        return self.find(lambda n: n.id == node_id)

    def to_dict(self) -> Dict[str, Any]:
        """Lightweight serialization for debugging."""
        d: Dict[str, Any] = {
            "type": self.type.value,
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width.to_pencil(),
            "height": self.height.to_pencil(),
            "fills": len(self.fills),
            "strokes": len(self.strokes),
            "effects": len(self.effects),
            "children": len(self.children),
        }
        if self.text_content:
            d["text"] = self.text_content[:60]
        if self.geometry:
            d["geometry"] = self.geometry[:40] + "..."
        return d

    def __repr__(self) -> str:
        sz = f"{self.width.to_pencil()}×{self.height.to_pencil()}"
        return f"<UNNode {self.type.value} '{self.name}' {sz} children={len(self.children)}>"


# ---------------------------------------------------------------------------
# Factory helpers (convenience constructors)
# ---------------------------------------------------------------------------


def make_frame(
    name: str,
    width: float,
    height: float,
    *,
    fill_color: Optional[str] = None,
    layout: LayoutMode = LayoutMode.NONE,
    gap: float = 0.0,
    padding: Optional[UNPadding] = None,
    clip: bool = False,
    corner_radius: float = 0.0,
) -> UNNode:
    node = UNNode(
        type=NodeType.FRAME,
        name=name,
        width=UNSize.fixed(width),
        height=UNSize.fixed(height),
        layout=layout,
        gap=gap,
        padding=padding or UNPadding(),
        clip_content=clip,
        corner_radius=UNCornerRadius.all(corner_radius),
    )
    if fill_color:
        node.fills.append(UNSolidFill(color=UNColor.from_hex(fill_color)))
    return node


def make_text(
    name: str,
    content: str,
    *,
    font_size: float = 14.0,
    font_weight: str = "400",
    font_family: str = "Inter",
    color: str = "#000000",
    letter_spacing: float = 0.0,
    text_align: TextAlign = TextAlign.LEFT,
    text_transform: TextTransform = TextTransform.NONE,
    width: Optional[float] = None,
    height: Optional[float] = None,
) -> UNNode:
    node = UNNode(
        type=NodeType.TEXT,
        name=name,
        text_content=content,
        text_style=UNTextStyle(
            font_family=font_family,
            font_size=font_size,
            font_weight=font_weight,
            letter_spacing=letter_spacing,
            text_align=text_align,
            text_transform=text_transform,
        ),
    )
    node.fills.append(UNSolidFill(color=UNColor.from_hex(color)))
    if width is not None:
        node.width = UNSize.fixed(width)
        node.text_style.text_auto_resize = TextAutoResize.HEIGHT
    else:
        node.width = UNSize.hug()
        node.text_style.text_auto_resize = TextAutoResize.WIDTH_HEIGHT
    if height is not None:
        node.height = UNSize.fixed(height)
    else:
        node.height = UNSize.hug()
    return node


def make_rect(
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill_color: Optional[str] = None,
    corner_radius: float = 0.0,
) -> UNNode:
    node = UNNode(
        type=NodeType.RECTANGLE,
        name=name,
        x=x,
        y=y,
        width=UNSize.fixed(width),
        height=UNSize.fixed(height),
        corner_radius=UNCornerRadius.all(corner_radius),
    )
    if fill_color:
        node.fills.append(UNSolidFill(color=UNColor.from_hex(fill_color)))
    return node


def make_ellipse(
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill_color: Optional[str] = None,
) -> UNNode:
    node = UNNode(
        type=NodeType.ELLIPSE,
        name=name,
        x=x,
        y=y,
        width=UNSize.fixed(width),
        height=UNSize.fixed(height),
    )
    if fill_color:
        node.fills.append(UNSolidFill(color=UNColor.from_hex(fill_color)))
    return node


def make_path(
    name: str,
    width: float,
    height: float,
    geometry: str,
    *,
    stroke_color: Optional[str] = None,
    stroke_width: float = 1.0,
    stroke_cap: str = "round",
    stroke_join: str = "round",
    fill_color: Optional[str] = None,
) -> UNNode:
    node = UNNode(
        type=NodeType.PATH,
        name=name,
        width=UNSize.fixed(width),
        height=UNSize.fixed(height),
        geometry=geometry,
    )
    if fill_color:
        node.fills.append(UNSolidFill(color=UNColor.from_hex(fill_color)))
    if stroke_color:
        node.strokes.append(
            UNStroke(
                fill=UNSolidFill(color=UNColor.from_hex(stroke_color)),
                thickness=UNStrokeThickness.uniform(stroke_width),
                align=StrokeAlign.CENTER,
                cap=stroke_cap,
                join=stroke_join,
            )
        )
    return node


def make_gradient_fill(
    gradient_type: GradientType = GradientType.LINEAR,
    rotation: float = 180.0,
    stops: Optional[List] = None,
    opacity: float = 1.0,
) -> UNGradientFill:
    """Convenience constructor for gradient fills."""
    return UNGradientFill(
        gradient_type=gradient_type,
        rotation=rotation,
        stops=stops or [],
        opacity=opacity,
    )


def make_solid_fill(hex_color: str, opacity: float = 1.0) -> UNSolidFill:
    c = UNColor.from_hex(hex_color)
    c.a = min(c.a, opacity)
    return UNSolidFill(color=c)


def make_shadow(
    color: str = "#00000040",
    offset_x: float = 0.0,
    offset_y: float = 4.0,
    blur: float = 8.0,
    spread: float = 0.0,
    inner: bool = False,
) -> UNDropShadow:
    return UNDropShadow(
        color=UNColor.from_hex(color),
        offset_x=offset_x,
        offset_y=offset_y,
        blur=blur,
        spread=spread,
        inner=inner,
    )


# ---------------------------------------------------------------------------
# Serialisation / deserialisation  (JSON-round-trip for caching / debug)
# ---------------------------------------------------------------------------


def _fill_to_dict(f: UNFill) -> Dict[str, Any]:
    if isinstance(f, UNSolidFill):
        return {
            "type": "solid",
            "color": f.color.to_hex(),
            "opacity": f.opacity,
            "blend_mode": f.blend_mode.value if hasattr(f, 'blend_mode') and f.blend_mode else "normal",
            "enabled": f.enabled,
        }
    if isinstance(f, UNGradientFill):
        return {
            "type": "gradient",
            "gradient_type": f.gradient_type.value,
            "rotation": f.rotation,
            "opacity": f.opacity,
            "enabled": f.enabled,
            "stops": [
                {"color": s.color.to_hex(), "position": s.position} for s in f.stops
            ],
        }
    if isinstance(f, UNImageFill):
        return {
            "type": "image",
            "url": f.url,
            "mode": f.mode.value,
            "opacity": f.opacity,
            "enabled": f.enabled,
        }
    return {}


def _fill_from_dict(d: Dict[str, Any]) -> UNFill:
    t = d.get("type")
    if t == "solid":
        bm_raw = d.get("blend_mode", "normal")
        try:
            blend_mode = BlendMode(bm_raw)
        except (ValueError, AttributeError):
            blend_mode = BlendMode.NORMAL
        return UNSolidFill(
            color=UNColor.from_hex(d["color"]),
            opacity=d.get("opacity", 1.0),
            blend_mode=blend_mode,
            enabled=d.get("enabled", True),
        )
    if t == "gradient":
        stops = [
            UNGradientStop(color=UNColor.from_hex(s["color"]), position=s["position"])
            for s in d.get("stops", [])
        ]
        return UNGradientFill(
            gradient_type=GradientType(d.get("gradient_type", "linear")),
            rotation=d.get("rotation", 180.0),
            opacity=d.get("opacity", 1.0),
            enabled=d.get("enabled", True),
            stops=stops,
        )
    if t == "image":
        return UNImageFill(
            url=d.get("url", ""),
            mode=ImageFillMode(d.get("mode", "fill")),
            opacity=d.get("opacity", 1.0),
            enabled=d.get("enabled", True),
        )
    raise ValueError(f"Unknown fill type: {t!r}. Expected 'solid', 'gradient', or 'image'.")


def un_node_to_dict(node: UNNode) -> Dict[str, Any]:
    """Full serialization to a plain dict (JSON-safe)."""
    d: Dict[str, Any] = {
        "type": node.type.value,
        "id": node.id,
        "name": node.name,
        "x": node.x,
        "y": node.y,
        "width": {"value": node.width.value, "mode": node.width.mode.value},
        "height": {"value": node.height.value, "mode": node.height.mode.value},
        "fills": [_fill_to_dict(f) for f in node.fills],
        "strokes": [],
        "effects": [],
        "opacity": node.opacity,
        "visible": node.visible,
        "clip_content": node.clip_content,
        "rotation": node.rotation,
        "corner_radius": {
            "tl": node.corner_radius.tl,
            "tr": node.corner_radius.tr,
            "br": node.corner_radius.br,
            "bl": node.corner_radius.bl,
        },
        "layout": node.layout.value,
        "gap": node.gap,
        "padding": node.padding.to_list(),
        "justify_content": node.justify_content.value,
        "align_items": node.align_items.value,
        "source_tool": node.source_tool,
        "source_id": node.source_id,
    }

    # Strokes
    for s in node.strokes:
        sd: Dict[str, Any] = {
            "fill": _fill_to_dict(s.fill),
            "thickness": s.thickness.to_pencil(),
            "align": s.align.value,
            "cap": s.cap,
            "join": s.join,
            "dash_pattern": s.dash_pattern,
            "enabled": s.enabled,
        }
        d["strokes"].append(sd)

    # Effects
    for e in node.effects:
        if isinstance(e, UNDropShadow):
            d["effects"].append(
                {
                    "type": "drop_shadow",
                    "color": e.color.to_hex(),
                    "offset_x": e.offset_x,
                    "offset_y": e.offset_y,
                    "blur": e.blur,
                    "spread": e.spread,
                    "inner": e.inner,
                    "enabled": e.enabled,
                }
            )
        elif isinstance(e, UNBlur):
            d["effects"].append(
                {
                    "type": "blur",
                    "radius": e.radius,
                    "background": e.background,
                    "enabled": e.enabled,
                }
            )

    # Text
    if node.type == NodeType.TEXT:
        ts = node.text_style
        d["text_content"] = node.text_content
        d["text_style"] = {
            "font_family": ts.font_family,
            "font_size": ts.font_size,
            "font_weight": ts.font_weight,
            "font_style": ts.font_style,
            "line_height": ts.line_height,
            "letter_spacing": ts.letter_spacing,
            "text_align": ts.text_align.value,
            "text_transform": ts.text_transform.value,
            "text_auto_resize": ts.text_auto_resize.value,
            "text_decoration": ts.text_decoration,
        }
        if node.text_runs:
            d["text_runs"] = [
                {
                    "content": run.content,
                    "start": run.start,
                    "end": run.end,
                    "fill": {"r": run.fill.r, "g": run.fill.g, "b": run.fill.b, "a": run.fill.a} if run.fill else None,
                    "font_family": run.font_family,
                    "font_size": run.font_size,
                    "font_weight": run.font_weight,
                    "italic": run.italic,
                    "underline": run.underline,
                    "strikethrough": run.strikethrough,
                    "letter_spacing": run.letter_spacing,
                    "text_transform": run.text_transform.value if run.text_transform else None,
                }
                for run in node.text_runs
            ]

    # Path
    if node.type == NodeType.PATH:
        d["geometry"] = node.geometry
        d["fill_rule"] = node.fill_rule

    # Ellipse
    if node.type == NodeType.ELLIPSE:
        d["inner_radius"] = node.inner_radius
        d["start_angle"] = node.start_angle
        d["sweep_angle"] = node.sweep_angle

    # Children
    d["children"] = [un_node_to_dict(c) for c in node.children]
    return d


def un_node_from_dict(d: Dict[str, Any]) -> UNNode:
    """Full deserialization from a plain dict."""
    w_d = d.get("width", {})
    h_d = d.get("height", {})
    pad = d.get("padding", [0, 0, 0, 0])
    cr = d.get("corner_radius", {})
    ts_d = d.get("text_style", {})

    node = UNNode(
        type=NodeType(d.get("type", "frame")),
        id=d.get("id", ""),
        name=d.get("name", ""),
        x=d.get("x", 0.0),
        y=d.get("y", 0.0),
        width=UNSize(
            value=w_d.get("value", 0.0),
            mode=SizingMode(w_d.get("mode", "fixed")),
        ),
        height=UNSize(
            value=h_d.get("value", 0.0),
            mode=SizingMode(h_d.get("mode", "fixed")),
        ),
        opacity=d.get("opacity", 1.0),
        visible=d.get("visible", True),
        clip_content=d.get("clip_content", False),
        rotation=d.get("rotation", 0.0),
        corner_radius=UNCornerRadius(
            tl=cr.get("tl", 0.0),
            tr=cr.get("tr", 0.0),
            br=cr.get("br", 0.0),
            bl=cr.get("bl", 0.0),
        ),
        layout=LayoutMode(d.get("layout", "none")),
        gap=d.get("gap", 0.0),
        padding=UNPadding(
            top=pad[0] if len(pad) > 0 else 0,
            right=pad[1] if len(pad) > 1 else 0,
            bottom=pad[2] if len(pad) > 2 else 0,
            left=pad[3] if len(pad) > 3 else 0,
        ),
        justify_content=JustifyContent(d.get("justify_content", "start")),
        align_items=AlignItems(d.get("align_items", "start")),
        source_tool=d.get("source_tool", ""),
        source_id=d.get("source_id", ""),
        text_content=d.get("text_content", ""),
        geometry=d.get("geometry", ""),
        fill_rule=d.get("fill_rule", "nonzero"),
        inner_radius=d.get("inner_radius", 0.0),
        start_angle=d.get("start_angle", 0.0),
        sweep_angle=d.get("sweep_angle", 360.0),
    )

    # Text style
    if ts_d:
        node.text_style = UNTextStyle(
            font_family=ts_d.get("font_family", "Inter"),
            font_size=ts_d.get("font_size", 14.0),
            font_weight=str(ts_d.get("font_weight", "400")),
            font_style=ts_d.get("font_style", "normal"),
            line_height=ts_d.get("line_height"),
            letter_spacing=ts_d.get("letter_spacing", 0.0),
            text_align=TextAlign(ts_d.get("text_align", "left")),
            text_transform=TextTransform(ts_d.get("text_transform", "none")),
            text_auto_resize=TextAutoResize(
                ts_d.get("text_auto_resize", "width_height")
            ),
            text_decoration=ts_d.get("text_decoration", "none"),
        )

    # Text runs
    raw_runs = d.get("text_runs", [])
    if raw_runs:
        node.text_runs = []
        for r in raw_runs:
            fill_d = r.get("fill")
            fill_color = UNColor(r=fill_d["r"], g=fill_d["g"], b=fill_d["b"], a=fill_d.get("a", 1.0)) if fill_d else None
            tt_raw = r.get("text_transform")
            tt = None
            if tt_raw:
                try:
                    tt = TextTransform(tt_raw)
                except ValueError:
                    pass
            node.text_runs.append(UNTextRun(
                content=r.get("content", ""),
                start=r.get("start", 0),
                end=r.get("end", 0),
                fill=fill_color,
                font_family=r.get("font_family"),
                font_size=r.get("font_size"),
                font_weight=r.get("font_weight"),
                italic=r.get("italic", False),
                underline=r.get("underline", False),
                strikethrough=r.get("strikethrough", False),
                letter_spacing=r.get("letter_spacing"),
                text_transform=tt,
            ))

    # Fills / strokes / effects
    for fd in d.get("fills", []):
        node.fills.append(_fill_from_dict(fd))

    for sd in d.get("strokes", []):
        th = sd.get("thickness", 1.0)
        if isinstance(th, dict):
            thickness = UNStrokeThickness(
                top=th.get("top"),
                right=th.get("right"),
                bottom=th.get("bottom"),
                left=th.get("left"),
            )
        else:
            thickness = UNStrokeThickness.uniform(float(th))
        node.strokes.append(
            UNStroke(
                fill=_fill_from_dict(
                    sd.get("fill", {"type": "solid", "color": "#000000"})
                ),
                thickness=thickness,
                align=StrokeAlign(sd.get("align", "center")),
                cap=sd.get("cap", "none"),
                join=sd.get("join", "miter"),
                dash_pattern=sd.get("dash_pattern", []),
                enabled=sd.get("enabled", True),
            )
        )

    for ed in d.get("effects", []):
        et = ed.get("type")
        if et == "drop_shadow":
            node.effects.append(
                UNDropShadow(
                    color=UNColor.from_hex(ed.get("color", "#00000040")),
                    offset_x=ed.get("offset_x", 0.0),
                    offset_y=ed.get("offset_y", 4.0),
                    blur=ed.get("blur", 8.0),
                    spread=ed.get("spread", 0.0),
                    inner=ed.get("inner", False),
                    enabled=ed.get("enabled", True),
                )
            )
        elif et == "blur":
            node.effects.append(
                UNBlur(
                    radius=ed.get("radius", 8.0),
                    background=ed.get("background", False),
                    enabled=ed.get("enabled", True),
                )
            )

    # Children (recursive)
    for cd in d.get("children", []):
        node.children.append(un_node_from_dict(cd))

    return node


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def serialize_tree(node: UNNode, indent: int = 0) -> str:
    """Human-readable tree dump for debugging."""
    pad = "  " * indent
    sz = f"{node.width.to_pencil()}×{node.height.to_pencil()}"
    txt = f" '{node.text_content[:30]}'" if node.text_content else ""
    geo = f" <path>" if node.geometry else ""
    line = f"{pad}[{node.type.value}] '{node.name}' {sz}{txt}{geo}"
    lines = [line]
    for child in node.children:
        lines.append(serialize_tree(child, indent + 1))
    return "\n".join(lines)


def count_nodes(node: UNNode) -> int:
    """Count total nodes in subtree including self."""
    return 1 + sum(count_nodes(c) for c in node.children)
