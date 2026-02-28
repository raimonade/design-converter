interface HistoryItem {
  id: string;
  prompt: string;
  mode: string;
  timestamp: Date;
  status: "pending" | "success" | "error";
}

interface HistoryPanelProps {
  items: HistoryItem[];
  onSelect: (item: HistoryItem) => void;
  onClose: () => void;
}

export function HistoryPanel({ items, onSelect, onClose }: HistoryPanelProps) {
  if (items.length === 0) {
    return (
      <div class="history-panel">
        <div class="history-header">
          <h3>History</h3>
          <button type="button" class="close-btn" onClick={onClose}>X</button>
        </div>
        <div class="history-empty">No designs yet</div>
      </div>
    );
  }

  return (
    <div class="history-panel">
      <div class="history-header">
        <h3>History</h3>
        <button type="button" class="close-btn" onClick={onClose}>X</button>
      </div>
      <div class="history-list">
        {items.map((item) => (
          <button
            type="button"
            key={item.id}
            class={"history-item status-" + item.status}
            onClick={() => onSelect(item)}
          >
            <span class="history-prompt">{item.prompt}</span>
            <span class="history-meta">
              {item.mode.toUpperCase()} - {formatTime(item.timestamp)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const mins = Math.floor(diff / 60000);
  
  if (mins < 1) return "just now";
  if (mins < 60) return mins + "m ago";
  
  const hours = Math.floor(mins / 60);
  if (hours < 24) return hours + "h ago";
  
  return date.toLocaleDateString();
}
