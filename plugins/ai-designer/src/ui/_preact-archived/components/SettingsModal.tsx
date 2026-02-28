import { useState } from "preact/hooks";
import type { AIMode } from "../services/ai-service";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiKeys: Record<AIMode, string>;
  onSave: (keys: Record<AIMode, string>) => void;
}

export function SettingsModal({ isOpen, onClose, apiKeys, onSave }: SettingsModalProps) {
  const [keys, setKeys] = useState(apiKeys);
  const [showGlm, setShowGlm] = useState(false);
  const [showKimi, setShowKimi] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(keys);
  };

  const handleCancel = () => {
    onClose();
  };

  return (
    <div class="modal-overlay" onClick={handleCancel}>
      <div class="modal-content" onClick={(e) => e.stopPropagation()}>
        <div class="modal-header">
          <h2>Settings</h2>
          <button type="button" class="close-btn" onClick={handleCancel}>X</button>
        </div>

        <div class="modal-body">
          <h3>API Keys (Free Unlimited)</h3>
          <p class="settings-hint">
            Your API keys are stored locally.
          </p>

          <div class="api-key-list">
            <div class="api-key-item">
              <label>
                <span class="api-name">Z.AI (GLM-4.7)</span>
              </label>
              <div class="input-group">
                <input
                  type={showGlm ? "text" : "password"}
                  value={keys.glm}
                  onInput={(e) => setKeys({ ...keys, glm: (e.target as HTMLInputElement).value })}
                  placeholder="zai-..."
                />
                <button 
                  type="button"
                  class="toggle-visibility" 
                  onClick={() => setShowGlm(!showGlm)}
                >
                  {showGlm ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div class="api-key-item">
              <label>
                <span class="api-name">NVIDIA NIM (Kimi 2.5)</span>
              </label>
              <div class="input-group">
                <input
                  type={showKimi ? "text" : "password"}
                  value={keys.kimi}
                  onInput={(e) => setKeys({ ...keys, kimi: (e.target as HTMLInputElement).value })}
                  placeholder="nvapi-..."
                />
                <button 
                  type="button"
                  class="toggle-visibility" 
                  onClick={() => setShowKimi(!showKimi)}
                >
                  {showKimi ? "Hide" : "Show"}
                </button>
              </div>
            </div>
          </div>

          <div class="about-section">
            <p><strong>AI Designer</strong> v0.1.0</p>
            <p>Free unlimited AI design generation.</p>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn-secondary" onClick={handleCancel}>
            Cancel
          </button>
          <button type="button" class="btn-primary" onClick={handleSave}>
            Save Keys
          </button>
        </div>
      </div>
    </div>
  );
}
