import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-[11px] font-medium',
  {
    variants: {
      variant: {
        default: 'bg-[var(--color-accent-dim)] text-[var(--color-accent)] border border-[rgba(52,211,153,0.25)]',
        secondary: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)]',
        warning: 'bg-[var(--color-amber-dim)] text-[var(--color-amber)] border border-[rgba(251,191,36,0.2)]',
        error: 'bg-[var(--color-red-dim)] text-[var(--color-red)] border border-[rgba(248,113,113,0.2)]',
        info: 'bg-[var(--color-blue-dim)] text-[var(--color-blue)] border border-[rgba(96,165,250,0.2)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && <span className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />}
      {children}
    </span>
  );
}
