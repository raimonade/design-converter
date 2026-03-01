import { cn } from '@/lib/utils';
import { AlertCircle, AlertTriangle, Info, Lightbulb } from 'lucide-react';

type CalloutVariant = 'default' | 'warning' | 'error' | 'info';

interface CalloutProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CalloutVariant;
  icon?: React.ReactNode;
  title?: string;
}

const variantStyles: Record<CalloutVariant, { border: string; bg: string; icon: React.ReactNode }> = {
  default: {
    border: 'border-l-[var(--color-accent)]',
    bg: 'bg-[var(--color-bg-tertiary)]',
    icon: <Info className="w-4 h-4 text-[var(--color-accent)]" />,
  },
  warning: {
    border: 'border-l-[var(--color-amber)]',
    bg: 'bg-[var(--color-bg-tertiary)]',
    icon: <AlertTriangle className="w-4 h-4 text-[var(--color-amber)]" />,
  },
  error: {
    border: 'border-l-[var(--color-red)]',
    bg: 'bg-[var(--color-bg-tertiary)]',
    icon: <AlertCircle className="w-4 h-4 text-[var(--color-red)]" />,
  },
  info: {
    border: 'border-l-[var(--color-blue)]',
    bg: 'bg-[var(--color-bg-tertiary)]',
    icon: <Lightbulb className="w-4 h-4 text-[var(--color-blue)]" />,
  },
};

export function Callout({
  variant = 'default',
  icon,
  title,
  className,
  children,
  ...props
}: CalloutProps) {
  const styles = variantStyles[variant];

  return (
    <div
      className={cn(
        'border border-[var(--color-border)] border-l-[3px]',
        'rounded-none rounded-r-[var(--radius-md)]',
        'p-4 my-6',
        styles.border,
        styles.bg,
        className
      )}
      {...props}
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {icon || styles.icon}
        </div>
        <div className="flex-1 min-w-0">
          {title && (
            <div className="font-semibold text-[var(--color-heading)] mb-1 font-[var(--font-heading)]">
              {title}
            </div>
          )}
          <div className="text-[15px] text-[var(--color-text-secondary)] leading-relaxed">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
