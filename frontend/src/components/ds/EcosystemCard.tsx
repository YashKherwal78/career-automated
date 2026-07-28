import * as React from "react";

export interface DsEcosystemCardProps {
  eyebrow: React.ReactNode;
  headline: React.ReactNode;
  desc: React.ReactNode;
  tags: string[];
  iconColor?: string;
  iconBg?: string;
}

export function DsEcosystemCard({
  eyebrow,
  headline,
  desc,
  tags,
  iconColor = "var(--ds-accent-primary)",
  iconBg = "var(--ds-brand-orange-tint-10)",
}: DsEcosystemCardProps) {
  return (
    <div className="p-[30px] bg-[var(--ds-surface-card)] rounded-[var(--ds-radius-xl)]">
      <div
        className="flex items-center justify-center mb-5 rounded-[var(--ds-radius-md)]"
        style={{ width: 36, height: 36, background: iconBg }}
      >
        <div style={{ width: 13, height: 13, borderRadius: 4, background: iconColor }} />
      </div>
      <div className="text-[length:var(--ds-text-sm)] font-bold tracking-[var(--ds-tracking-wide)] uppercase text-[var(--ds-text-secondary)] mb-2.5">
        {eyebrow}
      </div>
      <div
        className="font-[var(--ds-font-display)] font-bold tracking-[var(--ds-tracking-snug)] mb-2.5"
        style={{ fontSize: 21, lineHeight: 1.25 }}
      >
        {headline}
      </div>
      <div className="text-[length:var(--ds-text-lg)] text-[var(--ds-ink-500)] leading-[var(--ds-leading-relaxed)] mb-5">
        {desc}
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((t) => (
          <span
            key={t}
            className="text-[12.5px] font-medium text-[var(--ds-ink-600)] bg-[var(--ds-cream-300)] px-3 py-1.5 rounded-[var(--ds-radius-pill)]"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}
