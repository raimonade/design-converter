interface ColorSpec { r: number; g: number; b: number; a?: number }
interface FillSpec { 
  type: string
  color?: ColorSpec
  opacity?: number
  semanticColor?: string
}
interface StrokeSpec { 
  type: string
  color?: ColorSpec
  width?: number
  semanticColor?: string
}
interface ShadowSpec { 
  type: "DROP_SHADOW" | "INNER_SHADOW" | "LAYER_BLUR" | "BACKGROUND_BLUR"
  color?: ColorSpec
  offset?: { x: number; y: number }
  radius?: number
  spread?: number
  visible?: boolean
  blendMode?: "NORMAL" | "MULTIPLY" | "SCREEN" | "OVERLAY"
}
interface TextSpec { 
  type: "TEXT"
  characters: string
  fontSize?: number
  fontWeight?: number
  fontFamily?: string
  lineHeight?: number
  letterSpacing?: number
  textAlignHorizontal?: "LEFT" | "CENTER" | "RIGHT" | "JUSTIFIED"
  color?: ColorSpec
  semanticColor?: string
}
interface ComponentPropertySpec {
  type: "BOOLEAN" | "TEXT" | "INSTANCE_SWAP" | "VARIANT"
  name: string
  defaultValue: string | boolean
  variantOptions?: string[]
}
interface FrameSpec {
  type: "FRAME"
  name: string
  layoutMode?: "HORIZONTAL" | "VERTICAL" | "NONE"
  width?: number | "hug" | "fill"
  height?: number | "hug" | "fill"
  itemSpacing?: number
  paddingLeft?: number
  paddingRight?: number
  paddingTop?: number
  paddingBottom?: number
  cornerRadius?: number | { topLeft: number; topRight: number; bottomRight: number; bottomLeft: number }
  fills?: FillSpec[]
  strokes?: StrokeSpec[]
  effects?: ShadowSpec[]
  primaryAxisAlignItems?: "MIN" | "CENTER" | "MAX" | "SPACE_BETWEEN"
  counterAxisAlignItems?: "MIN" | "CENTER" | "MAX" | "BASELINE"
  primaryAxisSizingMode?: "AUTO" | "FIXED"
  counterAxisSizingMode?: "AUTO" | "FIXED"
  layoutSizingHorizontal?: "FIXED" | "HUG" | "FILL"
  layoutSizingVertical?: "FIXED" | "HUG" | "FILL"
  opacity?: number
  children?: (FrameSpec | TextSpec)[]
  componentProperties?: ComponentPropertySpec[]
  variantName?: string
  atomicLevel?: "atom" | "molecule" | "organism" | "template"
}
interface ComponentVariantSpec {
  componentName: string
  description?: string
  variants: FrameSpec[]
  atomicLevel?: "atom" | "molecule" | "organism" | "template"
}
interface DesignSpec {
  version: string
  tokens?: Record<string, Record<string, unknown>>
  semantics?: {
    primitives?: Record<string, Record<string, unknown>>
    semantics?: Record<string, Record<string, unknown>>
  }
  root: FrameSpec | ComponentVariantSpec
}

let semanticVariables: Map<string, Variable> = new Map()
let variableCollection: VariableCollection | null = null
let atomsPage: PageNode | null = null
let moleculesPage: PageNode | null = null
let organismsPage: PageNode | null = null

function findVariable(name: string): Variable | undefined {
  return semanticVariables.get(name)
}

function registerVariable(name: string, variable: Variable): void {
  semanticVariables.set(name, variable)
}

async function loadFont(family: string, style: string): Promise<void> {
  try {
    await figma.loadFontAsync({ family, style })
  } catch (e) {
    console.log("Font load failed:", e)
  }
}

function parseColor(color: ColorSpec | undefined): { r: number; g: number; b: number } {
  if (!color) return { r: 1, g: 1, b: 1 }
  return {
    r: Math.max(0, Math.min(1, color.r || 0)),
    g: Math.max(0, Math.min(1, color.g || 0)),
    b: Math.max(0, Math.min(1, color.b || 0))
  }
}

async function ensurePages(): Promise<void> {
  const pages = figma.root.children
  
  atomsPage = pages.find(p => p.name === "Atoms") || figma.createPage()
  atomsPage.name = "Atoms"
  
  moleculesPage = pages.find(p => p.name === "Molecules") || figma.createPage()
  moleculesPage.name = "Molecules"
  
  organismsPage = pages.find(p => p.name === "Organisms") || figma.createPage()
  organismsPage.name = "Organisms"
}

