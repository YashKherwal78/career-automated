import * as React from "react";

export interface DsLogoProps {
  size?: "sm" | "md";
  withWordmark?: boolean;
  dark?: boolean;
  className?: string;
}

const DIMS = {
  sm: { w: 24, h: 20, bar: 3.5, barH: 14 },
  md: { w: 26, h: 22, bar: 4, barH: 16 },
};

/** CareerAutomated logo mark — CSS-drawn (rotated bar pair), no image asset. */
export function DsLogo({ size = "md", withWordmark = true, dark = false, className }: DsLogoProps) {
  const dims = DIMS[size];
  return (
    <div className={`flex items-center gap-2.5 ${className ?? ""}`}>
      <div className="relative flex-shrink-0" style={{ width: dims.w, height: dims.h }}>
        <div
          className="absolute rounded-[2px] bg-[var(--ds-accent-primary)]"
          style={{
            bottom: 2,
            left: dims.w / 2 - dims.bar - 1,
            width: dims.bar,
            height: dims.barH,
            transformOrigin: "bottom center",
            transform: "rotate(28deg)",
          }}
        />
        <div
          className="absolute rounded-[2px] bg-[var(--ds-accent-primary)]"
          style={{
            bottom: 2,
            right: dims.w / 2 - dims.bar - 1,
            width: dims.bar,
            height: dims.barH,
            transformOrigin: "bottom center",
            transform: "rotate(-28deg)",
          }}
        />
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
