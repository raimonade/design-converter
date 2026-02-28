import { TOOL_CATEGORIES, type ToolCategory } from './tool-schema'

export interface ToolResult {
  success: boolean
  data?: unknown
  error?: string
  nodeId?: string
}

export interface ExecutionContext {
  variables: Map<string, string>
  components: Map<string, string>
  frames: Map<string, string>
  errors: string[]
  created: string[]
}

let context: ExecutionContext = {
  variables: new Map(),
  components: new Map(),
  frames: new Map(),
  errors: [],
  created: []
}

function resetContext() {
  context = {
    variables: new Map(),
    components: new Map(),
    frames: new Map(),
    errors: [],
    created: []
  }
}

function parseColor(color: string): { r: number; g: number; b: number; a: number } {
  if (color.startsWith('#')) {
    const hex = color.slice(1)
    const fullHex = hex.length === 3 
      ? hex.split('').map(c => c + c).join('')
      : hex
    return {
      r: parseInt(fullHex.slice(0, 2), 16) / 255,
      g: parseInt(fullHex.slice(2, 4), 16) / 255,
      b: parseInt(fullHex.slice(4, 6), 16) / 255,
      a: 1
    }
  }
  return { r: 1, g: 1, b: 1, a: 1 }
}

async function loadFont(family: string = 'Inter', style: string = 'Regular') {
  try {
    await figma.loadFontAsync({ family, style })
  } catch (e) {
    console.log('Font load error:', e)
  }
}

