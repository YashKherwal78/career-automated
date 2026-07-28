import * as React from "react";

export type DsStepStatus = "done" | "active" | "pending";
export interface DsStep {
  label: React.ReactNode;
  status: DsStepStatus;
}

/** Vertical stepper (Resume Builder / onboarding progress). */
export function DsStepper({ steps }: { steps: DsStep[] }) {
  return (
    <div className="flex flex-col">
      {steps.map((s, i) => {
        const isDone = s.status === "done";
        const isActive = s.status === "active";
        const dotBg = isDone
          ? "var(--ds-accent-success)"
          : isActive
            ? "var(--ds-accent-primary)"
            : "var(--ds-surface-card)";
        const dotBorder = isDone
          ? "var(--ds-accent-success)"
          : isActive
            ? "var(--ds-accent-primary)"
            : "var(--ds-border-strong)";
        const dotInner = isDone || isActive ? "#FFFDFA" : "var(--ds-border-strong)";
        const labelColor = isDone || isActive ? "var(--ds-text-primary)" : "var(--ds-text-faint)";
        return (
          <div key={i} className="flex gap-4">
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className="flex items-center justify-center rounded-full"
                style={{
                  width: 30,
                  height: 30,
                  background: dotBg,
                  border: `2px solid ${dotBorder}`,
                }}
              >
                <div
                  className="rounded-full"
                  style={{ width: 7, height: 7, background: dotInner }}
                />
              </div>
              {i < steps.length - 1 && (
                <div
                  className="mt-1"
                  style={{
                    width: 2,
                    flex: 1,
                    minHeight: 20,
                    background: isDone ? "var(--ds-accent-success)" : "var(--ds-border-strong)",
                  }}
                />
              )}
            </div>
            <div className="pt-[5px] pb-5">
              <div
                className="text-[length:var(--ds-text-md)] font-semibold"
                style={{ color: labelColor }}
              >
                {s.label}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
