import { cn } from '@/lib/utils';

interface Field {
  name: string;
  type: string;
  default: string;
  description: string;
}

interface FieldTableProps extends React.HTMLAttributes<HTMLDivElement> {
  fields: Field[];
}

export function FieldTable({ fields, className, ...props }: FieldTableProps) {
  return (
    <div
      className={cn(
        'overflow-x-auto my-5',
        'rounded-[var(--radius-md)] border border-[var(--color-border)]',
        className
      )}
      {...props}
    >
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
            <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-left whitespace-nowrap">
              Field
            </th>
            <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-left whitespace-nowrap">
              Type
            </th>
            <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-left whitespace-nowrap">
              Default
            </th>
            <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-left whitespace-nowrap">
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => (
            <tr
              key={field.name}
              className="border-b border-[var(--color-border-subtle)] last:border-0 hover:bg-[var(--color-bg-tertiary)]/50 transition-colors"
            >
              <td className="p-3 font-mono text-[12.5px] text-[var(--color-accent)] whitespace-nowrap">
                {field.name}
              </td>
              <td className="p-3 font-mono text-[12.5px] text-[var(--color-text-secondary)]">
                {field.type}
              </td>
              <td className="p-3 font-mono text-[12.5px] text-[var(--color-text-muted)]">
                {field.default}
              </td>
              <td className="p-3 text-[var(--color-text-secondary)]">
                {field.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