function getTargetPage(name: string): PageNode {
  if (name.startsWith("atom/")) return atomsPage || figma.currentPage
  if (name.startsWith("molecule/")) return moleculesPage || figma.currentPage
  if (name.startsWith("organism/")) return organismsPage || figma.currentPage
  return figma.currentPage
}

async function createSemanticVariableCollection(semantics: { 
  primitives?: Record<string, Record<string, unknown>>
  semantics?: Record<string, Record<string, unknown>>
}): Promise<VariableCollection> {
  const collection = figma.variables.createVariableCollection("Design System")
  collection.addMode("Dark")
  
  const lightModeId = collection.modes[0].modeId
  const darkModeId = collection.modes[1].modeId
  
  const semanticColors = semantics.semantics?.colors || {}
  
  for (const [name, value] of Object.entries(semanticColors)) {
    if (typeof value === "object" && value !== null) {
      const c = value as { r?: number; g?: number; b?: number; a?: number }
      try {
        const variable = figma.variables.createVariable(name, collection, "COLOR")
        variable.setValueForMode(lightModeId, { ...parseColor(c as ColorSpec), a: c.a ?? 1 })
        variable.setValueForMode(darkModeId, getDarkSemanticValue(name, c))
        registerVariable(name, variable)
      } catch (e) {
        console.log("Semantic color error:", name, e)
      }
    }
  }
  
  variableCollection = collection
  return collection
}

function getDarkSemanticValue(name: string, lightColor: { r?: number; g?: number; b?: number; a?: number }): { r: number; g: number; b: number; a: number } {
  const n = name.toLowerCase()
  if (n.includes("background")) return { r: 0.09, g: 0.11, b: 0.15, a: 1 }
  if (n.includes("foreground")) return { r: 0.98, g: 0.98, b: 0.99, a: 1 }
  if (n.includes("border")) return { r: 0.29, g: 0.32, b: 0.37, a: 1 }
  if (n.includes("muted")) return { r: 0.22, g: 0.25, b: 0.29, a: 1 }
  return { r: lightColor.r ?? 0.5, g: lightColor.g ?? 0.5, b: lightColor.b ?? 0.5, a: lightColor.a ?? 1 }
}

function applyFillsToFillsArray(fills: FillSpec[] | undefined): ReadonlyArray<Paint> {
  if (!fills || fills.length === 0) {
    return [{ type: "SOLID", color: { r: 1, g: 1, b: 1 } }]
  }
  
  return fills.map(fill => {
    if (fill.semanticColor) {
      const variable = findVariable(fill.semanticColor)
      if (variable) {
        return {
          type: "SOLID" as const,
          color: { r: 0, g: 0, b: 0 },
          opacity: fill.opacity ?? 1,
          boundVariables: { color: { type: "VARIABLE_ALIAS" as const, id: variable.id } }
        }
      }
    }
    return {
      type: "SOLID" as const,
      color: parseColor(fill.color),
      opacity: fill.opacity ?? 1
    }
  })
}

function applyStrokesToStrokesArray(strokes: StrokeSpec[] | undefined): ReadonlyArray<Paint> {
  if (!strokes || strokes.length === 0) return []
  
  return strokes.map(stroke => {
    if (stroke.semanticColor) {
      const variable = findVariable(stroke.semanticColor)
      if (variable) {
        return {
          type: "SOLID" as const,
          color: { r: 0, g: 0, b: 0 },
          boundVariables: { color: { type: "VARIABLE_ALIAS" as const, id: variable.id } }
        }
      }
    }
    return {
      type: "SOLID" as const,
      color: parseColor(stroke.color)
    }
  })
}

async function createTextFromSpec(spec: TextSpec): Promise<TextNode> {
  await loadFont("Inter", "Regular")
  await loadFont("Inter", "Medium")
  await loadFont("Inter", "Bold")
  
  const text = figma.createText()
  text.characters = spec.characters || "Text"
  
  if (spec.fontSize) text.fontSize = spec.fontSize
  if (spec.fontWeight) {
    const style = spec.fontWeight >= 700 ? "Bold" : spec.fontWeight >= 500 ? "Medium" : "Regular"
    text.fontName = { family: "Inter", style }
  }
  
  if (spec.semanticColor) {
    const variable = findVariable(spec.semanticColor)
    if (variable) {
      text.fills = [{ 
        type: "SOLID", 
        color: { r: 0, g: 0, b: 0 }, 
        boundVariables: { color: { type: "VARIABLE_ALIAS", id: variable.id } } 
      }]
    }
  } else if (spec.color) {
    text.fills = [{ type: "SOLID", color: parseColor(spec.color) }]
  }
  
  return text
}

