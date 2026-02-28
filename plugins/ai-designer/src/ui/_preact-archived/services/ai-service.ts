import type { DesignSpecification, FrameNodeSpec } from "../../shared/types/messages";

export type AIMode = "glm" | "kimi" | "auto";

// API configurations - using your free unlimited APIs
const API_CONFIGS = {
  glm: {
    url: "https://api.z.ai/api/paas/v4/chat/completions",
    model: "glm-4.7",
    name: "GLM-4.7 (Z.AI)",
    buildAuth: (key: string) => ["Authorization", `Bearer ${key}`]
  },
  kimi: {
    url: "https://integrate.api.nvidia.com/v1/chat/completions",
    model: "moonshotai/kimi-k2.5",
    name: "Kimi 2.5 (NVIDIA)",
    buildAuth: (key: string) => ["Authorization", `Bearer ${key}`]
  }
};

// System prompt for design generation
const SYSTEM_PROMPT = `You are an expert UI/UX designer AI that generates Figma-compatible design specifications.

When given a description, generate a JSON design specification with this exact structure:

{
  "version": "1.0",
  "root": {
    "id": "root-frame",
    "name": "Container",
    "type": "FRAME",
    "layoutMode": "VERTICAL",
    "primaryAxisSizingMode": "AUTO",
    "counterAxisSizingMode": "AUTO",
    "paddingTop": 24,
    "paddingBottom": 24,
    "paddingLeft": 24,
    "paddingRight": 24,
    "itemSpacing": 16,
    "cornerRadius": 12,
    "fills": [{ "type": "SOLID", "color": { "r": 1, "g": 1, "b": 1, "a": 1 } }],
    "children": [
      {
        "id": "header-text",
        "name": "Header",
        "type": "TEXT",
        "characters": "Welcome",
        "fontSize": 24,
        "fontWeight": 700,
        "fills": [{ "type": "SOLID", "color": { "r": 0.1, "g": 0.1, "b": 0.1, "a": 1 } }]
      },
      {
        "id": "button-frame",
        "name": "Button",
        "type": "FRAME",
        "layoutMode": "HORIZONTAL",
        "paddingTop": 12,
        "paddingBottom": 12,
        "paddingLeft": 24,
        "paddingRight": 24,
        "cornerRadius": 8,
        "fills": [{ "type": "SOLID", "color": { "r": 0.04, "g": 0.48, "b": 1, "a": 1 } }],
        "children": [
          {
            "id": "button-text",
            "name": "Label",
            "type": "TEXT",
            "characters": "Click me",
            "fontSize": 14,
            "fontWeight": 600,
            "fills": [{ "type": "SOLID", "color": { "r": 1, "g": 1, "b": 1, "a": 1 } }]
          }
        ]
      }
    ]
  }
}

DESIGN RULES:
1. Use semantic names (Container, Header, Button, Input, Card)
2. Colors: use 0-1 range (divide hex by 255)
3. Spacing: use multiples of 4 (4, 8, 12, 16, 24, 32)
4. Text: include fontFamily as "Inter"
5. Layout: prefer AUTO sizing for responsive designs
6. Always include fills array for backgrounds
7. For text nodes, always include characters, fontSize, fontWeight, and fills

NODE TYPES:
- FRAME: Container with layout (layoutMode, padding, itemSpacing)
- TEXT: Text content (characters, fontSize, fontWeight)
- RECTANGLE: Simple shapes (width, height, cornerRadius)

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanations.`;

// Generate design using selected AI model
export async function generateDesign(
  prompt: string,
  mode: AIMode,
  apiKeys: Record<AIMode, string>,
  onProgress: (progress: number) => void
): Promise<DesignSpecification> {
  // Determine which model to use
  const actualMode = mode === "auto" ? selectBestModel(prompt) : mode;
  const config = API_CONFIGS[actualMode];

  // Get API key
  const apiKey = apiKeys[actualMode];
  if (!apiKey) {
    throw new Error("API key not configured. Please add your " + config.name + " API key in Settings.");
  }

  onProgress(10);

  const [authHeader, authValue] = config.buildAuth(apiKey);

  const response = await fetch(config.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [authHeader]: authValue
    },
    body: JSON.stringify({
      model: config.model,
      max_tokens: 4096,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: prompt }
      ]
    })
  });

  onProgress(50);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error?.message || "API error: " + response.status);
  }

  const data = await response.json();
  onProgress(80);

  // Extract content
  const content = data.choices?.[0]?.message?.content;

  if (!content) {
    throw new Error("No content received from AI");
  }

  // Parse the design specification
  const design = parseDesignSpec(content);
  onProgress(100);

  return design;
}

// Parse AI response into design specification
function parseDesignSpec(content: string): DesignSpecification {
  // Try to extract JSON from the response
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error("No valid JSON found in AI response");
  }

  try {
    const spec = JSON.parse(jsonMatch[0]) as DesignSpecification;
    
    // Validate required fields
    if (!spec.root || !spec.root.type) {
      throw new Error("Invalid design specification: missing root node");
    }

    // Ensure IDs are present
    ensureIds(spec.root);

    return spec;
  } catch (error) {
    throw new Error("Failed to parse design: " + (error instanceof Error ? error.message : "Unknown error"));
  }
}

// Ensure all nodes have unique IDs
function ensureIds(node: FrameNodeSpec, prefix = "node"): void {
  if (!node.id) {
    node.id = prefix + "-" + Math.random().toString(36).substring(2, 9);
  }
  if (node.children) {
    node.children.forEach((child, i) => ensureIds(child, node.id + "-" + i));
  }
}

// Select best model based on prompt characteristics
function selectBestModel(prompt: string): AIMode {
  const lowerPrompt = prompt.toLowerCase();
  
  // Complex UI descriptions -> GLM-4.7 (better structured output)
  if (lowerPrompt.includes("complex") || lowerPrompt.includes("detailed") || prompt.length > 200) {
    return "glm";
  }
  
  // Simple requests -> Kimi (faster)
  if (lowerPrompt.includes("simple") || lowerPrompt.includes("quick") || prompt.length < 50) {
    return "kimi";
  }
  
  // Default to GLM-4.7 for best quality
  return "glm";
}

export { SYSTEM_PROMPT, API_CONFIGS };
