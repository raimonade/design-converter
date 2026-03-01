import { Link } from '@tanstack/react-router';
import { useRef, useCallback, type ForwardRefExoticComponent, type RefAttributes } from 'react';
import {
  MagnifyingGlassIcon,
  HomeIcon,
  WrenchScrewdriverIcon,
  CodeBracketIcon,
  BookOpenIcon,
  ArrowTopRightOnSquareIcon,
  SparklesIcon,
} from '@heroicons-animated/react';
import { useSearch } from '@/context/SearchContext';

interface IconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}

type AnimatedIcon = ForwardRefExoticComponent<{ size?: number; className?: string } & RefAttributes<IconHandle>>;

const navSections = [
  {
    label: 'Overview',
    items: [
      { to: '/' as const, icon: HomeIcon as AnimatedIcon, label: 'Dashboard', num: '01' },
      { to: '/tools' as const, icon: WrenchScrewdriverIcon as AnimatedIcon, label: 'Tools & CLI', num: '02' },
    ],
  },
  {
    label: 'Documentation',
    items: [
      { to: '/ir-reference' as const, icon: CodeBracketIcon as AnimatedIcon, label: 'IR Reference', num: '03' },
    ],
  },
];

function NavLink({ item }: { item: { to: '/' | '/tools' | '/ir-reference'; icon: AnimatedIcon; label: string; num: string } }) {
  const iconRef = useRef<IconHandle>(null);
  const handleMouseEnter = useCallback(() => iconRef.current?.startAnimation(), []);
  const handleMouseLeave = useCallback(() => iconRef.current?.stopAnimation(), []);

  return (
    <Link
      to={item.to}
      activeOptions={{ exact: true }}
      className="flex items-center gap-2.5 px-5 py-2 font-mono text-[13px] text-[var(--color-text)] border-l-2 border-transparent transition-all duration-[180ms] hover:text-[var(--color-heading)] hover:bg-[var(--color-accent-dim)] hover:border-l-[rgba(52,211,153,0.4)] [&.active]:text-[var(--color-accent)] [&.active]:bg-[var(--color-accent-dim)] [&.active]:border-l-[var(--color-accent)] [&.active]:font-medium no-underline hover:no-underline"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <span className="text-[10px] min-w-[18px] text-[var(--color-text-muted)] [.active_&]:text-[var(--color-accent)] [.active_&]:opacity-70">
        {item.num}
      </span>
      <item.icon ref={iconRef} size={16} className="opacity-75" />
      {item.label}
    </Link>
  );
}

function ResourceLink({ href, icon: Icon, label }: { href: string; icon: AnimatedIcon; label: string }) {
  const iconRef = useRef<IconHandle>(null);
  const handleMouseEnter = useCallback(() => iconRef.current?.startAnimation(), []);
  const handleMouseLeave = useCallback(() => iconRef.current?.stopAnimation(), []);

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 px-0 py-1.5 font-mono text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors no-underline hover:no-underline"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <Icon ref={iconRef} size={14} />
      {label}
    </a>
  );
}

export function Sidebar() {
  const { openSearch } = useSearch();
  const searchIconRef = useRef<IconHandle>(null);
  const handleSearchEnter = useCallback(() => searchIconRef.current?.startAnimation(), []);
  const handleSearchLeave = useCallback(() => searchIconRef.current?.stopAnimation(), []);
  const brandIconRef = useRef<IconHandle>(null);
  const handleBrandEnter = useCallback(() => brandIconRef.current?.startAnimation(), []);
  const handleBrandLeave = useCallback(() => brandIconRef.current?.stopAnimation(), []);

  return (
    <aside className="fixed top-0 left-0 w-[var(--sidebar-width)] h-screen overflow-y-auto bg-[var(--color-bg-elevated)] border-r-2 border-[var(--color-border)] flex flex-col z-50 shadow-[4px_0_24px_rgba(0,0,0,0.3)]">
      {/* Brand */}
      <div className="px-5 pt-7 pb-5 border-b border-[var(--color-border)]">
        <div className="font-mono text-[10px] font-medium tracking-[0.15em] uppercase text-[var(--color-text-secondary)] mb-1.5">
          DesignDev Workspace
        </div>
        <Link
          to="/"
          className="block no-underline hover:no-underline"
          onMouseEnter={handleBrandEnter}
          onMouseLeave={handleBrandLeave}
        >
          <div className="flex items-center gap-2">
            <div className="font-[family-name:var(--font-heading)] text-[18px] font-bold text-[var(--color-heading)] leading-tight">
              Design<span className="text-[var(--color-accent)]">Dev</span>
            </div>
            <SparklesIcon ref={brandIconRef} size={16} className="text-[var(--color-accent)] opacity-60" />
          </div>
        </Link>
        <div className="inline-flex items-center gap-[5px] mt-2 px-2 py-[2px] bg-[var(--color-accent-dim)] border border-[rgba(52,211,153,0.25)] rounded-full font-mono text-[10px] text-[var(--color-accent)]">
          <span className="w-1.5 h-1.5 bg-current rounded-full animate-pulse-dot" />
          5 MCPs Active
        </div>
      </div>

      {/* Search trigger */}
      <div className="px-4 pt-4 pb-2">
        <button
          type="button"
          onClick={openSearch}
          onMouseEnter={handleSearchEnter}
          onMouseLeave={handleSearchLeave}
          className="w-full flex items-center gap-2 px-3 py-[6px] bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-[var(--radius-sm)] transition-all duration-150 hover:border-[rgba(52,211,153,0.3)] cursor-pointer group"
        >
          <MagnifyingGlassIcon ref={searchIconRef} size={13} className="text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] transition-colors" />
          <span className="text-[12px] text-[var(--color-text-secondary)] font-mono">Search...</span>
          <kbd className="ml-auto px-1 py-px bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded text-[9px] font-mono text-[var(--color-text-muted)]">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3">
        {navSections.map((section) => (
          <div key={section.label}>
            <div className="font-mono text-[10px] font-medium tracking-[0.14em] uppercase text-[var(--color-text-secondary)] px-5 pt-5 pb-2">
              {section.label}
            </div>
            <div className="space-y-px">
              {section.items.map((item) => (
                <NavLink key={item.to} item={item} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Resources */}
      <div className="border-t border-[var(--color-border)] px-5 py-4">
        <div className="font-mono text-[10px] font-medium tracking-[0.14em] uppercase text-[var(--color-text-secondary)] mb-2">
          Resources
        </div>
        <div className="space-y-px">
          <ResourceLink
            href="/UNNODE_DEEP_DIVE.html"
            icon={BookOpenIcon as AnimatedIcon}
            label="UNNode Deep Dive"
          />
          <ResourceLink
            href="https://github.com/willbnu/DesignDev"
            icon={ArrowTopRightOnSquareIcon as AnimatedIcon}
            label="GitHub"
          />
        </div>
      </div>
    </aside>
  );
}
