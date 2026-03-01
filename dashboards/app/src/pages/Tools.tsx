import { useState, useRef, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import { Badge } from '@/components/ui/Badge';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { Callout } from '@/components/ui/Callout';
import { cliTools, toolCategories } from '@/content/cli-tools';
import { Copy, Check } from 'lucide-react';
import {
  CommandLineIcon,
  WrenchScrewdriverIcon,
  SignalIcon,
} from '@heroicons-animated/react';

interface IconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}

type AnimatedIcon = ForwardRefExoticComponent<{ size?: number; className?: string } & RefAttributes<IconHandle>>;

function SectionIcon({ icon: Icon, className = '' }: { icon: AnimatedIcon; className?: string }) {
  const ref = useRef<IconHandle>(null);
  return (
    <span
      className={`inline-flex ${className}`}
      onMouseEnter={() => ref.current?.startAnimation()}
      onMouseLeave={() => ref.current?.stopAnimation()}
    >
      <Icon ref={ref} size={20} className="opacity-60" />
    </span>
  );
}

export function Tools() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredTools = selectedCategory
    ? cliTools.filter((t) => t.category === selectedCategory)
    : cliTools;

  const copyCommand = (cmd: string, id: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="content-wrap">
      {/* ── Hero ──────────────────────────────────────────── */}
      <header className="mb-14 pb-10 border-b border-[var(--color-border)]">
        <div className="eyebrow">CLI Interface</div>
        <h1>
          Tools <em>& CLI</em>
        </h1>
        <p className="text-[var(--color-text-secondary)] text-base max-w-xl mt-4 mb-5">
          Command-line tools for token extraction, design analysis, workflow automation,
          and cross-tool conversion. All support <code>--help</code>, <code>--dry-run</code>,
          and interactive mode.
        </p>
        <div className="flex flex-wrap gap-2">
          <Badge variant="default">{cliTools.length} Tools</Badge>
          <Badge variant="secondary">Bash + Python</Badge>
          <Badge variant="info">Exit codes: 0 / 1 / 2</Badge>
        </div>
      </header>

      {/* ── §1 Setup ──────────────────────────────────────── */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§1</span>
          <SectionIcon icon={CommandLineIcon as AnimatedIcon} />
          Setup
        </h2>
        <p>Add the CLI bin directory to your PATH:</p>
        <CodeBlock
          code='export PATH="$HOME/Projects Parent Folder/DesignDev/cli/bin:$PATH"'
          language="bash"
        />

        <Callout variant="default" title="Exit Codes">
          All CLI tools follow Unix conventions: <code>0</code> success,{' '}
          <code>1</code> error, <code>2</code> not connected to Figma.
        </Callout>
      </section>

      {/* ── §2 Catalog ────────────────────────────────────── */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§2</span>
          <SectionIcon icon={WrenchScrewdriverIcon as AnimatedIcon} />
          Catalog
        </h2>

        {/* Filter pills — styled as the UNNODE legend strip */}
        <div className="flex flex-wrap gap-2 p-3 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-[var(--radius-md)] mb-8">
          <FilterPill
            active={selectedCategory === null}
            onClick={() => setSelectedCategory(null)}
            label={`All (${cliTools.length})`}
          />
          {toolCategories.map((cat) => (
            <FilterPill
              key={cat.id}
              active={selectedCategory === cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              label={`${cat.label} (${cat.count})`}
            />
          ))}
        </div>

        {/* Tool cards */}
        {filteredTools.map((tool, idx) => (
          <div
            key={tool.id}
            className="mb-4 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] border-l-[3px] rounded-none rounded-r-[var(--radius-md)] transition-colors hover:border-[var(--color-border)]"
            style={{
              borderLeftColor:
                tool.category === 'tokens'
                  ? 'var(--color-accent)'
                  : tool.category === 'conversion'
                    ? 'var(--color-blue)'
                    : tool.category === 'testing'
                      ? 'var(--color-amber)'
                      : tool.category === 'analysis'
                        ? 'var(--color-purple)'
                        : 'var(--color-border)',
            }}
          >
            {/* Tool header */}
            <div className="px-5 pt-5 pb-3">
              <div className="flex items-center gap-3 mb-1">
                <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <h3 className="text-base font-semibold text-[var(--color-heading)] m-0">
                  {tool.name}
                </h3>
                <Badge
                  variant={
                    tool.category === 'tokens'
                      ? 'default'
                      : tool.category === 'conversion'
                        ? 'info'
                        : tool.category === 'testing'
                          ? 'warning'
                          : 'secondary'
                  }
                  className="ml-auto text-[10px]"
                >
                  {tool.category}
                </Badge>
              </div>
              <div className="ml-[30px]">
                <code className="text-[12px]">{tool.script}</code>
                <p className="text-sm text-[var(--color-text-secondary)] mt-2 mb-0">
                  {tool.description}
                </p>
              </div>
            </div>

            {/* Examples — dark code area */}
            <div className="mx-5 mb-5 rounded-[var(--radius-sm)] border border-[var(--color-border)] overflow-hidden bg-[var(--color-bg-code)]">
              <div className="px-3 py-1.5 bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                <span className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)]">
                  Examples
                </span>
              </div>
              <div className="divide-y divide-[var(--color-border-subtle)]">
                {tool.examples.map((example, exIdx) => (
                  <div
                    key={exIdx}
                    className="flex items-center justify-between px-4 py-2 group hover:bg-[var(--color-bg-tertiary)]/30 transition-colors"
                  >
                    <code className="text-[12.5px] text-[var(--color-code-text)] bg-transparent border-none p-0 leading-relaxed">
                      <span className="text-[var(--color-text-muted)] mr-2 select-none">$</span>
                      {example}
                    </code>
                    <button
                      onClick={() => copyCommand(example, `${tool.id}-${exIdx}`)}
                      className="p-1 rounded hover:bg-[var(--color-bg-elevated)] transition-all opacity-0 group-hover:opacity-100 cursor-pointer flex-shrink-0 ml-3"
                    >
                      {copiedId === `${tool.id}-${exIdx}` ? (
                        <Check className="w-3.5 h-3.5 text-[var(--color-accent)]" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </section>

      {/* ── §3 Connection Requirements ────────────────────── */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§3</span>
          <SectionIcon icon={SignalIcon as AnimatedIcon} />
          Connection Requirements
        </h2>

        <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                {['Tool', 'Requires', 'Port', 'Protocol'].map((h) => (
                  <th
                    key={h}
                    className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-left whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { tool: 'figma-tokens.sh', requires: 'Figma API token', port: '—', protocol: 'REST API' },
                { tool: 'figma-analyze.sh', requires: 'Figma API token', port: '—', protocol: 'REST API' },
                { tool: 'figma-smoke-test.sh', requires: 'Desktop Bridge', port: '9223–9232', protocol: 'WebSocket' },
                { tool: 'figma-workflow-runner.sh', requires: 'Desktop Bridge', port: '9223–9232', protocol: 'WebSocket' },
                { tool: 'design-convert.sh', requires: 'Varies by adapter', port: '9224 / 29979 / 19002', protocol: 'WS / SSE / HTTP' },
                { tool: 'figma-bridge-server', requires: 'None', port: '9224', protocol: 'WebSocket' },
              ].map((row) => (
                <tr
                  key={row.tool}
                  className="border-b border-[var(--color-border-subtle)] last:border-0 hover:bg-[var(--color-bg-tertiary)]/50 transition-colors"
                >
                  <td className="p-3 font-mono text-[12.5px] text-[var(--color-accent)] whitespace-nowrap">
                    {row.tool}
                  </td>
                  <td className="p-3 text-[var(--color-text-secondary)]">{row.requires}</td>
                  <td className="p-3 font-mono text-[12px] text-[var(--color-text-muted)]">{row.port}</td>
                  <td className="p-3 text-[var(--color-text-secondary)] text-xs">{row.protocol}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────── */}
      <footer className="mt-16 pt-6 border-t border-[var(--color-border)] font-mono text-[11px] text-[var(--color-text-muted)] flex justify-between flex-wrap gap-2">
        <span>DesignDev · CLI Tools Reference</span>
        <span>{cliTools.length} tools · {toolCategories.length} categories</span>
      </footer>
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`font-mono text-[11px] font-medium px-2.5 py-1 rounded-[4px] border transition-all cursor-pointer ${
        active
          ? 'bg-[var(--color-accent-dim)] text-[var(--color-accent)] border-[rgba(52,211,153,0.25)]'
          : 'bg-transparent text-[var(--color-text-muted)] border-transparent hover:text-[var(--color-heading)] hover:bg-[var(--color-bg-elevated)]'
      }`}
    >
      {label}
    </button>
  );
}
