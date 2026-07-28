import * as React from "react";
import { cn } from "@/lib/utils";

export interface DsTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export const DsTextarea = React.forwardRef<HTMLTextAreaElement, DsTextareaProps>(
  ({ className, label, style, ...props }, ref) => {
    return (
      <div>
        {label && <div className="text-[length:var(--ds-text-md)] font-semibold mb-3">{label}</div>}
        <textarea
          ref={ref}
          style={{ minHeight: 140, ...style }}
          className={cn(
            "w-full resize-y border border-[var(--ds-border-default)] rounded-[var(--ds-radius-md)] px-3.5 py-3 font-[var(--ds-font-body)] text-[length:var(--ds-text-base)] text-[var(--ds-text-primary)] bg-[var(--ds-surface-page)] outline-none focus:border-[var(--ds-accent-primary)]",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);
DsTextarea.displayName = "DsTextarea";