async function createFrameFromSpec(spec: FrameSpec, componentMap?: Map<string, ComponentNode>): Promise<FrameNode> {
  const frame = figma.createFrame()
  
  frame.name = spec.name || "Frame"
  frame.layoutMode = spec.layoutMode || "VERTICAL"
  
  // Validate primaryAxisSizingMode (valid: "AUTO" | "FIXED")
  if (spec.primaryAxisSizingMode === "AUTO" || spec.primaryAxisSizingMode === "FIXED") {
    frame.primaryAxisSizingMode = spec.primaryAxisSizingMode
  }
  // Validate counterAxisSizingMode (valid: "AUTO" | "FIXED")
  if (spec.counterAxisSizingMode === "AUTO" || spec.counterAxisSizingMode === "FIXED") {
    frame.counterAxisSizingMode = spec.counterAxisSizingMode
  }
  // Handle layoutSizingHorizontal/Vertical (valid: "FIXED" | "HUG" | "FILL")
  if (spec.layoutSizingHorizontal === "FIXED" || spec.layoutSizingHorizontal === "HUG" || spec.layoutSizingHorizontal === "FILL") {
    frame.layoutSizingHorizontal = spec.layoutSizingHorizontal
  }
  if (spec.layoutSizingVertical === "FIXED" || spec.layoutSizingVertical === "HUG" || spec.layoutSizingVertical === "FILL") {
    frame.layoutSizingVertical = spec.layoutSizingVertical
  }
  
  const widthNum = typeof spec.width === "number" ? spec.width : undefined
  const heightNum = typeof spec.height === "number" ? spec.height : undefined
  
  if (widthNum && heightNum) {
    frame.resize(widthNum, heightNum)
  } else if (widthNum) {
    frame.resize(widthNum, frame.height)
  } else if (heightNum) {
    frame.resize(frame.width, heightNum)
  }
  
  frame.itemSpacing = spec.itemSpacing ?? 16
  frame.paddingLeft = spec.paddingLeft ?? 16
  frame.paddingRight = spec.paddingRight ?? 16
  frame.paddingTop = spec.paddingTop ?? 16
  frame.paddingBottom = spec.paddingBottom ?? 16
  
  if (spec.cornerRadius !== undefined) {
    if (typeof spec.cornerRadius === "number") {
      frame.cornerRadius = spec.cornerRadius
    } else {
      frame.topLeftRadius = spec.cornerRadius.topLeft
      frame.topRightRadius = spec.cornerRadius.topRight
      frame.bottomRightRadius = spec.cornerRadius.bottomRight
      frame.bottomLeftRadius = spec.cornerRadius.bottomLeft
    }
  }
  
  if (spec.effects && spec.effects.length > 0) {
    frame.effects = spec.effects.map(effect => {
      if (effect.type === "DROP_SHADOW" || effect.type === "INNER_SHADOW") {
        return {
          type: effect.type,
          color: effect.color ? { ...parseColor(effect.color), a: effect.color.a ?? 0.25 } : { r: 0, g: 0, b: 0, a: 0.25 },
          offset: effect.offset || { x: 0, y: 4 },
          radius: effect.radius ?? 8,
          spread: effect.spread ?? 0,
          visible: effect.visible ?? true,
          blendMode: "NORMAL" as const,
          showShadowBehindNode: true
        }
      }
      return {
        type: effect.type,
        radius: effect.radius ?? 8,
        visible: effect.visible ?? true
      }
    }) as Effect[]
  }
  
  frame.primaryAxisAlignItems = spec.primaryAxisAlignItems || "MIN"
  frame.counterAxisAlignItems = spec.counterAxisAlignItems || "MIN"
  
  frame.fills = applyFillsToFillsArray(spec.fills)
  frame.strokes = applyStrokesToStrokesArray(spec.strokes)
  
  if (spec.strokes && spec.strokes.length > 0 && spec.strokes[0].width) {
    frame.strokeWeight = spec.strokes[0].width
  }
  
  if (spec.children && spec.children.length > 0) {
    for (const childSpec of spec.children) {
      if (childSpec.type === "TEXT") {
        const textNode = await createTextFromSpec(childSpec as TextSpec)
        frame.appendChild(textNode)
      } else {
        const childFrameSpec = childSpec as FrameSpec
        const childFrame = await createFrameFromSpec(childFrameSpec, componentMap)
        
        const childNameLower = childFrameSpec.name?.toLowerCase() || ""
        const isCommonComponent = /^(button|input|textfield|checkbox|radio|badge|avatar|icon|label|header|footer|sidebar|nav|modal|dialog|card|list|item|row|col|column|row|divider|spacer|chip|tag|tab|tooltip|popover|dropdown|select|slider|toggle|switch)/.test(childNameLower)
        
        const hasAtomicPrefix = childFrameSpec.name && (
          childFrameSpec.name.startsWith("atom/") ||
          childFrameSpec.name.startsWith("molecule/") ||
          childFrameSpec.name.startsWith("organism/")
        )
        
        if (isCommonComponent || hasAtomicPrefix) {
          if (componentMap && componentMap.has(childFrameSpec.name || "")) {
            const comp = componentMap.get(childFrameSpec.name || "")
            if (comp) {
              const instance = comp.createInstance()
              instance.name = "instance:" + (childFrameSpec.name || "")
              frame.appendChild(instance)
            }
          } else {
            const component = figma.createComponentFromNode(childFrame)
            component.name = childFrameSpec.name || "Component"
            frame.appendChild(component)
          }
        } else {
          frame.appendChild(childFrame)
        }
      }
    }
  }
  
  return frame
}

