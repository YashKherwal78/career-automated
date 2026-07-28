import * as React from "react";

export interface DsLogoProps {
  /** Mark box size in px — each screen in the handoff uses its own exact size (20/26/30/33/37...). */
  box?: number;
  /** Wordmark font size in px. */
  wordmark?: number;
  weight?: 500 | 600 | 700;
  withWordmark?: boolean;
  dark?: boolean;
  className?: string;
}

// Fixed ratios confirmed identical across every size the handoff uses (20/26/30/33/37px):
// radius 0.2714, ring 0.6287, ringOffset 0.2157, dot 0.257, dotOffset 0.1762 of the box size.
export function DsLogo({
  box = 30,
  wordmark = 16,
  weight = 700,
  withWordmark = true,
  dark = false,
  className,
}: DsLogoProps) {
  const squareBg = "var(--ds-ink-900)";
  const radius = box * 0.2714;
  const ringSize = box * 0.6287;
  const ringOffset = box * 0.2157;
  const dotSize = box * 0.257;
  const dotOffset = box * 0.1762;

  return (
    <div className={`flex items-center gap-1.5 ${className ?? ""}`}>
      <div
        className="relative flex-shrink-0"
        style={{ width: box, height: box, borderRadius: radius, background: squareBg }}
      >
        <div
          className="absolute rounded-full"
          style={{
            top: ringOffset,
            left: ringOffset,
            width: ringSize,
            height: ringSize,
            background: "var(--ds-accent-primary)",
          }}
        >
          <div
            className="absolute rounded-full"
            style={{
              top: dotOffset,
              left: dotOffset,
              width: dotSize,
              height: dotSize,
              background: squareBg,
            }}
          />
        </div>
      </div>
      {withWordmark && (
        <span
          className="font-[var(--ds-font-display)] tracking-[var(--ds-tracking-snug)]"
          style={{
            fontSize: wordmark,
            fontWeight: weight,
            color: dark ? "var(--ds-text-on-dark)" : "var(--ds-text-primary)",
          }}
        >
          CareerAutomated
        </span>
      )}
    </div>
  );
}
