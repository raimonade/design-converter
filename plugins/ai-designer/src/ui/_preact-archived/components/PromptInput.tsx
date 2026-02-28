interface PromptInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function PromptInput({ value, onChange, onSubmit, disabled, placeholder }: PromptInputProps) {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div class="prompt-input-container">
      <textarea
        class="prompt-input"
        value={value}
        onInput={(e) => onChange((e.target as HTMLTextAreaElement).value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={4}
      />
      <div class="prompt-hint">
        <kbd>⌘</kbd> + <kbd>Enter</kbd> to generate
      </div>
    </div>
  );
}