function countChildren(node: FrameSpec): number {
  let count = 1
  if (node.children) {
    for (const child of node.children) {
      if (child.type === "FRAME") {
        count += countChildren(child as FrameSpec)
      } else {
        count += 1
      }
    }
  }
  return count
}

export async function createDesignFromSpec(spec: DesignSpec): Promise<{ success: boolean; message: string }> {
  try {
    console.log("Creating design:", JSON.stringify(spec, null, 2).substring(0, 2000))
    
    await loadFont("Inter", "Regular")
    await loadFont("Inter", "Medium")
    await loadFont("Inter", "Bold")
    
    await ensurePages()
    
    if (spec.semantics) {
      console.log("Creating semantic variables...")
      await createSemanticVariableCollection(spec.semantics)
    }
    
    if (spec.tokens) {
      console.log("Creating legacy tokens...")
      await createTokensFromSpec(spec.tokens)
    }
    
    if (!spec.root) {
      return { success: false, message: "No root element" }
    }
    
    const isVariantSpec = (root: any): root is ComponentVariantSpec => 'variants' in root && Array.isArray(root.variants)
    const isFrameSpec = (root: any): root is FrameSpec => 'type' in root && root.type === "FRAME"
    
    if (isVariantSpec(spec.root)) {
      const variants = spec.root.variants
      if (variants.length === 0) {
        return { success: false, message: "No variants provided" }
      }
      
      const componentNodes: ComponentNode[] = []
      const targetPage = getTargetPage(spec.root.componentName || "")
      
      for (const variantSpec of variants) {
        const frame = await createFrameFromSpec(variantSpec)
        const component = figma.createComponentFromNode(frame)
        component.name = variantSpec.variantName || variantSpec.name || "Variant"
        
        if (variantSpec.componentProperties) {
          for (const prop of variantSpec.componentProperties) {
            try {
              component.addComponentProperty(prop.name, prop.type, prop.defaultValue)
            } catch (e) {
              console.log("Property add failed:", e)
            }
          }
        }
        
        componentNodes.push(component)
      }
      
      const containerFrame = figma.createFrame()
      containerFrame.name = "temp"
      containerFrame.layoutMode = "HORIZONTAL"
      containerFrame.fills = []
      targetPage.appendChild(containerFrame)
      
      const componentSet = figma.combineAsVariants(componentNodes, containerFrame)
      componentSet.name = spec.root.componentName || "Component Set"
      if (spec.root.description) {
        componentSet.description = spec.root.description
      }
      
      figma.viewport.scrollAndZoomIntoView([componentSet])
      
      return { 
        success: true, 
        message: `Created component set "${componentSet.name}" with ${componentNodes.length} variants` 
      }
    }
    
    if (!isFrameSpec(spec.root)) {
      return { success: false, message: "Invalid root element type" }
    }
    
    // Two-pass: First collect all component definitions
    const componentDefs: FrameSpec[] = []
    const collectComponents = (node: FrameSpec) => {
      const name = node.name?.toLowerCase() || ""
      const hasAtomicPrefix = node.name && (
        node.name.startsWith("atom/") ||
        node.name.startsWith("molecule/") ||
        node.name.startsWith("organism/")
      )
      const isCommonComponent = /^(button|input|textfield|checkbox|radio|badge|avatar|icon|label|header|footer|sidebar|nav|modal|dialog|card|list|item|row|col|column|divider|spacer|chip|tag|tab|tooltip|popover|dropdown|select|slider|toggle|switch)/.test(name)
      
      if ((hasAtomicPrefix || isCommonComponent) && node.name) {
        componentDefs.push(node)
      }
      if (node.children) {
        for (const child of node.children) {
          if (child.type === "FRAME") {
            collectComponents(child as FrameSpec)
          }
        }
      }
    }
    collectComponents(spec.root)
    
    // Create all components on appropriate pages first
    const createdComponents: Map<string, ComponentNode> = new Map()
    for (const compDef of componentDefs) {
      const page = getTargetPage(compDef.name || "")
      const frame = await createFrameFromSpec(compDef)
      const component = figma.createComponentFromNode(frame)
      component.name = compDef.name || "Component"
      page.appendChild(component)
      createdComponents.set(compDef.name || "", component)
      console.log("Created component:", compDef.name)
    }
    
    // Now create the root with component instances
    const isComponent = spec.root.name && (
      spec.root.name.startsWith("atom/") ||
      spec.root.name.startsWith("molecule/") ||
      spec.root.name.startsWith("organism/")
    )
    
    const targetPage = getTargetPage(spec.root.name || "")
    
    // Modified createFrameFromSpec that uses instances
    const originalCreateFrame = createFrameFromSpec
    
    if (isComponent) {
      const frame = await createFrameFromSpec(spec.root, createdComponents)
      const component = figma.createComponentFromNode(frame)
      component.name = spec.root.name
      
      if (spec.root.componentProperties) {
        for (const prop of spec.root.componentProperties) {
          try {
            component.addComponentProperty(prop.name, prop.type, prop.defaultValue)
          } catch (e) {
            console.log("Property add failed:", e)
          }
        }
      }
      
      targetPage.appendChild(component)
      figma.viewport.scrollAndZoomIntoView([component])
      
      return { 
        success: true, 
        message: `Created component "${spec.root.name}" with ${createdComponents.size} child components` 
      }
    }
    
    const rootFrame = await createFrameFromSpec(spec.root, createdComponents)
    figma.currentPage.appendChild(rootFrame)
    figma.viewport.scrollAndZoomIntoView([rootFrame])
    
    return { 
      success: true, 
      message: `Created "${spec.root.name}" (${countChildren(spec.root)} elements)` 
    }
  } catch (error) {
    console.error("Error:", error)
    return { 
      success: false, 
      message: error instanceof Error ? error.message : "Unknown error"
    }
  }
}

