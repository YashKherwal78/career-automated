import * as React from "react";
import { Link, type LinkComponentProps } from "@tanstack/react-router";

export interface DsSidebarItemProps extends Omit<LinkComponentProps, "className" | "style"> {
  label: React.ReactNode;
  active?: boolean;
  shape?: "rect" | "circle";
  icon?: React.ReactNode;
}

export function DsSidebarItem({
  label,
  active = false,
  shape = "rect",
  icon,
  ...linkProps
}: DsSidebarItemProps) {
  const color = active ? "var(--ds-brand-orange-text)" : "var(--ds-ink-600)";
  return (
    <Link
      {...linkProps}
      className="flex items-center gap-3.5 px-4 py-3.5 rounded-[var(--ds-radius-lg)]"
      style={{
        background: active ? "var(--ds-brand-orange-tint-08)" : "transparent",
        color,
        fontSize: "var(--ds-text-md)",
        fontWeight: "var(--ds-weight-semibold)",
      }}
    >
      {icon ?? (
        <div
          className="flex-shrink-0"
          style={{
            width: 20,
            height: 20,
            borderRadius: shape === "circle" ? "50%" : "var(--ds-radius-xs)",
            border: `2px solid ${color}`,
          }}
        />
      )}
      {label}
    </Link>
  );
}
