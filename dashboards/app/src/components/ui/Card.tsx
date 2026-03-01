import { cn } from '@/lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered';
}

export function Card({ className, variant = 'default', ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-[var(--radius-md)] p-5',
        {
          'bg-[var(--color-bg-secondary)] border border-[var(--color-border)]': variant === 'default',
          'bg-[var(--color-bg-elevated)] shadow-[var(--shadow-lg)]': variant === 'elevated',
          'bg-[var(--color-bg-secondary)] border-2 border-[var(--color-border)]': variant === 'bordered',
        },
        className
      )}
      {...props}
    />
  );
}

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardHeader({ className, ...props }: CardHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)} {...props} />
  );
}

interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export function CardTitle({ className, ...props }: CardTitleProps) {
  return <h3 className={cn('font-[var(--font-heading)] font-semibold text-lg text-[var(--color-heading)]', className)} {...props} />;
}

interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

export function CardDescription({ className, ...props }: CardDescriptionProps) {
  return <p className={cn('text-sm text-[var(--color-text-secondary)]', className)} {...props} />;
}

interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardContent({ className, ...props }: CardContentProps) {
  return <div className={cn('', className)} {...props} />;
}
