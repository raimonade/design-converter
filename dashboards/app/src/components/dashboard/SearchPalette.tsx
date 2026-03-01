import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useSearch } from '@/context/SearchContext';
import { mcpServers } from '@/content/mcp-servers';
import { cliTools } from '@/content/cli-tools';
import { irSections, irEnums } from '@/content/ir-reference';
import {
  MagnifyingGlassIcon,
  ServerStackIcon,
  WrenchScrewdriverIcon,
  CodeBracketIcon,
  DocumentTextIcon,
} from '@heroicons-animated/react';
import type { ComponentType } from 'react';

interface SearchItem {
  id: string;
  title: string;
  subtitle: string;
  category: 'mcp' | 'cli' | 'ir' | 'enum';
  href: string;
  icon: ComponentType<{ size?: number; className?: string }>;
}

const categoryLabels: Record<string, string> = {
  mcp: 'MCP Servers',
  cli: 'CLI Tools',
  ir: 'IR Reference',
  enum: 'Enums',
};

const categoryColors: Record<string, string> = {
  mcp: 'var(--color-accent)',
  cli: 'var(--color-amber)',
  ir: 'var(--color-blue)',
  enum: 'var(--color-purple)',
};

function buildIndex(): SearchItem[] {
  const items: SearchItem[] = [];

  for (const s of mcpServers) {
    items.push({
      id: `mcp-${s.id}`,
      title: s.name,
      subtitle: `${s.tools} tools · ${s.protocol}`,
      category: 'mcp',
      href: '/',
      icon: ServerStackIcon,
    });
  }

  for (const t of cliTools) {
    items.push({
      id: `cli-${t.id}`,
      title: t.name,
      subtitle: t.script,
      category: 'cli',
      href: '/tools',
      icon: WrenchScrewdriverIcon,
    });
  }

  for (const s of irSections) {
    items.push({
      id: `ir-${s.id}`,
      title: s.title,
      subtitle: s.description.slice(0, 80),
      category: 'ir',
      href: '/ir-reference',
      icon: CodeBracketIcon,
    });
  }

  for (const e of irEnums) {
    items.push({
      id: `enum-${e.name}`,
      title: e.name,
      subtitle: e.values.join(', ').slice(0, 60),
      category: 'enum',
      href: '/ir-reference',
      icon: DocumentTextIcon,
    });
  }

  return items;
}

export function SearchPalette() {
  const { isSearchOpen, closeSearch } = useSearch();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const index = useMemo(() => buildIndex(), []);

  const results = useMemo(() => {
    if (!query.trim()) return index.slice(0, 8);
    const q = query.toLowerCase();
    return index.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        item.category.includes(q),
    );
  }, [query, index]);

  useEffect(() => {
    if (isSearchOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isSearchOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const selectItem = (item: SearchItem) => {
    closeSearch();
    navigate({ to: item.href });
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      selectItem(results[selectedIndex]);
    }
  };

  if (!isSearchOpen) return null;

  const grouped = results.reduce<Record<string, SearchItem[]>>((acc, item) => {
    (acc[item.category] ??= []).push(item);
    return acc;
  }, {});

  let flatIndex = 0;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[18vh]" onClick={closeSearch}>
      <div className="absolute inset-0 bg-[rgba(0,0,0,0.6)] backdrop-blur-[6px]" />
      <div
        className="relative w-full max-w-[540px] bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-lg)] shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)]">
          <MagnifyingGlassIcon size={18} className="text-[var(--color-text-muted)] flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search MCPs, tools, IR nodes, enums..."
            className="flex-1 bg-transparent text-[var(--color-text)] text-sm font-[family-name:var(--font-body)] placeholder:text-[var(--color-text-muted)] outline-none border-none"
          />
          <kbd className="px-1.5 py-0.5 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded text-[10px] font-mono text-[var(--color-text-muted)]">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[360px] overflow-y-auto py-2">
          {results.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
              No results for "{query}"
            </div>
          ) : (
            Object.entries(grouped).map(([cat, items]) => (
              <div key={cat}>
                <div className="px-4 py-1.5">
                  <span
                    className="font-mono text-[9px] font-medium tracking-[0.14em] uppercase"
                    style={{ color: categoryColors[cat] }}
                  >
                    {categoryLabels[cat]}
                  </span>
                </div>
                {items.map((item) => {
                  const thisIndex = flatIndex++;
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => selectItem(item)}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors cursor-pointer ${
                        thisIndex === selectedIndex
                          ? 'bg-[var(--color-accent-dim)]'
                          : 'hover:bg-[var(--color-bg-tertiary)]/50'
                      }`}
                    >
                      <div className="flex-shrink-0 opacity-60" style={{ color: categoryColors[item.category] }}>
                        <Icon size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-[var(--color-heading)] truncate">{item.title}</div>
                        <div className="text-[11px] text-[var(--color-text-muted)] font-mono truncate">
                          {item.subtitle}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-[var(--color-border)] text-[10px] font-mono text-[var(--color-text-muted)]">
          <span>
            <kbd className="px-1 py-px bg-[var(--color-bg-tertiary)] rounded border border-[var(--color-border)]">↑↓</kbd>{' '}
            Navigate
          </span>
          <span>
            <kbd className="px-1 py-px bg-[var(--color-bg-tertiary)] rounded border border-[var(--color-border)]">↵</kbd>{' '}
            Open
          </span>
          <span className="ml-auto">{results.length} results</span>
        </div>
      </div>
    </div>
  );
}
