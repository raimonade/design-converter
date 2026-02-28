import type { DesignSpecification } from "../../shared/types/messages";

interface PreviewPanelProps {
  design?: DesignSpecification;
}

export function PreviewPanel({ design }: PreviewPanelProps) {
  if (!design) {
    return (
      <div class="preview-panel preview-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <path d="M21 15l-5-5L5 21"/>
        </svg>
        <p>Your design will appear here</p>
      </div>
    );
  }

  return (
    <div class="preview-panel">
      <div class="preview-header">
        <h4>Preview</h4>
        <button class="preview-inspect">Inspect</button>
      </div>
      <div class="preview-content">
        {/* Design preview would go here */}
        <pre>{JSON.stringify(design.root, null, 2)}</pre>
      </div>
    </div>
  );
}
