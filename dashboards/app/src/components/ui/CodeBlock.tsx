import { useState } from 'react';
import { cn } from '@/lib/utils';
import { Copy, Check } from 'lucide-react';

interface CodeBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({
  code,
  language = 'python',
  filename,
  showLineNumbers = false,
  className,
  ...props
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = code.split('\n');

  return (
    <div
      className={cn(
        'relative rounded-[var(--radius-md)] border border-[var(--color-border)]',
        'overflow-hidden bg-[var(--color-bg-code)]',
        'my-5',
        className
      )}
      {...props}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
        <span className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)]">
          {filename || language}
        </span>
        <button
          onClick={handleCopy}
          className={cn(
            'font-mono text-[10px] tracking-[0.08em] uppercase',
            'px-2 py-1 rounded border transition-all',
            copied
              ? 'text-[var(--color-accent)] border-[var(--color-accent)] bg-[var(--color-accent-dim)]'
              : 'text-[var(--color-text-muted)] border-[var(--color-border)] hover:text-[var(--color-accent)] hover:border-[var(--color-accent)]'
          )}
        >
          <span className="flex items-center gap-1.5">
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </span>
        </button>
      </div>

      {/* Code */}
      <pre className="overflow-x-auto p-4 scrollbar-thin">
        <code className="font-mono text-[13px] leading-relaxed text-[var(--color-code-text)]">
          {showLineNumbers ? (
            <table className="w-full border-collapse">
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i} className="hover:bg-[var(--color-bg-tertiary)]/30">
                    <td className="pr-4 text-right text-[var(--color-text-muted)] select-none w-8 align-top">
                      {i + 1}
                    </td>
                    <td className="whitespace-pre">{line || ' '}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            code
          )}
        </code>
      </pre>
    </div>
  );
}
