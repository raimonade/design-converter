// AI Designer Plugin - Main Thread
import { createDesignFromSpec, createTokensFromSpec } from './design-generator';
import { DESIGN_SYSTEM_PROMPT } from './system-prompt';

figma.showUI(__html__, { 
  width: 450, 
  height: 750,
  title: "AI Designer"
});

const VALID_MESSAGE_TYPES = [
  'load-keys', 'save-keys', 'generate-design', 
  'check-services', 'run-services', 'log', 'close'
];

function isValidMessage(msg: unknown): msg is { type: string; [key: string]: unknown } {
  return typeof msg === 'object' && msg !== null && 
         'type' in msg && typeof (msg as { type: string }).type === 'string' &&
         VALID_MESSAGE_TYPES.includes((msg as { type: string }).type);
}

figma.ui.onmessage = async (message) => {
  if (!isValidMessage(message)) {
    console.error('Invalid message received:', message);
    return;
  }
  console.log('Plugin received message:', message.type);

  switch (message.type) {
    case "load-keys":
      await handleLoadKeys();
      break;
    
    case "save-keys":
      await handleSaveKeys(message.keys as { glm: string; kimi: string });
      break;
    
    case "generate-design":
      await handleGenerateDesign(message as unknown as { prompt: string; mode: string; apiKey: string; requestId: string });
      break;
    
    case "check-services":
      await handleCheckServices();
      break;
    
    case "run-services":
      await handleRunServices();
      break;
    
    case "log":
      console.log('[UI]', message.message);
      break;
    
    case "close":
      figma.closePlugin();
      break;
  }
};

// Handle loading API keys from storage
async function handleLoadKeys() {
  try {
    const keys = await figma.clientStorage.getAsync('api-keys');
    figma.ui.postMessage({ type: 'keys-loaded', keys: keys || { glm: '', kimi: '' } });
  } catch (error) {
    console.error('Failed to load keys:', error);
    figma.ui.postMessage({ type: 'keys-loaded', keys: { glm: '', kimi: '' } });
  }
}

// Handle saving API keys to storage
async function handleSaveKeys(keys: { glm: string; kimi: string }) {
  try {
    await figma.clientStorage.setAsync('api-keys', keys);
    figma.ui.postMessage({ type: 'keys-saved' });
    console.log('Keys saved successfully');
  } catch (error) {
    console.error('Failed to save keys:', error);
    figma.ui.postMessage({ type: 'keys-save-error', error: 'Failed to save' });
  }
}

async function handleCheckServices() {
  const status = {
    ollama: false,
    proxy: false,
    timestamp: Date.now()
  };

  try {
    const ollamaRes = await fetch('http://localhost:11434/api/tags', { method: 'GET' });
    status.ollama = ollamaRes.ok;
  } catch (e) {
    status.ollama = false;
  }

  try {
    const proxyRes = await fetch('http://localhost:11435/v1/models', { method: 'GET' });
    status.proxy = proxyRes.ok;
  } catch (e) {
    status.proxy = false;
  }

  figma.ui.postMessage({ type: 'services-status', status });
}

async function handleRunServices() {
  try {
    const res = await fetch('http://localhost:11436/start', { method: 'POST' });
    const data = await res.json();
    
    if (data.success && data.status) {
      figma.ui.postMessage({ type: 'services-started', status: data.status });
    } else {
      figma.ui.postMessage({ type: 'services-error', error: data.error || 'Failed to start services' });
    }
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Service manager not running. Start it first: node service-manager/server.js';
    figma.ui.postMessage({ type: 'services-error', error: errorMsg });
  }
}

