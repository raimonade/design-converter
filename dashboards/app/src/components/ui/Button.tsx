import { Button as BaseButton } from '@base-ui/react/button';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50 cursor-pointer',
  {
    variants: {
      variant: {
        default:
          'bg-emerald-500 text-white hover:bg-emerald-400 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40',
        secondary: 'bg-bg-tertiary text-text hover:bg-bg-elevated border border-border',
        outline: 'border border-border text-text hover:bg-bg-tertiary',
        ghost: 'text-text-secondary hover:text-text hover:bg-bg-tertiary',
        link: 'text-emerald-400 hover:text-emerald-300 underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-12 px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface ButtonProps
  extends React.ComponentProps<typeof BaseButton>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return (
    <BaseButton className={cn(buttonVariants({ variant, size }), className)} {...props} />
  );
}
