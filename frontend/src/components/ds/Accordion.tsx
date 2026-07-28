import * as React from "react";

export function DsAccordionSection({
  title,
  summary,
  icon,
  defaultOpen = false,
  children,
}: {
  title: React.ReactNode;
  summary?: React.ReactNode;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div
      style={{
        background: "var(--ds-surface-card)",
        border: "1px solid var(--ds-border-default)",
        borderRadius: "var(--ds-radius-lg)",
        marginBottom: 12,
        overflow: "hidden",
      }}
    >
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => e.key === "Enter" && setOpen((o) => !o)}
        className="flex items-center gap-3.5 cursor-pointer"
        style={{ padding: "16px 20px" }}
      >
        {icon && (
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "var(--ds-surface-tint)",
              fontSize: 16,
            }}
          >
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div style={{ fontSize: 15, fontWeight: 600, color: "var(--ds-text-primary)" }}>
            {title}
          </div>
          {summary && (
            <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)", marginTop: 1 }}>
              {summary}
            </div>
          )}
        </div>
        <div
          style={{
            transform: open ? "rotate(90deg)" : "none",
            transition: "transform 200ms linear",
            color: "var(--ds-ink-400)",
          }}
        >
          ›
        </div>
      </div>
      {open && (
        <div
          style={{
            padding: "0 20px 20px",
            borderTop: "1px solid var(--ds-border-default)",
            paddingTop: 16,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