// Handle design generation request
async function handleGenerateDesign(message: { prompt: string; mode: string; apiKey: string; requestId: string }) {
  const { prompt, mode, apiKey, requestId } = message;
  
  try {
    // Route local services (Ollama, Kimi) through service manager to avoid CORS
    const apiConfigs: Record<string, { url: string; model: string; useProxy: boolean }> = {
      glm: { 
        url: "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions", 
        model: "glm-5",
        useProxy: false
      },
      kimi: { 
        // Use service manager as proxy to avoid CORS
        url: "http://localhost:11436/proxy/kimi", 
        model: "moonshotai/kimi-k2-5",
        useProxy: true
      },
      minimax: { 
        // Use service manager as proxy to avoid CORS
        url: "http://localhost:11436/proxy/ollama", 
        model: "minimax-m2.5:cloud",
        useProxy: true
      }
    };

    const config = apiConfigs[mode] || apiConfigs.glm;

    figma.ui.postMessage({ type: "progress", requestId, progress: 10, message: "Analyzing design request..." });

    // Enhanced system prompt with design system knowledge
    const systemPrompt = DESIGN_SYSTEM_PROMPT;

    const requestBody = JSON.stringify({
      model: config.model,
      max_tokens: 16384,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: `Create a Figma design for: ${prompt}. Generate complete JSON with tokens and components.` }
      ]
    });

    figma.ui.postMessage({ type: "progress", requestId, progress: 30, message: "Connecting to AI..." });

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    let response: Response;
    try {
      response = await fetch(config.url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + apiKey
        },
        body: requestBody,
        signal: controller.signal
      });
    } catch (fetchError) {
      clearTimeout(timeoutId);
      if (fetchError instanceof Error && fetchError.name === 'AbortError') {
        figma.ui.postMessage({ type: "generation-error", requestId, error: "Request timed out after 2 minutes" });
      } else {
        figma.ui.postMessage({ type: "generation-error", requestId, error: fetchError instanceof Error ? fetchError.message : "Network error" });
      }
      return;
    }
    clearTimeout(timeoutId);

    figma.ui.postMessage({ type: "progress", requestId, progress: 60, message: "Processing AI response..." });

    const responseText = await response.text();
    console.log('API Response status:', response.status);
    console.log('API Response body:', responseText.substring(0, 500));

    if (!response.ok) {
      let errorMsg = "API error: " + response.status;
      try {
        const errData = JSON.parse(responseText);
        // NVIDIA NIM error format
        errorMsg = errData.error?.message || errData.message || errData.detail || errorMsg;
      } catch (e) {
        errorMsg = responseText.substring(0, 200);
      }
      figma.ui.postMessage({ type: "generation-error", requestId, error: errorMsg });
      return;
    }

    // Parse response
    let designSpec;
    try {
      const data = JSON.parse(responseText);
      const msg = data.choices?.[0]?.message || {};
      let content = msg.content || "";
      
      // Handle different reasoning field names (NVIDIA NIM, MiniMax/Ollama)
      if (!content && msg.reasoning_content) {
        content = msg.reasoning_content;
      }
      if (!content && msg.reasoning) {
        content = msg.reasoning;
      }
      
      console.log('AI Content length:', content.length);
      console.log('AI Content preview:', content.substring(0, 500));
      
      if (!content) {
        figma.ui.postMessage({ type: "generation-error", requestId, error: "Empty response from AI" });
        return;
      }
      
      content = content.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
      
      let jsonStr = content;
      const firstBrace = content.indexOf('{');
      if (firstBrace !== -1) {
        let braceCount = 0;
        let lastBrace = firstBrace;
        for (let i = firstBrace; i < content.length; i++) {
          if (content[i] === '{') braceCount++;
          else if (content[i] === '}') {
            braceCount--;
            if (braceCount === 0) {
              lastBrace = i;
              break;
            }
          }
        }
        jsonStr = content.substring(firstBrace, lastBrace + 1);
      }
      
      console.log('Extracted JSON length:', jsonStr.length);
      
      try {
        designSpec = JSON.parse(jsonStr);
      } catch (firstError) {
        console.log('Initial parse failed, attempting repair...');
        let openBraces = 0;
        let openBrackets = 0;
        let inString = false;
        let escapeNext = false;
        
        for (let i = 0; i < jsonStr.length; i++) {
          const c = jsonStr[i];
          if (escapeNext) { escapeNext = false; continue; }
          if (c === '\\') { escapeNext = true; continue; }
          if (c === '"') { inString = !inString; continue; }
          if (inString) continue;
          if (c === '{') openBraces++;
          else if (c === '}') openBraces--;
          else if (c === '[') openBrackets++;
          else if (c === ']') openBrackets--;
        }
        
        let repaired = jsonStr;
        if (inString) repaired += '"';
        while (openBrackets > 0) { repaired += ']'; openBrackets--; }
        while (openBraces > 0) { repaired += '}'; openBraces--; }
        
        console.log('Repaired JSON length:', repaired.length);
        designSpec = JSON.parse(repaired);
      }
    } catch (parseError) {
      console.error("Parse error:", parseError);
      figma.ui.postMessage({ type: "generation-error", requestId, error: "Failed to parse AI response. The AI may have generated incomplete JSON. Try again with a simpler prompt." });
      return;
    }

    figma.ui.postMessage({ type: "progress", requestId, progress: 80, message: "Creating design in Figma..." });

    // Create tokens if provided
    if (designSpec.tokens) {
      await createTokensFromSpec(designSpec.tokens);
    }

    // Create design
    const result = await createDesignFromSpec(designSpec);

    if (result.success) {
      figma.ui.postMessage({ 
        type: "generation-complete", 
        requestId, 
        message: result.message 
      });
      figma.notify("✅ Design created successfully!");
    } else {
      figma.ui.postMessage({ type: "generation-error", requestId, error: result.message });
    }

  } catch (error) {
    console.error("Generation error:", error);
    figma.ui.postMessage({ 
      type: "generation-error", 
      requestId, 
      error: error instanceof Error ? error.message : "Unknown error" 
    });
  }
}