export async function createTokensFromSpec(tokens: Record<string, Record<string, unknown>>): Promise<void> {
  if (!tokens || Object.keys(tokens).length === 0) return
  
  try {
    if (!variableCollection) {
      variableCollection = figma.variables.createVariableCollection("Design Tokens")
      variableCollection.addMode("Dark")
    }
    
    const modeId = variableCollection.modes[0].modeId
    
    if (tokens.colors) {
      for (const [name, value] of Object.entries(tokens.colors)) {
        if (typeof value === "object" && value !== null) {
          const c = value as { r?: number; g?: number; b?: number }
          const variable = figma.variables.createVariable(`color/${name}`, variableCollection, "COLOR")
          variable.setValueForMode(modeId, parseColor(c as ColorSpec))
        }
      }
    }
    
    if (tokens.spacing) {
      for (const [name, value] of Object.entries(tokens.spacing)) {
        if (typeof value === "number") {
          const variable = figma.variables.createVariable(`spacing/${name}`, variableCollection, "FLOAT")
          variable.setValueForMode(modeId, value)
        }
      }
    }
    
    if (tokens.radius) {
      for (const [name, value] of Object.entries(tokens.radius)) {
        if (typeof value === "number") {
          const variable = figma.variables.createVariable(`radius/${name}`, variableCollection, "FLOAT")
          variable.setValueForMode(modeId, value)
        }
      }
    }
  } catch (error) {
    console.error("Token error:", error)
  }
}
