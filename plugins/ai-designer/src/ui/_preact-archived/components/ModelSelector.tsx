import type { AIMode } from "../services/ai-service";

interface ModelSelectorProps {
  mode: AIMode;
  onChange: (mode: AIMode) => void;
  disabled?: boolean;
}

const MODELS: { id: AIMode; name: string; description: string; badge?: string }[] = [
  { id: "glm", name: "GLM-4.7", description: "Best for complex UIs", badge: "Free" },
  { id: "kimi", name: "Kimi 2.5", description: "Fast & efficient", badge: "Free" },
  { id: "auto", name: "Auto", description: "Let AI choose" }
];

export function ModelSelector({ mode, onChange, disabled }: ModelSelectorProps) {
  return (
    <div class="model-selector">
      <label class="model-label">AI Model (Unlimited)</label>
      <div class="model-grid">
        {MODELS.map((model) => (
          <button
            type="button"
            key={model.id}
            class={"model-btn " + (mode === model.id ? "active" : "")}
            onClick={() => onChange(model.id)}
            disabled={disabled}
          >
            <span class="model-name">{model.name}</span>
            {model.badge && <span class="model-badge">{model.badge}</span>}
          </button>
        ))}
      </div>
    </div>
  );
}
