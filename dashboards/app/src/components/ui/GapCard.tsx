import { cn } from '@/lib/utils';

type GapSeverity = 'critical' | 'important' | 'nice';

interface GapCardProps extends React.HTMLAttributes<HTMLDivElement> {
  id: string;
  title: string;
  severity: GapSeverity;
  children: React.ReactNode;
}

const severityStyles: Record<GapSeverity, { border: string; badge: string }> = {
  critical: {
    border: 'border-l-[var(--color-red)]',
    badge: 'bg-[var(--color-red-dim)] text-[var(--color-red)]',
  },
  important: {
    border: 'border-l-[var(--color-amber)]',
    badge: 'bg-[var(--color-amber-dim)] text-[var(--color-amber)]',
  },
  nice: {
    border: 'border-l-[var(--color-text-muted)]',
    badge: 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]',
  },
};

export function GapCard({
  id,
  title,
  severity,
  className,
  children,
  ...props
}: GapCardProps) {
  const styles = severityStyles[severity];

  return (
    <div
      className={cn(
        'p-5 my-4',
        'bg-[var(--color-bg-secondary)]',
        'border border-[var(--color-border)] border-l-[3px]',
        'rounded-[var(--radius-md)]',
        'transition-colors hover:border-[var(--color-border-subtle)]',
        styles.border,
        className
      )}
      {...props}
    >
      <div className="flex items-center gap-2.5 mb-2.5">
        <span
          className={cn(
            'font-mono text-[11px] font-medium px-1.5 py-0.5 rounded',
            styles.badge
          )}
        >
          {id}
        </span>
        <span className="font-[var(--font-heading)] text-base font-semibold text-[var(--color-heading)]">
          {title}
        </span>
      </div>
      <div className="text-[14.5px] text-[var(--color-text)] leading-relaxed">
        {children}
      </div>
    </div>
  );
}
