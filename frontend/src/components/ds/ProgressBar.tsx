import * as React from "react";

export interface DsProgressBarProps {
  progress?: number;
  color?: string;
  height?: number;
  className?: string;
}

export function DsProgressBar({
  progress = 0,
  color = "var(--ds-accent-success)",
  height = 3,
  className,
}: DsProgressBarProps) {
  return (
    <div
      className={`bg-[var(--ds-border-default)] rounded-[2px] overflow-hidden ${className ?? ""}`}
      style={{ height }}
    >
      <div
        className="h-full rounded-[2px] transition-[width] duration-[3s] ease-linear"
        style={{ width: `${progress}%`, background: color }}
      />
    </div>
  );
}
