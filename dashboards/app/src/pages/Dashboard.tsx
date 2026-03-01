import { useRef, useCallback, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import { Badge } from '@/components/ui/Badge';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { StatusStrip } from '@/components/dashboard/StatusStrip';
import { QuickAction } from '@/components/dashboard/QuickAction';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { BarChart } from '@/components/dashboard/BarChart';
import { useSearch } from '@/context/SearchContext';
import { mcpServers, mcpStats } from '@/content/mcp-servers';
import { cliTools } from '@/content/cli-tools';
import { designConverterStats, architectureLayers, languageMetrics } from '@/content/architecture';
import {
  MagnifyingGlassIcon,
  ServerStackIcon,
  WrenchScrewdriverIcon,
  CodeBracketIcon,
  BeakerIcon,
  CubeTransparentIcon,
  SwatchIcon,
  BoltIcon,
  ArrowsRightLeftIcon,
  ChartBarIcon,
  SignalIcon,
  SparklesIcon,
  ClockIcon,
  RocketLaunchIcon,
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

export function Dashboard() {
  const { openSearch } = useSearch();
  const searchRef = useRef<IconHandle>(null);
  const handleSearchEnter = useCallback(() => searchRef.current?.startAnimation(), []);
  const handleSearchLeave = useCallback(() => searchRef.current?.stopAnimation(), []);

  return (
    <div className="content-wrap">
      {/* Search trigger */}
      <button
        type="button"
        onClick={openSearch}
        onMouseEnter={handleSearchEnter}
        onMouseLeave={handleSearchLeave}
        className="w-full flex items-center gap-3 px-4 py-2.5 mb-8 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-[var(--radius-md)] transition-all duration-200 hover:border-[rgba(52,211,153,0.3)] hover:shadow-[0_0_20px_rgba(52,211,153,0.04)] cursor-pointer group"
      >
        <MagnifyingGlassIcon ref={searchRef} size={16} className="text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] transition-colors" />
        <span className="text-sm text-[var(--color-text-muted)] font-[family-name:var(--font-body)]">
          Search tools, MCPs, IR nodes...
        </span>
        <kbd className="ml-auto px-1.5 py-0.5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded text-[10px] font-mono text-[var(--color-text-muted)]">
          ⌘K
        </kbd>
      </button>

      {/* Hero */}
      <header className="mb-8 pb-8 border-b border-[var(--color-border)]">
        <div className="eyebrow">Unified Design Workspace</div>
        <h1 className="mb-4">
          Design<span className="text-[var(--color-accent)]">Dev</span>
          <br />
          <em>AI-powered design tooling</em>
        </h1>
        <p className="text-[var(--color-text-secondary)] text-base max-w-xl mt-4 mb-5">
          Integrating Figma, Paper Design, and Pencil.dev through MCP servers,
          a zero-dependency Python IR, CLI tools, and AI skills.
        </p>
        <div className="flex flex-wrap gap-2">
          <Badge variant="info">v1.2.0</Badge>
          <Badge variant="secondary">2026-03-01</Badge>
          <Badge variant="default" dot>5 MCPs Active</Badge>
        </div>
      </header>

      {/* Status Strip */}
      <div className="mb-10">
        <StatusStrip servers={mcpServers} />
      </div>

      {/* §1 — At a Glance */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§1</span>
          <SectionIcon icon={SparklesIcon as AnimatedIcon} />
          At a Glance
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
          <MetricCard
            icon={ServerStackIcon}
            value={mcpStats.total}
            label="MCP Servers"
            color="var(--color-accent)"
            iconColorClass="text-[var(--color-accent)]"
            subValue={`${mcpStats.active} active`}
            barPercent={(mcpStats.active / mcpStats.total) * 100}
          />
          <MetricCard
            icon={WrenchScrewdriverIcon}
            value={mcpStats.totalTools}
            label="Total Tools"
            color="var(--color-blue)"
            iconColorClass="text-[var(--color-blue)]"
            subValue="across 5 MCPs"
          />
          <MetricCard
            icon={CodeBracketIcon}
            value={cliTools.length}
            label="CLI Tools"
            color="var(--color-amber)"
            iconColorClass="text-[var(--color-amber)]"
            subValue="Bash + Python"
          />
          <MetricCard
            icon={ChartBarIcon}
            value={`${(designConverterStats.linesOfCode / 1000).toFixed(1)}K`}
            label="Lines of Code"
            color="var(--color-purple)"
            iconColorClass="text-[var(--color-purple)]"
            subValue={`${designConverterStats.files} files`}
          />
          <MetricCard
            icon={BeakerIcon}
            value={designConverterStats.testCount}
            label="Tests Passing"
            color="var(--color-accent)"
            iconColorClass="text-[var(--color-accent)]"
            barPercent={100}
          />
          <MetricCard
            icon={CubeTransparentIcon}
            value={`${designConverterStats.irDataclasses} + ${designConverterStats.irEnums}`}
            label="IR Nodes + Enums"
            color="var(--color-blue)"
            iconColorClass="text-[var(--color-blue)]"
            subValue="zero deps"
          />
        </div>

        {/* IR Pipeline */}
        <div className="p-5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)]">
          <h4 className="mt-0 mb-3">IR Conversion Pipeline</h4>
          <div className="font-mono text-sm text-[var(--color-text-secondary)] leading-relaxed text-center py-3">
            <span className="text-[var(--color-heading)]">Figma</span>
            <span className="text-[var(--color-text-muted)]"> ←→ </span>
            <span className="text-[var(--color-accent)]">UNNode (IR)</span>
            <span className="text-[var(--color-text-muted)]"> ←→ </span>
            <span className="text-[var(--color-heading)]">Paper</span>
            <br />
            <span className="text-[var(--color-text-muted)] inline-block mt-1">↕</span>
            <br />
            <span className="text-[var(--color-heading)]">Pencil</span>
          </div>
          <p className="text-[var(--color-text-secondary)] text-sm mt-3 mb-0">
            All adapters implement <code>BaseReader.read_node()</code> → <code>UNNode</code> and{' '}
            <code>BaseWriter.write_node()</code> ← <code>UNNode</code>. Zero external runtime dependencies.
          </p>
        </div>
      </section>

      {/* §2 — Quick Actions */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§2</span>
          <SectionIcon icon={BoltIcon as AnimatedIcon} />
          Quick Actions
        </h2>
        <p className="text-[var(--color-text-secondary)] text-sm mb-6">
          Click any action to copy the command to your clipboard.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <QuickAction
            icon={SwatchIcon}
            label="Extract Tokens"
            command="figma-tokens.sh --preset=shadcn --export=css"
            color="var(--color-accent)"
            iconColorClass="text-[var(--color-accent)]"
          />
          <QuickAction
            icon={BoltIcon}
            label="Smoke Test"
            command="figma-smoke-test.sh --quick"
            color="var(--color-amber)"
            iconColorClass="text-[var(--color-amber)]"
          />
          <QuickAction
            icon={ArrowsRightLeftIcon}
            label="Convert Design"
            command="design-convert.sh figma:ABC123 paper:"
            color="var(--color-blue)"
            iconColorClass="text-[var(--color-blue)]"
          />
          <QuickAction
            icon={ChartBarIcon}
            label="Analyze Colors"
            command="figma-analyze.sh --type=colors --json"
            color="var(--color-purple)"
            iconColorClass="text-[var(--color-purple)]"
          />
          <QuickAction
            icon={BeakerIcon}
            label="Run All Tests"
            command="cd services/design-converter && python -m pytest"
            color="var(--color-accent)"
            iconColorClass="text-[var(--color-accent)]"
          />
          <QuickAction
            icon={SignalIcon}
            label="Bridge Server"
            command="figma-bridge-server --daemon"
            color="var(--color-blue)"
            iconColorClass="text-[var(--color-blue)]"
          />
        </div>
      </section>

      {/* §3 — System Health */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§3</span>
          <SectionIcon icon={ClockIcon as AnimatedIcon} />
          System Health
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-6">
          {/* Activity Feed */}
          <div className="p-5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)]">
            <h4 className="mt-0 mb-3">Recent Activity</h4>
            <ActivityFeed />
          </div>

          {/* Architecture Summary */}
          <div className="space-y-3">
            <h4 className="mt-0 mb-1">Architecture</h4>
            {architectureLayers.map((layer, idx) => (
              <div
                key={layer.name}
                className="p-4 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] border-l-[3px] rounded-none rounded-r-[var(--radius-md)]"
                style={{
                  borderLeftColor:
                    idx === 0 ? 'var(--color-blue)' : idx === 1 ? 'var(--color-accent)' : 'var(--color-amber)',
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-[10px] text-[var(--color-text-muted)]">0{idx + 1}</span>
                  <span className="font-[family-name:var(--font-heading)] text-sm font-semibold text-[var(--color-heading)]">
                    {layer.name}
                  </span>
                  <div className="flex gap-1 ml-auto">
                    {layer.languages.map((lang) => (
                      <Badge
                        key={lang}
                        variant={lang === 'Python' ? 'default' : lang === 'TypeScript' ? 'info' : 'warning'}
                        className="text-[9px]"
                      >
                        {lang}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="text-[11px] text-[var(--color-text-muted)] font-mono">
                  {layer.components.join(' · ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* §4 — Language Breakdown */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§4</span>
          <SectionIcon icon={ChartBarIcon as AnimatedIcon} />
          Language Breakdown
        </h2>

        <div className="p-5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)] mb-6">
          <BarChart
            items={[
              { label: 'CLI Tools (Bash)', value: 57000, formattedValue: '57,000', color: 'var(--color-amber)' },
              { label: 'figma-console MCP (TS)', value: 27943, formattedValue: '27,943', color: 'var(--color-blue)' },
              { label: 'design-converter (Python)', value: 19836, formattedValue: '19,836', color: 'var(--color-accent)' },
              { label: 'claude-talk-to-figma (TS)', value: 5258, formattedValue: '5,258', color: 'var(--color-purple)' },
            ]}
          />
        </div>

        {/* Collapsible detail table */}
        <details className="group">
          <summary className="font-mono text-[11px] text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-accent)] transition-colors select-none">
            View detailed breakdown →
          </summary>
          <div className="overflow-x-auto mt-4 rounded-[var(--radius-md)] border border-[var(--color-border)]">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                  {['Component', 'Language', 'Lines', 'Files', 'Dependencies'].map((h) => (
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
                {languageMetrics.map((m) => (
                  <tr
                    key={m.component}
                    className="border-b border-[var(--color-border-subtle)] last:border-0 hover:bg-[var(--color-bg-tertiary)]/50 transition-colors"
                  >
                    <td className="p-3 font-mono text-[12.5px] text-[var(--color-accent)] whitespace-nowrap">
                      {m.component}
                    </td>
                    <td className="p-3 text-[var(--color-text-secondary)]">
                      <Badge
                        variant={m.language === 'Python' ? 'default' : m.language === 'TypeScript' ? 'info' : 'warning'}
                        className="text-[10px]"
                      >
                        {m.language}
                      </Badge>
                    </td>
                    <td className="p-3 font-mono text-[12.5px] text-[var(--color-heading)]">
                      {m.linesOfCode.toLocaleString()}
                    </td>
                    <td className="p-3 font-mono text-[12.5px] text-[var(--color-text-secondary)]">{m.files}</td>
                    <td className="p-3 text-[var(--color-text-secondary)] text-xs">{m.dependencies}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      {/* §5 — MCP Servers */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§5</span>
          <SectionIcon icon={ServerStackIcon as AnimatedIcon} />
          MCP Servers
        </h2>
        <p>
          Five MCP servers cover the full design tool ecosystem. All CRUD servers depend on the
          Desktop Bridge plugin.
        </p>

        <div className="space-y-3 mt-6">
          {mcpServers.map((server) => (
            <div
              key={server.id}
              className="p-5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)] hover:border-[rgba(52,211,153,0.3)] transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full mt-0.5 ${
                      server.status === 'active' ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-amber)]'
                    }`}
                  />
                  <div>
                    <div className="font-[family-name:var(--font-heading)] font-semibold text-[var(--color-heading)]">
                      {server.name}
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)] font-mono mt-0.5">
                      {server.location}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-[var(--color-text-secondary)]">
                    {server.tools} tools
                  </span>
                  <div className="flex gap-1">
                    {server.capabilities.map((cap) => (
                      <Badge key={cap} variant="secondary" className="text-[10px]">
                        {cap.toUpperCase()}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <p className="text-sm text-[var(--color-text-secondary)] mb-1.5">{server.description}</p>
              <div className="text-xs text-[var(--color-text-muted)] font-mono">{server.protocol}</div>
            </div>
          ))}
        </div>
      </section>

      {/* §6 — Quick Start */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§6</span>
          <SectionIcon icon={RocketLaunchIcon as AnimatedIcon} />
          Quick Start
        </h2>

        <h3>Add CLI tools to PATH</h3>
        <CodeBlock
          code={`export PATH="$HOME/Projects Parent Folder/DesignDev/cli/bin:$PATH"`}
          language="bash"
        />

        <h3>Design Converter</h3>
        <CodeBlock
          code={`# Convert Figma → Paper
design-convert.sh figma:ABC123 paper:

# Convert Pencil → Figma via HTTP bridge
design-convert.sh pencil: figma: --figma-mode=bridge

# Extract W3C DTCG tokens
design-convert.sh figma:ABC123 --export-tokens tokens.json`}
          language="bash"
        />

        <h3>Python API</h3>
        <CodeBlock
          code={`from adapters.figma import FigmaReader
from adapters.paper import PaperWriter

tree = FigmaReader().read_node(file_key="abc123")
PaperWriter().write_node(tree, output_path="./output")`}
          language="python"
        />
      </section>

      {/* Footer */}
      <footer className="mt-16 pt-6 border-t border-[var(--color-border)] font-mono text-[11px] text-[var(--color-text-muted)] flex justify-between flex-wrap gap-2">
        <span>DesignDev · AI-Powered Design Workspace</span>
        <span>5 MCP Servers · {mcpStats.totalTools} Tools · {designConverterStats.linesOfCode.toLocaleString()} Lines</span>
      </footer>
    </div>
  );
}
