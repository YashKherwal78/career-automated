import * as React from "react";
import type { DsStep } from "./Stepper";

/** Horizontal step flow (e.g. AI Understanding parsing progress). */
export function DsFlowSteps({ steps }: { steps: DsStep[] }) {
  return (
    <div className="flex items-start">
      {steps.map((s, i) => {
        const isDone = s.status === "done";
        const isActive = s.status === "active";
        const bg = isDone
          ? "var(--ds-sage-tint-18)"
          : isActive
            ? "var(--ds-accent-primary)"
            : "var(--ds-surface-card)";
        const border = isDone
          ? "var(--ds-accent-success)"
          : isActive
            ? "var(--ds-accent-primary)"
            : "var(--ds-border-strong)";
        const inner = isDone
          ? "var(--ds-accent-success)"
          : isActive
            ? "#FFFDFA"
            : "var(--ds-border-strong)";
        const labelColor = isDone || isActive ? "var(--ds-text-primary)" : "var(--ds-text-faint)";
        return (
          <div
            key={i}
            className="flex items-center"
            style={{ flex: i === steps.length - 1 ? "0 0 auto" : 1 }}
          >
            <div className="flex flex-col items-center gap-2 flex-shrink-0">
              <div
                className="flex items-center justify-center rounded-full"
                style={{ width: 34, height: 34, background: bg, border: `2px solid ${border}` }}
              >
                <div className="rounded-full" style={{ width: 8, height: 8, background: inner }} />
              </div>
              <div
                className="text-[length:var(--ds-text-base)] font-semibold whitespace-nowrap"
                style={{ color: labelColor }}
              >
                {s.label}
              </div>
            </div>
            {i < steps.length - 1 && (
              <div
                className="mx-2 mb-[22px]"
                style={{
                  flex: 1,
                  height: 2,
                  background: isDone ? "var(--ds-accent-success)" : "var(--ds-border-default)",
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
