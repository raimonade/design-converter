import { useState, useRef, useCallback, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import { Check } from 'lucide-react';

interface IconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}

interface QuickActionProps {
  icon: ForwardRefExoticComponent<{ size?: number; className?: string } & RefAttributes<IconHandle>>;
  label: string;
  command: string;
  color: string;
  iconColorClass: string;
}

export function QuickAction({ icon: Icon, label, command, color, iconColorClass }: QuickActionProps) {
  const [copied, setCopied] = useState(false);
  const iconRef = useRef<IconHandle>(null);

  const handleClick = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleMouseEnter = useCallback(() => iconRef.current?.startAnimation(), []);
  const handleMouseLeave = useCallback(() => iconRef.current?.stopAnimation(), []);

  return (
    <button
      type="button"
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group text-left p-4 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] border-l-[3px] rounded-none rounded-r-[var(--radius-md)] transition-all duration-200 hover:border-[var(--color-border)] hover:bg-[var(--color-bg-tertiary)]/30 cursor-pointer"
      style={{ borderLeftColor: color }}
    >
      <div className="flex items-center gap-2.5 mb-2">
        <Icon ref={iconRef} size={18} className={`opacity-80 ${iconColorClass}`} />
        <span className="font-[family-name:var(--font-heading)] text-sm font-semibold text-[var(--color-heading)]">
          {label}
        </span>
        {copied && <Check className="w-3.5 h-3.5 text-[var(--color-accent)] ml-auto" />}
      </div>
      <div className="font-mono text-[11px] text-[var(--color-text-muted)] leading-relaxed flex items-center gap-1.5">
        <span className="text-[var(--color-text-muted)] select-none">$</span>
        <span className="truncate">{command}</span>
      </div>
    </button>
  );
}
