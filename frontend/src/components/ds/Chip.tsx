import * as React from "react";

export interface DsChipProps {
  label: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}

export function DsChip({ label, active = false, onClick, className }: DsChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`cursor-pointer px-4 py-[11px] rounded-[var(--ds-radius-md)] text-[13.5px] font-semibold active:scale-[0.97] transition-transform ${className ?? ""}`}
      style={{
        background: active ? "var(--ds-ink-800)" : "var(--ds-surface-tint)",
        color: active ? "var(--ds-text-on-dark)" : "var(--ds-ink-700)",
      }}
    >
      {label}
    </button>
  );
}
