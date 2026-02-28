// Message types between UI and plugin

export type AIMode = 'claude' | 'kimi' | 'openai' | 'auto';

export interface GenerateDesignMessage {
  type: 'generate-design';
  prompt: string;
  mode: AIMode;
  designContext?: DesignContext;
}

export interface DesignContext {
  colors: ColorToken[];
  textStyles: TextStyleToken[];
  components: ComponentInfo[];
}

export interface ColorToken {
  name: string;
  value: { r: number; g: number; b: number; a: number };
}

export interface TextStyleToken {
  name: string;
  fontSize: number;
  fontFamily: string;
  fontWeight: number;
}

export interface ComponentInfo {
  id: string;
  name: string;
  type: string;
}

// Streaming events
export interface StreamStartEvent {
  type: 'stream-start';
  requestId: string;
}

export interface StreamChunkEvent {
  type: 'stream-chunk';
  requestId: string;
  chunk: string;
}

export interface StreamProgressEvent {
  type: 'stream-progress';
  requestId: string;
  progress: number;
  message: string;
}

export interface StreamEndEvent {
  type: 'stream-end';
  requestId: string;
}

export interface DesignResultEvent {
  type: 'design-result';
  requestId: string;
  design: DesignSpecification;
}

export interface ErrorEvent {
  type: 'error';
  message: string;
  code?: string;
}

// Design specification (what AI generates)
export interface DesignSpecification {
  version: string;
  root: FrameNodeSpec;
  variables?: Record<string, { r: number; g: number; b: number; a: number }>;
}

export interface FrameNodeSpec {
  id: string;
  name: string;
  type: 'FRAME' | 'TEXT' | 'RECTANGLE' | 'COMPONENT' | 'INSTANCE';
  layoutMode?: 'NONE' | 'HORIZONTAL' | 'VERTICAL';
  primaryAxisSizingMode?: 'FIXED' | 'AUTO';
  counterAxisSizingMode?: 'FIXED' | 'AUTO';
  paddingLeft?: number;
  paddingRight?: number;
  paddingTop?: number;
  paddingBottom?: number;
  itemSpacing?: number;
  fills?: FillSpec[];
  strokes?: StrokeSpec[];
  strokeWeight?: number;
  cornerRadius?: number;
  width?: number;
  height?: number;
  opacity?: number;
  characters?: string;
  fontSize?: number;
  fontFamily?: string;
  fontWeight?: number;
  textAlignHorizontal?: 'LEFT' | 'CENTER' | 'RIGHT';
  textAlignVertical?: 'TOP' | 'CENTER' | 'BOTTOM';
  children?: FrameNodeSpec[];
  componentId?: string;
}

export interface FillSpec {
  type: 'SOLID' | 'GRADIENT_LINEAR' | 'IMAGE';
  color?: { r: number; g: number; b: number; a: number };
  opacity?: number;
}

export interface StrokeSpec {
  type: 'SOLID';
  color: { r: number; g: number; b: number; a: number };
}

export type PluginMessage = 
  | GenerateDesignMessage
  | StreamStartEvent
  | StreamChunkEvent  
  | StreamProgressEvent
  | StreamEndEvent
  | DesignResultEvent
  | ErrorEvent;

export type UIMessage =
  | GenerateDesignMessage
  | { type: 'cancel'; requestId: string }
  | { type: 'get-design-context' };
