import { useRef, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import { Badge } from '@/components/ui/Badge';
import { CodeBlock } from '@/components/ui/CodeBlock';
import { FieldTable } from '@/components/ui/FieldTable';
import { Callout } from '@/components/ui/Callout';
import { GapCard } from '@/components/ui/GapCard';
import { PhaseCard } from '@/components/ui/PhaseCard';
import { irSections, irEnums, irKeyFacts } from '@/content/ir-reference';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  LightBulbIcon,
  ListBulletIcon,
  TableCellsIcon,
  ExclamationCircleIcon,
  MapIcon,
  CodeBracketIcon,
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

function StatusIcon({ status }: { status: string }) {
  const ref = useRef<IconHandle>(null);
  if (status === '✅') {
    return (
      <span
        className="inline-flex"
        onMouseEnter={() => ref.current?.startAnimation()}
        onMouseLeave={() => ref.current?.stopAnimation()}
      >
        <CheckCircleIcon ref={ref} size={18} className="text-[var(--color-accent)]" />
      </span>
    );
  }
  if (status === '⚠️') {
    return (
      <span
        className="inline-flex"
        onMouseEnter={() => ref.current?.startAnimation()}
        onMouseLeave={() => ref.current?.stopAnimation()}
      >
        <ExclamationTriangleIcon ref={ref} size={18} className="text-[var(--color-amber)]" />
      </span>
    );
  }
  return (
    <span
      className="inline-flex"
      onMouseEnter={() => ref.current?.startAnimation()}
      onMouseLeave={() => ref.current?.stopAnimation()}
    >
      <XCircleIcon ref={ref} size={18} className="text-[var(--color-text-muted)] opacity-50" />
    </span>
  );
}

export function IRReference() {
  return (
    <div className="content-wrap">
      {/* Hero */}
      <header className="mb-14 pb-10 border-b border-[var(--color-border)]">
        <div className="eyebrow">Universal Design Intermediate Representation</div>
        <h1 className="mb-4">
          UNNode
          <br />
          <em>The canonical layer between design tools</em>
        </h1>
        <p className="text-[var(--color-text-secondary)] text-base max-w-xl mt-4 mb-5">
          A Python dataclass-based IR for converting between Figma, Paper Design, and Pencil.dev.
          15 dataclasses, 13 enums, zero runtime dependencies.
        </p>
        <div className="flex flex-wrap gap-2">
          <Badge variant="info">v1.2.0</Badge>
          <Badge variant="secondary">2026-03-01</Badge>
          <Badge variant="default" dot>Production-ready</Badge>
        </div>
      </header>

      {/* All Sections */}
      {irSections.map((section, idx) => (
        <section key={section.id} id={section.id} className="mb-16">
          <h2>
            <span className="section-num">§{idx + 1}</span>
            <SectionIcon icon={CodeBracketIcon as AnimatedIcon} />
            {section.title}
          </h2>
          <p className="text-[var(--color-text)] text-base mb-6">{section.description}</p>

          {section.fields && <FieldTable fields={section.fields} />}

          {section.code && <CodeBlock code={section.code} language="python" />}

          {section.id === 'overview' && (
            <Callout variant="info" title="Zero Dependencies">
              The design-converter uses only Python stdlib — no external runtime dependencies.
              All HTTP, WebSocket, JSON, and CSS parsing is handled by stdlib modules.
            </Callout>
          )}
        </section>
      ))}

      {/* Key Facts */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§{irSections.length + 1}</span>
          <SectionIcon icon={LightBulbIcon as AnimatedIcon} />
          Key Facts
        </h2>
        <div className="space-y-4">
          {irKeyFacts.map((fact) => (
            <div
              key={fact.title}
              className="p-5 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)]"
            >
              <h4 className="mt-0 mb-2">{fact.title}</h4>
              <p className="text-[var(--color-text-secondary)] text-sm mb-0">{fact.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Enum Reference */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§{irSections.length + 2}</span>
          <SectionIcon icon={ListBulletIcon as AnimatedIcon} />
          Enum Reference
        </h2>
        <p>
          All enums use lowercase string values matching Figma's API conventions.
          Values are defined in <code>ir/nodes.py</code>.
        </p>

        <div className="overflow-x-auto mt-6 rounded-[var(--radius-md)] border border-[var(--color-border)]">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                {['Enum', 'Values', 'Description'].map((h) => (
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
              {irEnums.map((e) => (
                <tr
                  key={e.name}
                  className="border-b border-[var(--color-border-subtle)] last:border-0 hover:bg-[var(--color-bg-tertiary)]/50 transition-colors align-top"
                >
                  <td className="p-3 font-mono text-[12.5px] text-[var(--color-accent)] whitespace-nowrap">
                    {e.name}
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {e.values.map((v) => (
                        <span
                          key={v}
                          className="inline-block px-1.5 py-0.5 bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] font-mono text-[10px] rounded border border-[var(--color-border)]"
                        >
                          {v}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-3 text-[var(--color-text-secondary)] text-sm">{e.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Adapter Matrix */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§{irSections.length + 3}</span>
          <SectionIcon icon={TableCellsIcon as AnimatedIcon} />
          Adapter Matrix
        </h2>
        <p>Symmetric readers and writers for each design tool.</p>

        <div className="overflow-x-auto mt-6 rounded-[var(--radius-md)] border border-[var(--color-border)]">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                {['Adapter', 'Reader', 'Writer', 'Client', 'Protocol'].map((h) => (
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
                { name: 'Figma', reader: '965 lines', writer: '1,134 lines', client: '534 lines', protocol: 'REST API + Plugin JS' },
                { name: 'Paper', reader: '1,553 lines', writer: '1,154 lines', client: '663 lines', protocol: 'MCP SSE :29979' },
                { name: 'Pencil', reader: '1,300 lines', writer: '1,047 lines', client: '1,260 lines', protocol: 'HTTP REST :19002' },
              ].map((a) => (
                <tr
                  key={a.name}
                  className="border-b border-[var(--color-border-subtle)] last:border-0 hover:bg-[var(--color-bg-tertiary)]/50 transition-colors"
                >
                  <td className="p-3 font-mono text-[12.5px] text-[var(--color-accent)] whitespace-nowrap">
                    {a.name}
                  </td>
                  <td className="p-3 font-mono text-[12px] text-[var(--color-text-secondary)]">{a.reader}</td>
                  <td className="p-3 font-mono text-[12px] text-[var(--color-text-secondary)]">{a.writer}</td>
                  <td className="p-3 font-mono text-[12px] text-[var(--color-text-secondary)]">{a.client}</td>
                  <td className="p-3 text-[var(--color-text-secondary)] text-xs">{a.protocol}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Feature Matrix */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§{irSections.length + 4}</span>
          <SectionIcon icon={CheckCircleIcon as AnimatedIcon} />
          Feature Matrix
        </h2>
        <div className="flex items-center gap-4 text-[11px] text-[var(--color-text-muted)] font-mono mb-4">
          <span className="flex items-center gap-1.5"><CheckCircleIcon size={14} className="text-[var(--color-accent)]" /> Full</span>
          <span className="flex items-center gap-1.5"><ExclamationTriangleIcon size={14} className="text-[var(--color-amber)]" /> Partial</span>
          <span className="flex items-center gap-1.5"><XCircleIcon size={14} className="text-[var(--color-text-muted)] opacity-50" /> None</span>
        </div>

        <div className="overflow-x-auto mt-2 rounded-[var(--radius-md)] border border-[var(--color-border)]">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)]">
                <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-left whitespace-nowrap">
                  Feature
                </th>
                <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-center whitespace-nowrap">
                  Figma
                </th>
                <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-center whitespace-nowrap">
                  Paper
                </th>
                <th className="font-mono text-[10px] font-medium tracking-[0.12em] uppercase text-[var(--color-text-muted)] p-3 text-center whitespace-nowrap">
                  Pencil
                </th>
              </tr>
            </thead>
            <tbody>
              {[
                { feature: 'Frame / Rectangle', figma: '✅', paper: '✅', pencil: '✅' },
                { feature: 'Text with runs (rich text)', figma: '✅', paper: '✅', pencil: '⚠️' },
                { feature: 'Auto Layout (flexbox)', figma: '✅', paper: '✅', pencil: '❌' },
                { feature: 'Components & instances', figma: '✅', paper: '⚠️', pencil: '❌' },
                { feature: 'Design variables/tokens', figma: '✅', paper: '❌', pencil: '✅' },
                { feature: 'Gradients (linear/radial)', figma: '✅', paper: '⚠️', pencil: '✅' },
                { feature: 'Effects (shadows/blur)', figma: '✅', paper: '✅', pencil: '⚠️' },
                { feature: 'Images / raster fills', figma: '✅', paper: '✅', pencil: '✅' },
                { feature: 'Vector paths / SVG', figma: '⚠️', paper: '❌', pencil: '✅' },
                { feature: 'Mask nodes', figma: '✅', paper: '⚠️', pencil: '❌' },
              ].map((row) => (
                <tr
                  key={row.feature}
                  className="border-b border-[var(--color-border-subtle)] last:border-0 hover:bg-[var(--color-bg-tertiary)]/50 transition-colors"
                >
                  <td className="p-3 font-mono text-[12.5px] text-[var(--color-accent)] whitespace-nowrap">
                    {row.feature}
                  </td>
                  <td className="p-3 text-center"><div className="flex justify-center"><StatusIcon status={row.figma} /></div></td>
                  <td className="p-3 text-center"><div className="flex justify-center"><StatusIcon status={row.paper} /></div></td>
                  <td className="p-3 text-center"><div className="flex justify-center"><StatusIcon status={row.pencil} /></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Gap Analysis */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§{irSections.length + 5}</span>
          <SectionIcon icon={ExclamationCircleIcon as AnimatedIcon} />
          Gap Analysis
        </h2>
        <p>Known limitations and missing features prioritised by severity.</p>

        <div className="mt-6 space-y-4">
          <GapCard id="G1" title="Component Overrides" severity="critical">
            Deep instance overrides are not fully captured. Octopus has comprehensive <code>overrides[]</code> support.
            Currently only basic property overrides are preserved.
          </GapCard>
          <GapCard id="G2" title="Mask Nodes" severity="important">
            The <code>isMask</code> property is not preserved in UNNode. Frame-level masks work but
            vector masks and image masks need special handling.
          </GapCard>
          <GapCard id="G3" title="Stroke Dashes & Line Caps" severity="important">
            <code>UNStroke</code> is missing <code>dashPattern</code>, <code>lineCap</code>, and <code>lineJoin</code> fields.
            Dashed borders render as solid.
          </GapCard>
          <GapCard id="G4" title="Blend Mode Per Fill" severity="nice">
            <code>UNSolidFill</code> has no <code>blend_mode</code> field. Only node-level blend modes are supported,
            not per-fill compositing.
          </GapCard>
          <GapCard id="G5" title="Grid Layout Mode" severity="nice">
            CSS Grid layout mode is not supported. Only flexbox (horizontal/vertical) via <code>LayoutMode</code>.
          </GapCard>
        </div>
      </section>

      {/* Roadmap */}
      <section className="mb-16">
        <h2>
          <span className="section-num">§{irSections.length + 6}</span>
          <SectionIcon icon={MapIcon as AnimatedIcon} />
          Roadmap
        </h2>
        <p>Implementation phases and their current status.</p>

        <div className="mt-6 space-y-4">
          <PhaseCard
            title="Phase 1 — Core IR"
            status="done"
            items={[
              'UNNode dataclass with 15+ fields',
              'NodeType, LayoutMode, BlendMode enums',
              'un_node_to_dict / un_node_from_dict serialization',
            ]}
          />
          <PhaseCard
            title="Phase 2 — Figma Adapter"
            status="done"
            items={[
              'FigmaReader: REST API → UNNode',
              'FigmaWriter: UNNode → Plugin API JS',
              'Rich text runs from characterStyleOverrides',
            ]}
          />
          <PhaseCard
            title="Phase 3 — Paper & Pencil"
            status="done"
            items={[
              'PaperReader/Writer via MCP SSE :29979',
              'PencilReader/Writer via HTTP REST :19002',
              'DTCG token export (W3C 2025.10 format)',
            ]}
          />
          <PhaseCard
            title="Phase 4 — Gap Closure"
            status="next"
            items={[
              'Component overrides capture',
              'Mask node preservation',
              'Stroke dash/cap/join fields',
            ]}
          />
          <PhaseCard
            title="Phase 5 — Advanced"
            status="future"
            items={[
              'Grid layout mode support',
              'Vector boolean operations',
              'Plugin API code generation',
            ]}
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-16 pt-6 border-t border-[var(--color-border)] font-mono text-[11px] text-[var(--color-text-muted)] flex justify-between flex-wrap gap-2">
        <span>DesignDev · UNNode IR Reference</span>
        <span>
          {irSections.length} sections · {irEnums.length} enums · 15 dataclasses
        </span>
      </footer>
    </div>
  );
}