export async function executeTool(
  toolName: string, 
  args: Record<string, unknown>
): Promise<ToolResult> {
  console.log('Executing tool:', toolName, args)
  
  try {
    switch (toolName) {
      case 'create_variable_collection': {
        const name = args.name as string
        const collection = figma.variables.createVariableCollection(name)
        collection.addMode('Dark')
        return { success: true, data: { id: collection.id, modes: collection.modes.map(m => ({ id: m.modeId, name: m.name })) } }
      }
      
      case 'create_color_variable': {
        const name = args.name as string
        const collectionName = args.collection as string
        const lightColor = parseColor(args.light as string)
        const darkColor = args.dark ? parseColor(args.dark as string) : lightColor
        
        const collections = (figma.variables as any).getLocalVariableCollections()
        const collection = collections.find((c: any) => c.name === collectionName)
        
        if (!collection) {
          return { success: false, error: `Collection ${collectionName} not found` }
        }
        
        const variable = figma.variables.createVariable(name, collection, 'COLOR')
        const lightModeId = collection.modes[0].modeId
        const darkModeId = collection.modes[1]?.modeId || lightModeId
        
        variable.setValueForMode(lightModeId, lightColor)
        variable.setValueForMode(darkModeId, darkColor)
        
        context.variables.set(name, variable.id)
        
        return { success: true, nodeId: variable.id, data: { id: variable.id, name } }
      }
      
      case 'bind_variable': {
        const nodeId = args.nodeId as string
        const property = args.property as string
        const variableId = args.variableId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const variable = figma.variables.getVariableById(variableId)
        if (!variable) return { success: false, error: 'Variable not found' }
        
        const nodeAny = node as any
        if (property === 'fill' && nodeAny.fills) {
          nodeAny.fills = [{
            type: 'SOLID',
            color: { r: 0, g: 0, b: 0 },
            boundVariables: { color: { type: 'VARIABLE_ALIAS', id: variableId } }
          }]
        }
        
        return { success: true }
      }
      
      case 'create_frame': {
        const name = args.name as string
        const frame = figma.createFrame() as any
        frame.name = name
        frame.layoutMode = (args.layoutMode as any) || 'VERTICAL'
        
        if (args.width) frame.width = args.width as number
        if (args.height) frame.height = args.height as number
        if (args.itemSpacing) frame.itemSpacing = args.itemSpacing as number
        
        const padding = args.padding as number
        if (padding) {
          frame.paddingTop = frame.paddingBottom = frame.paddingLeft = frame.paddingRight = padding
        }
        
        frame.fills = []
        
        context.frames.set(name, frame.id)
        context.created.push(`frame:${name}`)
        
        return { success: true, nodeId: frame.id, data: { id: frame.id, name } }
      }
      
      case 'create_text': {
        const text = args.text as string
        await loadFont()
        
        const textNode = figma.createText()
        textNode.characters = text
        
        if (args.fontSize) textNode.fontSize = args.fontSize as number
        if (args.fontWeight) {
          const weight = args.fontWeight as number
          textNode.fontName = { family: 'Inter', style: weight >= 700 ? 'Bold' : weight >= 500 ? 'Medium' : 'Regular' }
        }
        
        if (args.color) {
          textNode.fills = [{ type: 'SOLID', color: parseColor(args.color as string) }]
        }
        
        if (args.x) textNode.x = args.x as number
        if (args.y) textNode.y = args.y as number
        
        context.created.push(`text:${text.substring(0, 20)}`)
        
        return { success: true, nodeId: textNode.id, data: { id: textNode.id, text } }
      }
      
      case 'create_rectangle': {
        const rect = figma.createRectangle() as any
        rect.name = (args.name as string) || 'Rectangle'
        
        if (args.width) rect.width = args.width as number
        if (args.height) rect.height = args.height as number
        if (args.cornerRadius) rect.cornerRadius = args.cornerRadius as number
        if (args.fill) rect.fills = [{ type: 'SOLID', color: parseColor(args.fill as string) }]
        if (args.x) rect.x = args.x as number
        if (args.y) rect.y = args.y as number
        
        context.created.push(`rect:${rect.name}`)
        
        return { success: true, nodeId: rect.id, data: { id: rect.id, name: rect.name } }
      }
      
      case 'set_fill': {
        const nodeId = args.nodeId as string
        const color = args.color as string
        const opacity = args.opacity as number | undefined
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        
        if (color.startsWith('$')) {
          const varName = color.slice(1)
          const varId = context.variables.get(varName)
          if (varId) {
            nodeAny.fills = [{
              type: 'SOLID',
              color: { r: 0, g: 0, b: 0 },
              opacity,
              boundVariables: { color: { type: 'VARIABLE_ALIAS', id: varId } }
            }]
          }
        } else {
          nodeAny.fills = [{
            type: 'SOLID',
            color: parseColor(color),
            opacity
          }]
        }
        
        return { success: true }
      }
      
      case 'set_stroke': {
        const nodeId = args.nodeId as string
        const color = args.color as string
        const width = (args.width as number) || 1
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        nodeAny.strokes = [{ type: 'SOLID', color: parseColor(color) }]
        nodeAny.strokeWeight = width
        
        return { success: true }
      }
      
      case 'set_effects': {
        const nodeId = args.nodeId as string
        const type = args.type as string
        const color = args.color ? parseColor(args.color as string) : { r: 0, g: 0, b: 0, a: 0.25 }
        const offsetX = (args.offsetX as number) || 0
        const offsetY = (args.offsetY as number) || 4
        const blur = (args.blur as number) || 8
        const spread = (args.spread as number) || 0
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        nodeAny.effects = [{
          type,
          color,
          offset: { x: offsetX, y: offsetY },
          radius: blur,
          spread,
          visible: true,
          blendMode: 'NORMAL'
        }]
        
        return { success: true }
      }
      
      case 'set_corner_radius': {
        const nodeId = args.nodeId as string
        const radius = args.radius as number
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        if (radius !== undefined) {
          nodeAny.cornerRadius = radius
        } else {
          if (args.topLeft) nodeAny.topLeftRadius = args.topLeft as number
          if (args.topRight) nodeAny.topRightRadius = args.topRight as number
          if (args.bottomLeft) nodeAny.bottomLeftRadius = args.bottomLeft as number
          if (args.bottomRight) nodeAny.bottomRightRadius = args.bottomRight as number
        }
        
        return { success: true }
      }
      
      case 'set_layout_mode': {
        const nodeId = args.nodeId as string
        const mode = args.mode as any
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        nodeAny.layoutMode = mode
        
        return { success: true }
      }
      
      case 'set_padding': {
        const nodeId = args.nodeId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        if (args.top !== undefined) nodeAny.paddingTop = args.top as number
        if (args.right !== undefined) nodeAny.paddingRight = args.right as number
        if (args.bottom !== undefined) nodeAny.paddingBottom = args.bottom as number
        if (args.left !== undefined) nodeAny.paddingLeft = args.left as number
        
        return { success: true }
      }
      
      case 'set_item_spacing': {
        const nodeId = args.nodeId as string
        const spacing = args.spacing as number
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        nodeAny.itemSpacing = spacing
        
        return { success: true }
      }
      
      case 'set_axis_align': {
        const nodeId = args.nodeId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        if (args.primary) nodeAny.primaryAxisAlignItems = args.primary
        if (args.counter) nodeAny.counterAxisAlignItems = args.counter
        
        return { success: true }
      }
      
      case 'set_sizing': {
        const nodeId = args.nodeId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        if (args.horizontal) nodeAny.layoutSizingHorizontal = args.horizontal
        if (args.vertical) nodeAny.layoutSizingVertical = args.vertical
        
        return { success: true }
      }
      
      case 'set_dimensions': {
        const nodeId = args.nodeId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        if (args.width !== undefined) nodeAny.width = args.width as number
        if (args.height !== undefined) nodeAny.height = args.height as number
        
        return { success: true }
      }
      
      case 'set_position': {
        const nodeId = args.nodeId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        if (args.x !== undefined) nodeAny.x = args.x as number
        if (args.y !== undefined) nodeAny.y = args.y as number
        
        return { success: true }
      }
      
      case 'add_child': {
        const parentId = args.parentId as string
        const childId = args.childId as string
        
        const parent = await figma.getNodeByIdAsync(parentId)
        const child = await figma.getNodeByIdAsync(childId)
        
        if (!parent || !child) return { success: false, error: 'Parent or child not found' }
        
        const parentAny = parent as any
        if (args.index !== undefined) {
          parentAny.insertChild(args.index as number, child)
        } else {
          parentAny.appendChild(child)
        }
        
        return { success: true }
      }
      
      case 'create_component': {
        const name = args.name as string
        const fromFrameId = args.fromFrame as string
        const pageName = args.page as string
        
        let frame: any
        if (fromFrameId) {
          frame = await figma.getNodeByIdAsync(fromFrameId)
        }
        
        if (!frame) {
          frame = figma.createFrame()
          frame.name = name + '_temp'
          frame.layoutMode = 'VERTICAL'
          frame.fills = []
        }
        
        const component = figma.createComponentFromNode(frame)
        component.name = name
        
        const pages = figma.root.children
        let targetPage = pages.find(p => p.name === pageName)
        if (!targetPage) {
          targetPage = figma.createPage()
          targetPage.name = pageName
        }
        
        targetPage.appendChild(component)
        
        context.components.set(name, component.id)
        context.created.push(`component:${name}`)
        
        return { success: true, nodeId: component.id, data: { id: component.id, name } }
      }
      
      case 'create_instance': {
        const componentId = args.componentId as string
        
        const component = await figma.getNodeByIdAsync(componentId)
        if (!component || component.type !== 'COMPONENT') {
          return { success: false, error: 'Component not found' }
        }
        
        const instance = (component as any).createInstance()
        
        if (args.x !== undefined) instance.x = args.x as number
        if (args.y !== undefined) instance.y = args.y as number
        
        context.created.push(`instance:${component.name}`)
        
        return { success: true, nodeId: instance.id, data: { id: instance.id } }
      }
      
      case 'create_component_property': {
        const componentId = args.componentId as string
        const propName = args.name as string
        const propType = args.type as any
        const defaultValue = args.defaultValue as string
        
        const component = await figma.getNodeByIdAsync(componentId)
        if (!component || component.type !== 'COMPONENT') {
          return { success: false, error: 'Component not found' }
        }
        
        try {
          (component as any).addComponentProperty(propName, propType, defaultValue)
          return { success: true }
        } catch (e) {
          return { success: false, error: (e as Error).message }
        }
      }
      
      case 'rename_node': {
        const nodeId = args.nodeId as string
        const name = args.name as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        node.name = name
        
        return { success: true }
      }
      
      case 'delete_node': {
        const nodeId = args.nodeId as string
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        node.remove()
        
        return { success: true }
      }
      
      case 'duplicate_node': {
        const nodeId = args.nodeId as string
        const offsetX = (args.offsetX as number) || 20
        const offsetY = (args.offsetY as number) || 20
        
        const node = await figma.getNodeByIdAsync(nodeId)
        if (!node) return { success: false, error: 'Node not found' }
        
        const nodeAny = node as any
        const clone = nodeAny.clone()
        clone.x += offsetX
        clone.y += offsetY
        
        return { success: true, nodeId: clone.id, data: { id: clone.id } }
      }
      
      case 'wait': {
        const ms = args.ms as number
        await new Promise(r => setTimeout(r, Math.min(ms, 2000)))
        return { success: true }
      }
      
      case 'done': {
        return { 
          success: true, 
          data: { 
            summary: args.summary || `Created: ${context.created.length} elements`,
            created: context.created,
            errors: context.errors
          } 
        }
      }
      
      default:
        return { success: false, error: `Unknown tool: ${toolName}` }
    }
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error'
    context.errors.push(`${toolName}: ${errorMsg}`)
    return { success: false, error: errorMsg }
  }
}

export async function executeBatch(operations: Array<{ tool: string; args: Record<string, unknown> }>): Promise<ToolResult[]> {
  const results: ToolResult[] = []
  
  for (const op of operations) {
    const result = await executeTool(op.tool, op.args)
    results.push(result)
    
    if (!result.success && result.error && !result.error.includes('not found')) {
      console.log('Tool error:', result.error)
    }
  }
  
  return results
}

export function getContext(): ExecutionContext {
  return context
}

export { resetContext }
