import * as React from "react";
import { DsAvatar } from "./Avatar";

export interface DsListRowProps {
  initial: string;
  avatarColor?: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  rightTop?: React.ReactNode;
  rightBottom?: React.ReactNode;
  rightToneSuccess?: boolean;
  className?: string;
}

export function DsListRow({
  initial,
  avatarColor,
  title,
  subtitle,
  rightTop,
  rightBottom,
  rightToneSuccess = true,
  className,
}: DsListRowProps) {
  return (
    <div
      className={`flex items-center gap-3 px-3 py-2.5 rounded-[var(--ds-radius-lg)] bg-[var(--ds-cream-100)] ${className ?? ""}`}
    >
      <DsAvatar initial={initial} color={avatarColor} />
      <div className="flex-1 min-w-0">
        <div className="text-[length:var(--ds-text-md)] font-semibold whitespace-nowrap overflow-hidden text-ellipsis">
          {title}
        </div>
        <div className="text-[length:var(--ds-text-base)] text-[var(--ds-text-secondary)]">
          {subtitle}
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <div
          className="text-[length:var(--ds-text-sm)] font-bold"
          style={{
            color: rightToneSuccess ? "var(--ds-accent-success)" : "var(--ds-text-primary)",
          }}
        >
          {rightTop}
        </div>
        <div className="text-[length:var(--ds-text-xs)] text-[var(--ds-text-secondary)]">
          {rightBottom}
        </div>
      </div>
    </div>
  );
}
