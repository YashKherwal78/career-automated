import * as React from "react";

export interface DsJobCardProps {
  initial: string;
  avatarColor: string;
  company: string;
  role: string;
  match: React.ReactNode;
  salary?: React.ReactNode;
  location?: React.ReactNode;
  progress?: number;
  tinted?: boolean;
  onClick?: () => void;
}

export function DsJobCard({
  initial,
  avatarColor,
  company,
  role,
  match,
  salary,
  location,
  progress = 0,
  tinted = false,
  onClick,
}: DsJobCardProps) {
  return (
    <div
      role={onClick ? "button" : undefined}
      onClick={onClick}
      className="p-[18px] rounded-[var(--ds-radius-xl)] transition-colors cursor-pointer"
      style={{
        background: tinted ? "var(--ds-sage-tint-16)" : "var(--ds-surface-card)",
        border: `1px solid ${tinted ? "var(--ds-accent-success)" : "var(--ds-border-default)"}`,
      }}
    >
      <div className="flex items-center gap-2 mb-3.5">
        <div
          className="flex items-center justify-center flex-shrink-0 text-white font-bold rounded-[6px]"
          style={{ width: 24, height: 24, background: avatarColor, fontSize: 11 }}
        >
          {initial}
        </div>
        <div className="text-xs font-semibold text-[var(--ds-ink-500)] overflow-hidden text-ellipsis whitespace-nowrap">
          {company}
        </div>
      </div>
      <div
        className="font-[var(--ds-font-display)] font-semibold mb-4"
        style={{ fontSize: 17, lineHeight: 1.3, minHeight: 44 }}
      >
        {role}
      </div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[11px] font-bold text-[var(--ds-accent-success)] bg-[var(--ds-sage-tint-12)] px-[7px] py-0.5 rounded-[var(--ds-radius-pill)]">
          {match}
        </span>
        <span className="text-[11.5px] text-[var(--ds-ink-450)]">{salary}</span>
      </div>
      <div className="text-[11px] text-[var(--ds-ink-400)] mb-3.5">{location}</div>
      <div className="h-[3px] bg-[var(--ds-border-default)] rounded-[2px] overflow-hidden">
        <div
          className="h-full bg-[var(--ds-accent-success)] rounded-[2px] transition-[width] duration-[3s] ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
