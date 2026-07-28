import * as React from "react";

export interface DsLogoProps {
  size?: "sm" | "md";
  withWordmark?: boolean;
  dark?: boolean;
  className?: string;
}

// Proportions match the design handoff's logo mark exactly (see e.g. Settings.dc.html
// sidebar: 30x30 square, rx 8.14, ring at 6.47/18.86, punched dot at 5.29/7.71).
const DIMS = {
  sm: { box: 26, radius: 7.05, ringSize: 16.34, ringOffset: 5.61, dotSize: 6.68, dotOffset: 4.59 },
  md: { box: 30, radius: 8.14, ringSize: 18.86, ringOffset: 6.47, dotSize: 7.71, dotOffset: 5.29 },
};

/** CareerAutomated logo mark — CSS-drawn rounded square with an orange ring and a punched-through center dot. */
export function DsLogo({ size = "md", withWordmark = true, dark = false, className }: DsLogoProps) {
  const d = DIMS[size];
  const squareBg = "var(--ds-ink-900)";
  return (
    <div className={`flex items-center gap-1.5 ${className ?? ""}`}>
      <div
        className="relative flex-shrink-0"
        style={{ width: d.box, height: d.box, borderRadius: d.radius, background: squareBg }}
      >
        <div
          className="absolute rounded-full"
          style={{
            top: d.ringOffset,
            left: d.ringOffset,
            width: d.ringSize,
            height: d.ringSize,
            background: "var(--ds-accent-primary)",
          }}
        >
          <div
            className="absolute rounded-full"
            style={{
              top: d.dotOffset,
              left: d.dotOffset,
              width: d.dotSize,
              height: d.dotSize,
              background: squareBg,
            }}
          />
        </div>
      </div>
      {withWordmark && (
        <span
          className="font-[var(--ds-font-display)] font-bold tracking-[var(--ds-tracking-snug)]"
          style={{
            fontSize: size === "sm" ? 16 : 18,
            color: dark ? "var(--ds-text-on-dark)" : "var(--ds-text-primary)",
          }}
        >
          CareerAutomated
        </span>
      )}
    </div>
  );
}
