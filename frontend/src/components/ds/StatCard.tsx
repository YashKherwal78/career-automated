import * as React from "react";

export interface DsStatCardProps {
  value: React.ReactNode;
  delta?: React.ReactNode;
  label: React.ReactNode;
  className?: string;
}

export function DsStatCard({ value, delta, label, className }: DsStatCardProps) {
  return (
    <div
      className={`bg-[var(--ds-surface-tint)] rounded-[var(--ds-radius-lg)] p-3.5 ${className ?? ""}`}
    >
      <div className="font-[var(--ds-font-display)] font-bold" style={{ fontSize: 21 }}>
        {value}
      </div>
      {delta && (
        <div className="text-[11px] font-semibold text-[var(--ds-accent-success)] my-[2px] mb-[3px]">
          {delta}
        </div>
      )}
      <div className="text-[11.5px] text-[var(--ds-text-secondary)]">{label}</div>
    </div>
  );
}
