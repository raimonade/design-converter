import { useRef, useCallback, type ForwardRefExoticComponent, type RefAttributes } from 'react';

interface IconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}

interface MetricCardProps {
  icon: ForwardRefExoticComponent<{ size?: number; className?: string } & RefAttributes<IconHandle>>;
  value: string | number;
  label: string;
  color: string;
  iconColorClass: string;
  subValue?: string;
  barPercent?: number;
  barColor?: string;
}

export function MetricCard({ icon: Icon, value, label, color, iconColorClass, subValue, barPercent, barColor }: MetricCardProps) {
  const iconRef = useRef<IconHandle>(null);

  const handleMouseEnter = useCallback(() => iconRef.current?.startAnimation(), []);
  const handleMouseLeave = useCallback(() => iconRef.current?.stopAnimation(), []);

  return (
    <div
      className="group p-5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)] transition-all duration-200 hover:border-[rgba(52,211,153,0.3)] hover:shadow-[0_0_24px_rgba(52,211,153,0.06)]"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className="p-2 rounded-[var(--radius-sm)] transition-transform duration-200 group-hover:scale-110"
          style={{ background: `color-mix(in srgb, ${color} 12%, transparent)` }}
        >
          <Icon ref={iconRef} size={20} className={iconColorClass} />
        </div>
        {subValue && (
          <span className="font-mono text-[10px] text-[var(--color-text-muted)] mt-1">{subValue}</span>
        )}
      </div>
      <div
        className="text-[28px] font-bold font-[family-name:var(--font-heading)] leading-none mb-1"
        style={{ color }}
      >
        {value}
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] font-mono uppercase tracking-[0.12em]">
        {label}
      </div>
      {barPercent !== undefined && (
        <div className="mt-3 h-[3px] bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full animate-bar-fill"
            style={{
              width: `${barPercent}%`,
              background: barColor || color,
            }}
          />
        </div>
      )}
    </div>
  );
}
