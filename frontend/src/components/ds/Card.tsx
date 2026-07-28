import * as React from "react";
import { cn } from "@/lib/utils";

export interface DsCardProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: number;
  hoverable?: boolean;
}

export const DsCard = React.forwardRef<HTMLDivElement, DsCardProps>(
  ({ className, padding = 22, hoverable = false, style, ...props }, ref) => {
    return (
      <div
        ref={ref}
        style={{ padding, ...style }}
        className={cn(
          "bg-[var(--ds-surface-card)] border border-[var(--ds-border-default)] rounded-[var(--ds-radius-xl)]",
          hoverable &&
            "transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-[var(--ds-shadow-card)]",
          className,
        )}
        {...props}
      />
    );
  },
);
DsCard.displayName = "DsCard";
