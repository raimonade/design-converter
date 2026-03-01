// ─────────────────────────────────────────────────────────────────────────────
// UNNode IR Reference — Accurate to services/design-converter/ir/nodes.py
// ─────────────────────────────────────────────────────────────────────────────

export interface IRField {
  name: string;
  type: string;
  default: string;
  description: string;
}

export interface IRSection {
  id: string;
  title: string;
  description: string;
  fields?: IRField[];
  code?: string;
  subsections?: IRSection[];
}

export const irSections: IRSection[] = [
  {
    id: 'overview',
    title: 'Executive Summary',
    description: 'UNNode (Universal Node) is a Python dataclass-based Intermediate Representation (IR) for design tool conversion. It occupies a single canonical layer between Figma, Paper Design, and Pencil.dev.',
    fields: [
      { name: 'Figma', type: 'REST + Plugin API JS', default: '-', description: 'Read & Write' },
      { name: 'Paper Design', type: 'MCP JSON-RPC :29979', default: '-', description: 'Read & Write' },
      { name: 'Pencil.dev', type: 'HTTP REST MCP :19002', default: '-', description: 'Read & Write' },
    ],
    code: `from ir import UNNode, NodeType

# Create a frame with auto-layout
card = UNNode(
    type=NodeType.FRAME,
    name="Card",
    visible=True
)`,
  },
  {
    id: 'core-structure',
    title: 'Core Node Structure',
    description: 'Every design node — frames, text, rectangles, ellipses, paths, components — maps to a UNNode with a NodeType enum. The tree mirrors the design tool\'s layer hierarchy.',
    fields: [
      { name: 'type', type: 'NodeType', default: 'frame', description: 'Node type enum (required)' },
      { name: 'name', type: 'str', default: '"Untitled"', description: 'Display name' },
      { name: 'figma_id', type: 'str', default: '""', description: 'Original Figma node ID' },
      { name: 'visible', type: 'bool', default: 'True', description: 'Visibility flag' },
      { name: 'locked', type: 'bool', default: 'False', description: 'Lock state' },
      { name: 'opacity', type: 'float', default: '1.0', description: 'Node opacity (0-1)' },
      { name: 'blend_mode', type: 'BlendMode', default: 'normal', description: 'Node blend mode' },
    ],
    code: `from ir import UNNode, NodeType, BlendMode

node = UNNode(
    type=NodeType.FRAME,
    name="Button",
    visible=True,
    opacity=0.9,
    blend_mode=BlendMode.NORMAL
)`,
  },
  {
    id: 'geometry',
    title: 'Geometry',
    description: 'Position and dimension properties. All coordinates are in pixels relative to parent. Width and height use UNSize for per-axis sizing modes.',
    fields: [
      { name: 'x', type: 'float', default: '0.0', description: 'X position' },
      { name: 'y', type: 'float', default: '0.0', description: 'Y position' },
      { name: 'width', type: 'UNSize', default: 'UNSize(100, FIXED)', description: 'Width with mode' },
      { name: 'height', type: 'UNSize', default: 'UNSize(100, FIXED)', description: 'Height with mode' },
      { name: 'rotation', type: 'float', default: '0.0', description: 'Rotation in degrees' },
      { name: 'corner_radius', type: 'UNCornerRadius', default: 'UNCornerRadius()', description: 'Corner radii' },
    ],
    code: `from ir import UNSize, SizingMode, UNCornerRadius

node.width = UNSize(200, SizingMode.FIXED)
node.height = UNSize(value=100, mode=SizingMode.HUG)
node.corner_radius = UNCornerRadius(top_left=8, top_right=8, bottom_left=8, bottom_right=8)`,
  },
  {
    id: 'sizing',
    title: 'UNSize — Per-Axis Sizing',
    description: 'Figma has independent primaryAxisSizingMode and counterAxisSizingMode. A node can be FIXED width + FILL height. UNSize captures this per-axis.',
    fields: [
      { name: 'value', type: 'float', default: '100.0', description: 'Pixel size' },
      { name: 'mode', type: 'SizingMode', default: 'FIXED', description: 'FIXED / HUG / FILL' },
    ],
    code: `from ir import UNSize, SizingMode

# Fixed size
fixed = UNSize(200, SizingMode.FIXED)

# Shrink-wrap children (CSS: width: fit-content)
hug = UNSize(value=0, mode=SizingMode.HUG)

# Fill available space (CSS: flex-grow: 1)
fill = UNSize(value=0, mode=SizingMode.FILL)`,
  },
  {
    id: 'fills',
    title: 'Fills',
    description: 'Fill layers including solid colors, gradients, and images. Each fill has opacity and visibility. Fills stack in order.',
    fields: [
      { name: 'fills', type: 'List[UNFill]', default: '[]', description: 'Stacked fill layers' },
      { name: 'UNSolidFill', type: 'dataclass', default: '-', description: 'color, opacity, visible' },
      { name: 'UNLinearGradientFill', type: 'dataclass', default: '-', description: 'Linear gradient with stops' },
      { name: 'UNRadialGradientFill', type: 'dataclass', default: '-', description: 'Radial gradient' },
      { name: 'UNAngularGradientFill', type: 'dataclass', default: '-', description: 'Angular/conic gradient' },
      { name: 'UNDiamondGradientFill', type: 'dataclass', default: '-', description: 'Diamond gradient' },
      { name: 'UNImageFill', type: 'dataclass', default: '-', description: 'Image with URL and mode' },
    ],
    code: `from ir import UNSolidFill, UNColor

node.fills.append(UNSolidFill(
    color=UNColor.from_hex("#0066FF"),
    opacity=0.8,
    visible=True
))`,
  },
  {
    id: 'strokes',
    title: 'Strokes',
    description: 'Border/stroke properties for outlines. Supports weight, alignment, and dash patterns.',
    fields: [
      { name: 'strokes', type: 'List[UNStroke]', default: '[]', description: 'Stroke layers' },
      { name: 'stroke_weight', type: 'float', default: '0.0', description: 'Stroke thickness' },
      { name: 'stroke_align', type: 'StrokeAlign', default: 'inside', description: 'INSIDE / CENTER / OUTSIDE' },
      { name: 'dash_pattern', type: 'List[float]', default: '[]', description: 'Dash pattern' },
    ],
    code: `from ir import UNStroke, UNColor, StrokeAlign

node.strokes.append(UNStroke(
    color=UNColor.from_hex("#333"),
    weight=2.0,
    align=StrokeAlign.INSIDE
))`,
  },
  {
    id: 'effects',
    title: 'Effects',
    description: 'Visual effects like shadows and blurs applied to nodes. Multiple effects stack.',
    fields: [
      { name: 'effects', type: 'List[UNEffect]', default: '[]', description: 'Effect layers' },
      { name: 'UNDropShadow', type: 'dataclass', default: '-', description: 'color, offset_x/y, blur, spread' },
      { name: 'UNInnerShadow', type: 'dataclass', default: '-', description: 'Inner shadow effect' },
      { name: 'UNBlur', type: 'dataclass', default: '-', description: 'Layer blur with radius' },
      { name: 'UNBackgroundBlur', type: 'dataclass', default: '-', description: 'Backdrop-filter blur' },
    ],
    code: `from ir import UNDropShadow, UNColor

node.effects.append(UNDropShadow(
    color=UNColor(r=0, g=0, b=0, a=0.25),
    offset_x=0, offset_y=4,
    blur=12, spread=0
))`,
  },
  {
    id: 'layout',
    title: 'Auto Layout',
    description: 'Figma-style flexbox auto-layout. Matches CSS flexbox semantics. Supports gap, padding, alignment, and wrap.',
    fields: [
      { name: 'layout', type: 'LayoutMode', default: 'none', description: 'NONE / HORIZONTAL / VERTICAL' },
      { name: 'gap', type: 'float', default: '0.0', description: 'Item spacing (itemSpacing)' },
      { name: 'padding', type: 'UNPadding', default: 'UNPadding()', description: 'top/right/bottom/left' },
      { name: 'align_items', type: 'AlignItems', default: 'start', description: 'Cross-axis alignment' },
      { name: 'justify_content', type: 'JustifyContent', default: 'start', description: 'Main-axis alignment' },
      { name: 'layout_wrap', type: 'bool', default: 'False', description: 'Wrap children' },
      { name: 'clip_content', type: 'bool', default: 'False', description: 'Overflow hidden' },
    ],
    code: `from ir import LayoutMode, UNPadding, AlignItems, JustifyContent

card = UNNode(type=NodeType.FRAME, name="Card")
card.layout = LayoutMode.HORIZONTAL
card.gap = 8
card.padding = UNPadding(top=16, right=16, bottom=16, left=16)
card.align_items = AlignItems.CENTER
card.justify_content = JustifyContent.SPACE_BETWEEN`,
  },
  {
    id: 'text',
    title: 'Text',
    description: 'Typography properties for TEXT nodes. Supports rich text via text_runs for per-character styling.',
    fields: [
      { name: 'characters', type: 'str', default: '""', description: 'Text content' },
      { name: 'text_style', type: 'UNTextStyle', default: 'None', description: 'Font properties' },
      { name: 'text_runs', type: 'List[UNTextRun]', default: '[]', description: 'Rich text spans' },
      { name: 'text_auto_resize', type: 'TextAutoResize', default: 'none', description: 'Resize behavior' },
      { name: 'text_align', type: 'TextAlign', default: 'left', description: 'Text alignment' },
      { name: 'text_transform', type: 'TextTransform', default: 'none', description: 'Text case' },
    ],
    code: `from ir import UNNode, NodeType, UNTextStyle, UNColor

title = UNNode(type=NodeType.TEXT, name="Title")
title.characters = "Hello World"
title.text_style = UNTextStyle(
    font_family="Inter",
    font_size=16,
    font_weight="600",
    color=UNColor.from_hex("#333")
)`,
  },
  {
    id: 'text-runs',
    title: 'Text Runs (Rich Text)',
    description: 'UNTextRun captures per-character style overrides from Figma\'s characterStyleOverrides. Enables rich text with mixed styles.',
    fields: [
      { name: 'start', type: 'int', default: '0', description: 'Start character index' },
      { name: 'end', type: 'int', default: '0', description: 'End character index' },
      { name: 'font_size', type: 'Optional[float]', default: 'None', description: 'Override font size' },
      { name: 'font_weight', type: 'Optional[str]', default: 'None', description: 'Override weight' },
      { name: 'color', type: 'Optional[UNColor]', default: 'None', description: 'Override color' },
      { name: 'text_decoration', type: 'Optional[str]', default: 'None', description: 'underline/strikethrough' },
    ],
    code: `from ir import UNTextRun, UNColor

# Apply bold + red to characters 0-5
run = UNTextRun(
    start=0,
    end=5,
    font_weight="700",
    color=UNColor.from_hex("#FF0000")
)
node.text_runs.append(run)`,
  },
  {
    id: 'components',
    title: 'Components',
    description: 'Figma component definition and instance references. Component masters define reusable elements.',
    fields: [
      { name: 'is_component', type: 'bool', default: 'False', description: 'Is component definition' },
      { name: 'component_id', type: 'Optional[str]', default: 'None', description: 'Component reference' },
      { name: 'overrides', type: 'List[UNOverride]', default: '[]', description: 'Instance overrides' },
    ],
    code: `# Component master
button_master = UNNode(type=NodeType.COMPONENT, name="Button")
button_master.is_component = True

# Component instance
button_instance = UNNode(type=NodeType.INSTANCE, name="Button Instance")
button_instance.component_id = button_master.figma_id`,
  },
  {
    id: 'variables',
    title: 'Variables',
    description: 'Design variable bindings for round-trip token fidelity. Binds node properties to design tokens.',
    fields: [
      { name: 'variable_bindings', type: 'Dict[str, UNVariableBinding]', default: '{}', description: 'Bound variables' },
    ],
    code: `from ir import UNVariableBinding

node.variable_bindings["fills[0].color"] = UNVariableBinding(
    property="fills[0].color",
    variable="brand/primary",
    tool_id="figma:vars"
)`,
  },
  {
    id: 'serialization',
    title: 'Serialization',
    description: 'JSON round-trip support for caching and transport. un_node_to_dict() and un_node_from_dict() preserve all fields.',
    fields: [
      { name: 'un_node_to_dict', type: 'function', default: '-', description: 'Convert UNNode to dict' },
      { name: 'un_node_from_dict', type: 'function', default: '-', description: 'Convert dict to UNNode' },
    ],
    code: `from ir import un_node_to_dict, un_node_from_dict
import json

# Serialize to JSON-compatible dict
data = un_node_to_dict(node)
json_str = json.dumps(data, indent=2)

# Deserialize back
restored = un_node_from_dict(data)`,
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Enums — Exact values from nodes.py
// ─────────────────────────────────────────────────────────────────────────────
export const irEnums = [
  {
    name: 'NodeType',
    values: ['frame', 'text', 'rectangle', 'ellipse', 'path', 'line', 'group', 'image', 'component', 'instance'],
    description: 'All supported node types'
  },
  {
    name: 'LayoutMode',
    values: ['none', 'horizontal', 'vertical'],
    description: 'Flex direction'
  },
  {
    name: 'AlignItems',
    values: ['start', 'center', 'end', 'stretch'],
    description: 'Cross-axis alignment'
  },
  {
    name: 'JustifyContent',
    values: ['start', 'center', 'end', 'space_between', 'space_around'],
    description: 'Main-axis alignment'
  },
  {
    name: 'SizingMode',
    values: ['fixed', 'hug', 'fill'],
    description: 'Width/height sizing constraint'
  },
  {
    name: 'BlendMode',
    values: ['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten', 'color_dodge', 'color_burn', 'hard_light', 'soft_light', 'difference', 'exclusion', 'hue', 'saturation', 'color', 'luminosity'],
    description: 'Blend modes (CSS compositing)'
  },
  {
    name: 'StrokeAlign',
    values: ['inside', 'center', 'outside'],
    description: 'Stroke position'
  },
  {
    name: 'TextAlign',
    values: ['left', 'center', 'right', 'justify'],
    description: 'Horizontal text alignment'
  },
  {
    name: 'TextTransform',
    values: ['none', 'uppercase', 'lowercase', 'capitalize'],
    description: 'Text case transformation'
  },
  {
    name: 'TextAutoResize',
    values: ['none', 'width_height', 'height'],
    description: 'Text resize behavior'
  },
  {
    name: 'GradientType',
    values: ['linear', 'radial', 'angular', 'diamond'],
    description: 'Gradient fill types'
  },
  {
    name: 'ImageFillMode',
    values: ['fill', 'fit', 'stretch', 'tile', 'crop'],
    description: 'Image fill scaling'
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Key Facts
// ─────────────────────────────────────────────────────────────────────────────
export const irKeyFacts = [
  {
    title: 'Zero Dependencies',
    description: 'The design-converter uses only Python stdlib — no external runtime dependencies. Works anywhere Python 3.9+ runs.'
  },
  {
    title: 'Figma-Modeled',
    description: 'IR mirrors Figma\'s node architecture, making it the natural interchange format for design tools.'
  },
  {
    title: 'Symmetric Adapters',
    description: 'If you can read from a tool, you can write to it. All adapters implement BaseReader/BaseWriter.'
  },
  {
    title: '146 Tests',
    description: 'Full test coverage for IR, adapters, HTTP bridge, and token extraction. Battle-tested and production-ready.'
  },
  {
    title: 'Rich Text Runs',
    description: 'UNTextRun captures per-character style overrides from Figma\'s characterStyleOverrides for accurate rich text.'
  },
  {
    title: 'DTCG Token Export',
    description: 'utils/tokens.py emits W3C Design Tokens Community Group 2025.10 format for design system integration.'
  },
];
