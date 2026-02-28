import { useState, useCallback, useEffect } from "preact/hooks";
import { PromptInput } from "./components/PromptInput";
import { ModelSelector } from "./components/ModelSelector";
import { HistoryPanel } from "./components/HistoryPanel";
import { SettingsModal } from "./components/SettingsModal";
import { generateDesign, AIMode } from "./services/ai-service";
import type { DesignSpecification } from "../shared/types/messages";

interface HistoryItem {
  id: string;
  prompt: string;
  mode: AIMode;
  design?: DesignSpecification;
  timestamp: Date;
  status: "pending" | "success" | "error";
}

const STORAGE_KEY = "figma-ai-designer-keys";

export function App() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<AIMode>("glm");
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiKeys, setApiKeys] = useState<Record<AIMode, string>>({
    glm: "",
    kimi: "",
    auto: ""
  });

  // Load API keys from storage on mount
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setApiKeys(JSON.parse(stored));
      } catch {}
    }
  }, []);

  // Save API keys to storage
  const handleSaveKeys = useCallback((keys: Record<AIMode, string>) => {
    setApiKeys(keys);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
    setShowSettings(false);
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || isGenerating) return;

    const requestId = crypto.randomUUID();
    const historyItem: HistoryItem = {
      id: requestId,
      prompt,
      mode,
      timestamp: new Date(),
      status: "pending"
    };

    setHistory(prev => [historyItem, ...prev]);
    setIsGenerating(true);
    setError(null);
    setProgress(0);

    try {
      const actualMode = mode === "auto" ? "glm" : mode;
      if (!apiKeys[actualMode]) {
        throw new Error("Please add your " + actualMode.toUpperCase() + " API key in Settings");
      }

      parent.postMessage(
        { pluginMessage: { type: "generate-design", prompt, mode, requestId } },
        "*"
      );

      const design = await generateDesign(prompt, mode, apiKeys, (p) => {
        setProgress(p);
        parent.postMessage(
          { pluginMessage: { type: "stream-progress", requestId, progress: p } },
          "*"
        );
      });

      parent.postMessage(
        { pluginMessage: { type: "design-result", requestId, design } },
        "*"
      );

      setHistory(prev =>
        prev.map(item =>
          item.id === requestId
            ? { ...item, design, status: "success" }
            : item
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Generation failed";
      setError(errorMessage);
      setHistory(prev =>
        prev.map(item =>
          item.id === requestId ? { ...item, status: "error" } : item
        )
      );
    } finally {
      setIsGenerating(false);
      setProgress(0);
    }
  }, [prompt, mode, isGenerating, apiKeys]);

  const handleHistorySelect = useCallback((item: HistoryItem) => {
    setPrompt(item.prompt);
    setMode(item.mode);
    setShowHistory(false);
  }, []);

  const canGenerate = prompt.trim().length > 0 && !isGenerating;

  return (
    <div class="app">
      <header class="header">
        <h1 class="title">AI Designer</h1>
        <div class="header-actions">
          <button 
            type="button"
            class="icon-btn"
            onClick={() => setShowHistory(!showHistory)}
          >
            History
          </button>
          <button 
            type="button"
            class="icon-btn"
            onClick={() => setShowSettings(true)}
          >
            Settings
          </button>
        </div>
      </header>

      {showHistory && (
        <HistoryPanel
          items={history}
          onSelect={handleHistorySelect}
          onClose={() => setShowHistory(false)}
        />
      )}

      <main class="main">
        <ModelSelector
          mode={mode}
          onChange={setMode}
          disabled={isGenerating}
        />

        <textarea
          class="prompt-input"
          value={prompt}
          onInput={(e) => setPrompt((e.target as HTMLTextAreaElement).value)}
          placeholder="Describe your design... e.g., 'Create a login form'"
          disabled={isGenerating}
          rows={4}
        />

        {isGenerating && (
          <div class="progress-bar">
            <div class="progress-fill" style={{ width: progress + "%" }} />
            <span class="progress-text">{Math.round(progress)}%</span>
          </div>
        )}

        {error && (
          <div class="error-message">
            {error}
          </div>
        )}

        <button
          type="button"
          class="generate-btn"
          onClick={handleGenerate}
          disabled={!canGenerate}
        >
          {isGenerating ? "Generating..." : "Generate Design"}
        </button>
      </main>

      <footer class="footer">
        <span class="powered-by">Powered by {mode === "auto" ? "GLM-4.7" : mode.toUpperCase()}</span>
      </footer>

      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        apiKeys={apiKeys}
        onSave={handleSaveKeys}
      />
    </div>
  );
}
