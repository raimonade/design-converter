import { cn } from '@/lib/utils';
import { CheckCircle2, Clock, ArrowRight } from 'lucide-react';

type PhaseStatus = 'done' | 'next' | 'future';

interface PhaseCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  status: PhaseStatus;
  icon?: string;
  items?: string[];
}

const statusStyles: Record<PhaseStatus, { border: string; icon: React.ReactNode }> = {
  done: {
    border: 'border-l-[var(--color-accent)]',
    icon: <CheckCircle2 className="w-5 h-5 text-[var(--color-accent)]" />,
  },
  next: {
    border: 'border-l-[var(--color-blue)]',
    icon: <ArrowRight className="w-5 h-5 text-[var(--color-blue)]" />,
  },
  future: {
    border: 'border-l-[var(--color-border)]',
    icon: <Clock className="w-5 h-5 text-[var(--color-text-muted)]" />,
  },
};

export function PhaseCard({
  title,
  status,
  icon,
  items = [],
  className,
  ...props
}: PhaseCardProps) {
  const styles = statusStyles[status];

  return (
    <div
      className={cn(
        'flex gap-5 p-5 my-4',
        'bg-[var(--color-bg-secondary)]',
        'border border-[var(--color-border)] border-l-[3px]',
        'rounded-[var(--radius-md)]',
        styles.border,
        className
      )}
      {...props}
    >
      <div className="flex-shrink-0 pt-0.5">
        {icon ? <span className="text-xl">{icon}</span> : styles.icon}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-[var(--font-heading)] text-base font-semibold text-[var(--color-heading)] mb-2">
          {title}
        </h4>
        {items.length > 0 && (
          <ul className="space-y-1.5">
            {items.map((item, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-[var(--color-text)]"
              >
                <span className="text-[var(--color-text-muted)] mt-0.5">—</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
