interface BarChartItem {
  label: string;
  value: number;
  formattedValue: string;
  color: string;
}

interface BarChartProps {
  items: BarChartItem[];
}

export function BarChart({ items }: BarChartProps) {
  const maxValue = Math.max(...items.map((i) => i.value));

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const percent = (item.value / maxValue) * 100;
        return (
          <div key={item.label} className="group">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-mono text-[12px] text-[var(--color-text-secondary)] group-hover:text-[var(--color-heading)] transition-colors">
                {item.label}
              </span>
              <span className="font-mono text-[12px] font-medium" style={{ color: item.color }}>
                {item.formattedValue}
              </span>
            </div>
            <div className="h-[6px] bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full animate-bar-fill"
                style={{
                  width: `${percent}%`,
                  background: item.color,
                  opacity: 0.85,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
