import * as React from "react";
import { cn } from "@/lib/utils";

export interface DsInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  forgotHref?: string;
}

export const DsInput = React.forwardRef<HTMLInputElement, DsInputProps>(
  ({ className, label, forgotHref, ...props }, ref) => {
    return (
      <div>
        {label && (
          <div className="flex justify-between mb-1.5">
            <label className="text-[length:var(--ds-text-sm)] font-semibold text-[var(--ds-ink-700)]">
              {label}
            </label>
            {forgotHref && (
              <a
                href={forgotHref}
                className="text-[12.5px] font-medium text-[var(--ds-accent-primary)]"
              >
                Forgot?
              </a>
            )}
          </div>
        )}
        <input
          ref={ref}
          className={cn(
            "w-full px-3.5 py-3 rounded-[var(--ds-radius-md)] border border-[var(--ds-border-medium)] text-[length:var(--ds-text-md)] font-[var(--ds-font-body)] bg-[var(--ds-surface-card)] text-[var(--ds-text-primary)] outline-none focus:border-[var(--ds-accent-primary)] focus:ring-[3px] focus:ring-[var(--ds-brand-orange-tint-16)]",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);
DsInput.displayName = "DsInput";
