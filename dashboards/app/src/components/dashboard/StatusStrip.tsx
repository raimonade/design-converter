import { useRef, useCallback } from 'react';
import type { MCPServer } from '@/content/mcp-servers';
import { ServerStackIcon } from '@heroicons-animated/react';

interface IconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}

interface StatusStripProps {
  servers: MCPServer[];
}

export function StatusStrip({ servers }: StatusStripProps) {
  const iconRef = useRef<IconHandle>(null);
  const handleMouseEnter = useCallback(() => iconRef.current?.startAnimation(), []);
  const handleMouseLeave = useCallback(() => iconRef.current?.stopAnimation(), []);

  return (
    <div
      className="flex flex-wrap gap-2 p-3 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-[var(--radius-md)]"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="flex items-center gap-1.5 mr-2 text-[var(--color-text-muted)]">
        <ServerStackIcon ref={iconRef} size={14} />
        <span className="font-mono text-[10px] font-medium tracking-[0.1em] uppercase text-[var(--color-text-muted)]">
          MCP Status
        </span>
      </div>
      {servers.map((server) => (
        <div
          key={server.id}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-full transition-colors hover:border-[rgba(52,211,153,0.3)]"
        >
          <span
            className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
              server.status === 'active'
                ? 'bg-[var(--color-accent)] animate-pulse-dot'
                : 'bg-[var(--color-amber)]'
            }`}
          />
          <span className="font-mono text-[10px] text-[var(--color-text-secondary)] whitespace-nowrap">
            {server.name}
          </span>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
            {server.tools}
          </span>
        </div>
      ))}
    </div>
  );
}
