import {
  CheckCircleIcon,
  BeakerIcon,
  CodeBracketIcon,
  SignalIcon,
  BoltIcon,
} from '@heroicons-animated/react';
import { useRef, useCallback, type ForwardRefExoticComponent, type RefAttributes } from 'react';

interface IconHandle {
  startAnimation: () => void;
  stopAnimation: () => void;
}

interface ActivityItem {
  icon: ForwardRefExoticComponent<{ size?: number; className?: string } & RefAttributes<IconHandle>>;
  message: string;
  time: string;
  status: 'success' | 'info' | 'warning';
}

const activities: ActivityItem[] = [
  { icon: CheckCircleIcon, message: 'All 5 MCP servers connected', time: 'Just now', status: 'success' },
  { icon: BeakerIcon, message: '146 tests passing across all adapters', time: '2m ago', status: 'success' },
  { icon: SignalIcon, message: 'Bridge WebSocket active on port 9223', time: '5m ago', status: 'success' },
  { icon: CodeBracketIcon, message: 'IR: 15 dataclasses, 13 enums loaded', time: '8m ago', status: 'info' },
  { icon: BoltIcon, message: 'Last smoke test: all endpoints OK', time: '15m ago', status: 'success' },
];

const statusColors: Record<string, string> = {
  success: 'var(--color-accent)',
  info: 'var(--color-blue)',
  warning: 'var(--color-amber)',
};

function ActivityRow({ item, isLast }: { item: ActivityItem; isLast: boolean }) {
  const Icon = item.icon;
  const color = statusColors[item.status];
  const iconRef = useRef<IconHandle>(null);

  const handleMouseEnter = useCallback(() => iconRef.current?.startAnimation(), []);
  const handleMouseLeave = useCallback(() => iconRef.current?.stopAnimation(), []);

  return (
    <div
      className="flex items-start gap-3 py-3 border-b border-[var(--color-border-subtle)] last:border-0"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="relative flex-shrink-0 mt-0.5">
        <div
          className="w-[3px] absolute left-[9px] top-[22px] bottom-[-12px]"
          style={{
            background: !isLast ? 'var(--color-border-subtle)' : 'transparent',
          }}
        />
        <div
          className="w-5 h-5 rounded-full flex items-center justify-center"
          style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color }}
        >
          <Icon ref={iconRef} size={12} />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--color-text)] mb-0 leading-snug">{item.message}</p>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">{item.time}</span>
      </div>
    </div>
  );
}

export function ActivityFeed() {
  return (
    <div className="space-y-0">
      {activities.map((item, idx) => (
        <ActivityRow key={idx} item={item} isLast={idx === activities.length - 1} />
      ))}
    </div>
  );
}
