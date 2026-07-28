import * as React from "react";

export type DsBadgeTone = "neutral" | "orange" | "success" | "dark";

export interface DsBadgeProps {
  children: React.ReactNode;
  tone?: DsBadgeTone;
  pill?: boolean;
  className?: string;
}

const toneStyle: Record<DsBadgeTone, React.CSSProperties> = {
  neutral: { background: "var(--ds-surface-tint)", color: "var(--ds-ink-600)" },
  orange: { background: "var(--ds-brand-orange-tint-08)", color: "var(--ds-brand-orange-text)" },
  success: { background: "var(--ds-sage-tint-12)", color: "var(--ds-sage-text)" },
  dark: { background: "var(--ds-ink-800)", color: "var(--ds-text-on-dark)" },
};

export function DsBadge({ children, tone = "neutral", pill = true, className }: DsBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[length:var(--ds-text-sm)] font-semibold px-3 py-[5px] ${className ?? ""}`}
      style={{
        borderRadius: pill ? "var(--ds-radius-pill)" : "var(--ds-radius-xs)",
        ...toneStyle[tone],
      }}
    >
      {children}
    </span>
  );
}
