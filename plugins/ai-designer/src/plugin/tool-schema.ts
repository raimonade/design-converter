// Figma AI Designer - Tool Schema Definitions
// Professional tool-based architecture for AI-driven Figma generation

export interface ToolDefinition {
  name: string
  description: string
  args: ToolArgument[]
  category: ToolCategory
  returns: string
}

export interface ToolArgument {
  name: string
  type: "string" | "number" | "boolean" | "object" | "array"
  description: string
  required: boolean
  default?: unknown
}

export type ToolCategory = 
  | "document" 
  | "variables" 
  | "components" 
  | "creation" 
  | "styling" 
  | "layout" 
  | "organization"

export const TOOL_CATEGORIES: Record<ToolCategory, { color: string; description: string }> = {
  document: { color: "#8B5CF6", description: "Document operations" },
  variables: { color: "#06B6D4", description: "Design tokens & variables" },
  components: { color: "#F59E0B", description: "Component creation & management" },
  creation: { color: "#10B981", description: "Element creation" },
  styling: { color: "#EF4444", description: "Colors, strokes, effects" },
  layout: { color: "#3B82F6", description: "Auto-layout & positioning" },
  organization: { color: "#EC4899", description: "Layers & hierarchy" }
}

export const FIGMA_TOOLS: ToolDefinition[] = [
  // ═══════════════════════════════════════════════════════════════
  // DOCUMENT OPERATIONS
  // ═══════════════════════════════════════════════════════════════
  {
    name: "get_document",
    description: "Get the current Figma document structure including pages, frames, and components",
    category: "document",
    args: [],
    returns: "Document structure with pages, frames, and component definitions"
  },
  {
    name: "get_selection",
    description: "Get currently selected elements in Figma",
    category: "document",
    args: [],
    returns: "Array of selected nodes with their properties"
  },
  {
    name: "get_components",
    description: "List all components in the current file",
    category: "document",
    args: [],
    returns: "Array of component definitions"
  },

  // ═══════════════════════════════════════════════════════════════
  // VARIABLES & TOKENS
  // ═══════════════════════════════════════════════════════════════
  {
    name: "create_variable_collection",
    description: "Create a new variable collection (e.g., for Light/Dark mode)",
    category: "variables",
    args: [
      { name: "name", type: "string", description: "Collection name", required: true }
    ],
    returns: "Created collection with mode IDs"
  },
  {
    name: "create_color_variable",
    description: "Create a color variable in a collection",
    category: "variables",
    args: [
      { name: "name", type: "string", description: "Variable name (e.g., 'primary', 'background')", required: true },
      { name: "collection", type: "string", description: "Collection name", required: true },
      { name: "light", type: "string", description: "Light mode color (hex)", required: true },
      { name: "dark", type: "string", description: "Dark mode color (hex)", required: false }
    ],
    returns: "Created variable with ID"
  },
  {
    name: "bind_variable",
    description: "Bind a node property to a variable",
    category: "variables",
    args: [
      { name: "nodeId", type: "string", description: "Node ID to bind", required: true },
      { name: "property", type: "string", description: "Property: 'fill', 'stroke', 'text'", required: true },
      { name: "variableId", type: "string", description: "Variable ID to bind", required: true }
    ],
    returns: "Success confirmation"
  },

  // ═══════════════════════════════════════════════════════════════
  // COMPONENTS
  // ═══════════════════════════════════════════════════════════════
  {
    name: "create_component",
    description: "Create a new component from a frame",
    category: "components",
    args: [
      { name: "name", type: "string", description: "Component name with atomic prefix (atom/button, molecule/card)", required: true },
      { name: "page", type: "string", description: "Target page: 'Atoms', 'Molecules', 'Organisms'", required: true },
      { name: "fromFrame", type: "string", description: "Frame node ID to convert", required: false },
      { name: "description", type: "string", description: "Component description", required: false }
    ],
    returns: "Created component node ID"
  },
  {
    name: "create_component_property",
    description: "Add a property to a component (for variants)",
    category: "components",
    args: [
      { name: "componentId", type: "string", description: "Component ID", required: true },
      { name: "name", type: "string", description: "Property name", required: true },
      { name: "type", type: "string", description: "Type: BOOLEAN, TEXT, INSTANCE_SWAP, VARIANT", required: true },
      { name: "defaultValue", type: "string", description: "Default value", required: true }
    ],
    returns: "Success confirmation"
  },
  {
    name: "create_variant_set",
    description: "Combine multiple components as variants",
    category: "components",
    args: [
      { name: "componentIds", type: "array", description: "Array of component IDs", required: true },
      { name: "variantProperty", type: "string", description: "Property name to vary by", required: true }
    ],
    returns: "Created variant set"
  },
  {
    name: "create_instance",
    description: "Create an instance of a component",
    category: "components",
    args: [
      { name: "componentId", type: "string", description: "Component ID to instance", required: true },
      { name: "x", type: "number", description: "X position", required: false },
      { name: "y", type: "number", description: "Y position", required: false },
      { name: "overrides", type: "object", description: "Property overrides", required: false }
    ],
    returns: "Created instance node ID"
  },

  // ═══════════════════════════════════════════════════════════════
  // CREATION
  // ═══════════════════════════════════════════════════════════════
  {
    name: "create_frame",
    description: "Create a new frame with auto-layout",
    category: "creation",
    args: [
      { name: "name", type: "string", description: "Frame name", required: true },
      { name: "width", type: "number", description: "Width in pixels", required: false },
      { name: "height", type: "number", description: "Height in pixels", required: false },
      { name: "layoutMode", type: "string", description: "NONE, HORIZONTAL, VERTICAL", required: false, default: "VERTICAL" },
      { name: "itemSpacing", type: "number", description: "Spacing between children", required: false },
      { name: "padding", type: "number", description: "Padding all sides", required: false },
      { name: "paddingTop", type: "number", description: "Top padding", required: false },
      { name: "paddingBottom", type: "number", description: "Bottom padding", required: false },
      { name: "paddingLeft", type: "number", description: "Left padding", required: false },
      { name: "paddingRight", type: "number", description: "Right padding", required: false }
    ],
    returns: "Created frame node ID"
  },
  {
    name: "create_text",
    description: "Create a text node",
    category: "creation",
    args: [
      { name: "text", type: "string", description: "Text content", required: true },
      { name: "fontSize", type: "number", description: "Font size", required: false, default: 16 },
      { name: "fontWeight", type: "number", description: "Font weight (100-900)", required: false },
      { name: "fontFamily", type: "string", description: "Font family", required: false, default: "Inter" },
      { name: "color", type: "string", description: "Text color (hex)", required: false },
      { name: "x", type: "number", description: "X position", required: false },
      { name: "y", type: "number", description: "Y position", required: false }
    ],
    returns: "Created text node ID"
  },
  {
    name: "create_rectangle",
    description: "Create a rectangle or rounded rectangle",
    category: "creation",
    args: [
      { name: "name", type: "string", description: "Rectangle name", required: false },
      { name: "width", type: "number", description: "Width", required: false },
      { name: "height", type: "number", description: "Height", required: false },
      { name: "cornerRadius", type: "number", description: "Corner radius", required: false },
      { name: "fill", type: "string", description: "Fill color (hex)", required: false },
      { name: "x", type: "number", description: "X position", required: false },
      { name: "y", type: "number", description: "Y position", required: false }
    ],
    returns: "Created rectangle node ID"
  },
  {
    name: "create_icon",
    description: "Create an icon from SVG path",
    category: "creation",
    args: [
      { name: "svgPath", type: "string", description: "SVG path data", required: true },
      { name: "size", type: "number", description: "Icon size", required: false, default: 24 },
      { name: "color", type: "string", description: "Icon color (hex)", required: false }
    ],
    returns: "Created icon node ID"
  },

  // ═══════════════════════════════════════════════════════════════
  // STYLING
  // ═══════════════════════════════════════════════════════════════
  {
    name: "set_fill",
    description: "Set fill color on a node",
    category: "styling",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "color", type: "string", description: "Fill color (hex or semantic)", required: true },
      { name: "opacity", type: "number", description: "Opacity 0-1", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_stroke",
    description: "Set stroke on a node",
    category: "styling",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "color", type: "string", description: "Stroke color (hex)", required: true },
      { name: "width", type: "number", description: "Stroke weight", required: false, default: 1 }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_effects",
    description: "Add drop shadow or other effects",
    category: "styling",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "type", type: "string", description: "Effect type: DROP_SHADOW, INNER_SHADOW, LAYER_BLUR, BACKGROUND_BLUR", required: true },
      { name: "color", type: "string", description: "Shadow color (hex)", required: false },
      { name: "offsetX", type: "number", description: "Shadow offset X", required: false, default: 0 },
      { name: "offsetY", type: "number", description: "Shadow offset Y", required: false, default: 4 },
      { name: "blur", type: "number", description: "Blur radius", required: false, default: 8 },
      { name: "spread", type: "number", description: "Shadow spread", required: false, default: 0 }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_corner_radius",
    description: "Set corner radius on a node",
    category: "styling",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "radius", type: "number", description: "Corner radius for all corners", required: false },
      { name: "topLeft", type: "number", description: "Top left radius", required: false },
      { name: "topRight", type: "number", description: "Top right radius", required: false },
      { name: "bottomLeft", type: "number", description: "Bottom left radius", required: false },
      { name: "bottomRight", type: "number", description: "Bottom right radius", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_opacity",
    description: "Set opacity on a node",
    category: "styling",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "opacity", type: "number", description: "Opacity 0-1", required: true }
    ],
    returns: "Success confirmation"
  },

  // ═══════════════════════════════════════════════════════════════
  // LAYOUT
  // ═══════════════════════════════════════════════════════════════
  {
    name: "set_layout_mode",
    description: "Set auto-layout mode on a frame",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Frame node ID", required: true },
      { name: "mode", type: "string", description: "NONE, HORIZONTAL, VERTICAL", required: true }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_padding",
    description: "Set padding on auto-layout frame",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Frame node ID", required: true },
      { name: "top", type: "number", description: "Top padding", required: false },
      { name: "right", type: "number", description: "Right padding", required: false },
      { name: "bottom", type: "number", description: "Bottom padding", required: false },
      { name: "left", type: "number", description: "Left padding", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_item_spacing",
    description: "Set spacing between items in auto-layout",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Frame node ID", required: true },
      { name: "spacing", type: "number", description: "Spacing in pixels", required: true }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_axis_align",
    description: "Set primary and counter axis alignment",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Frame node ID", required: true },
      { name: "primary", type: "string", description: "Primary: MIN, CENTER, MAX, SPACE_BETWEEN", required: false },
      { name: "counter", type: "string", description: "Counter: MIN, CENTER, MAX, BASELINE", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_sizing",
    description: "Set horizontal and vertical sizing mode",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Frame node ID", required: true },
      { name: "horizontal", type: "string", description: "Horizontal: FIXED, HUG, FILL", required: false },
      { name: "vertical", type: "string", description: "Vertical: FIXED, HUG, FILL", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_dimensions",
    description: "Set width and height on a node",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "width", type: "number", description: "Width in pixels", required: false },
      { name: "height", type: "number", description: "Height in pixels", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "set_position",
    description: "Set X and Y position on a node",
    category: "layout",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "x", type: "number", description: "X position", required: false },
      { name: "y", type: "number", description: "Y position", required: false }
    ],
    returns: "Success confirmation"
  },

  // ═══════════════════════════════════════════════════════════════
  // ORGANIZATION
  // ═══════════════════════════════════════════════════════════════
  {
    name: "add_child",
    description: "Add a node as child of a frame",
    category: "organization",
    args: [
      { name: "parentId", type: "string", description: "Parent frame ID", required: true },
      { name: "childId", type: "string", description: "Child node ID to add", required: true },
      { name: "index", type: "number", description: "Position in children array", required: false }
    ],
    returns: "Success confirmation"
  },
  {
    name: "remove_child",
    description: "Remove a child from a frame",
    category: "organization",
    args: [
      { name: "parentId", type: "string", description: "Parent frame ID", required: true },
      { name: "childId", type: "string", description: "Child node ID to remove", required: true }
    ],
    returns: "Success confirmation"
  },
  {
    name: "rename_node",
    description: "Rename a node",
    category: "organization",
    args: [
      { name: "nodeId", type: "string", description: "Node ID", required: true },
      { name: "name", type: "string", description: "New name", required: true }
    ],
    returns: "Success confirmation"
  },
  {
    name: "delete_node",
    description: "Delete a node from the document",
    category: "organization",
    args: [
      { name: "nodeId", type: "string", description: "Node ID to delete", required: true }
    ],
    returns: "Success confirmation"
  },
  {
    name: "duplicate_node",
    description: "Duplicate a node",
    category: "organization",
    args: [
      { name: "nodeId", type: "string", description: "Node ID to duplicate", required: true },
      { name: "offsetX", type: "number", description: "X offset for copy", required: false, default: 20 },
      { name: "offsetY", type: "number", description: "Y offset for copy", required: false, default: 20 }
    ],
    returns: "Created duplicate node ID"
  },

  // ═══════════════════════════════════════════════════════════════
  // UTILITIES
  // ═══════════════════════════════════════════════════════════════
  {
    name: "wait",
    description: "Wait for specified milliseconds (for visual progress)",
    category: "document",
    args: [
      { name: "ms", type: "number", description: "Milliseconds to wait", required: true }
    ],
    returns: "Success after delay"
  },
  {
    name: "done",
    description: "Signal completion of design generation",
    category: "document",
    args: [
      { name: "summary", type: "string", description: "Summary of what was created", required: false }
    ],
    returns: "Final summary"
  }
]

export function getToolsByCategory(category: ToolCategory): ToolDefinition[] {
  return FIGMA_TOOLS.filter(t => t.category === category)
}

export function getToolSchemaForAI(): string {
  return FIGMA_TOOLS.map(t => {
    const args = t.args.map(a => 
      `  - ${a.name}${a.required ? '' : '?'}: ${a.type} - ${a.description}${a.default !== undefined ? ` (default: ${JSON.stringify(a.default)})` : ''}`
    ).join('\n')
    
    return `## ${t.name}
${t.description}

Arguments:
${args}

Returns: ${t.returns}
`
  }).join('\n')
}

export function getToolNames(): string[] {
  return FIGMA_TOOLS.map(t => t.name)
}
