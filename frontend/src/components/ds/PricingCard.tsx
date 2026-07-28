import * as React from "react";
import { Link } from "@tanstack/react-router";

export interface DsPricingCardProps {
  name: string;
  price: string;
  period?: string;
  features: string[];
  cta: string;
  recommended?: boolean;
  onCta?: () => void;
  href?: string;
}

export function DsPricingCard({
  name,
  price,
  period,
  features,
  cta,
  recommended = false,
  onCta,
  href,
}: DsPricingCardProps) {
  const dark = recommended;
  const ctaClassName =
    "block w-full text-center py-3 rounded-[var(--ds-radius-md)] font-semibold text-[14.5px] active:scale-[0.98] transition-transform cursor-pointer";
  const ctaStyle: React.CSSProperties = {
    background: dark ? "var(--ds-accent-primary)" : "var(--ds-border-default)",
    color: dark ? "var(--ds-text-on-brand)" : "var(--ds-text-primary)",
  };
  return (
    <div
      className="p-8 rounded-[var(--ds-radius-2xl)] relative"
      style={{
        background: dark ? "var(--ds-ink-800)" : "var(--ds-surface-card)",
        border: dark ? "1px solid var(--ds-ink-800)" : "1px solid var(--ds-border-default)",
      }}
    >
      {recommended && (
        <div
          className="absolute bg-[var(--ds-accent-primary)] text-[var(--ds-text-on-brand)] font-bold rounded-[var(--ds-radius-pill)]"
          style={{ top: -12, left: 32, fontSize: 11, padding: "4px 12px" }}
        >
          Recommended
        </div>
      )}
      <div
        className="flex items-center justify-center mb-[18px] rounded-[var(--ds-radius-md)]"
        style={{
          width: 36,
          height: 36,
          background: dark ? "var(--ds-brand-orange-tint-18)" : "var(--ds-brand-orange-tint-10)",
        }}
      >
        <div
          style={{
            width: 13,
            height: 13,
            borderRadius: dark ? "50%" : 4,
            background: "var(--ds-accent-primary)",
          }}
        />
      </div>
      <div
        className="font-[var(--ds-font-display)] font-semibold mb-1.5"
        style={{ fontSize: 16, color: dark ? "var(--ds-text-on-dark)" : "var(--ds-text-primary)" }}
      >
        {name}
      </div>
      <div className="flex items-baseline gap-1 mb-4">
        <span
          className="font-[var(--ds-font-display)] font-bold"
          style={{
            fontSize: 34,
            color: dark ? "var(--ds-text-on-dark)" : "var(--ds-text-primary)",
          }}
        >
          {price}
        </span>
        <span
          className="text-[13.5px]"
          style={{ color: dark ? "var(--ds-text-on-dark-muted)" : "var(--ds-text-secondary)" }}
        >
          {period}
        </span>
      </div>
      <div className="flex flex-col gap-2.5 mb-6">
        {features.map((f) => (
          <div
            key={f}
            className="flex items-center gap-2 text-[13.5px]"
            style={{ color: dark ? "var(--ds-text-on-dark-muted)" : "var(--ds-text-secondary)" }}
          >
            <div
              className="flex-shrink-0 rounded-full bg-[var(--ds-accent-primary)]"
              style={{ width: 6, height: 6 }}
            />
            {f}
          </div>
        ))}
      </div>
      {href ? (
        <Link to={href} onClick={onCta} className={ctaClassName} style={ctaStyle}>
          {cta}
        </Link>
      ) : (
        <button type="button" onClick={onCta} className={ctaClassName} style={ctaStyle}>
          {cta}
        </button>
      )}
    </div>
  );
}
