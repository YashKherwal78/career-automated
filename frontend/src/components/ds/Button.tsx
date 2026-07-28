import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

export type DsButtonVariant = "primary" | "dark" | "outline" | "ghost";
export type DsButtonSize = "md" | "lg";

const variantClasses: Record<DsButtonVariant, string> = {
  primary:
    "bg-[var(--ds-accent-primary)] text-[var(--ds-text-on-brand)] shadow-[var(--ds-shadow-button-glow-sm)] hover:bg-[var(--ds-accent-primary-hover)]",
  dark: "bg-[var(--ds-ink-800)] text-[var(--ds-text-on-dark)] hover:bg-[#3a2c1d]",
  outline:
    "bg-transparent border-[1.5px] border-[var(--ds-border-medium)] text-[var(--ds-text-primary)] hover:border-[var(--ds-border-emphasis)]",
  ghost: "bg-[var(--ds-surface-tint)] text-[var(--ds-text-primary)] hover:bg-[var(--ds-cream-300)]",
};

const sizeClasses: Record<DsButtonSize, string> = {
  md: "px-5 py-3 text-[length:var(--ds-text-md)]",
  lg: "px-[30px] py-[15px] text-[length:var(--ds-text-xl)]",
};

export interface DsButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: DsButtonVariant;
  size?: DsButtonSize;
  asChild?: boolean;
}

/**
 * Design-system Button (CareerAutomated handoff). Presses compress
 * slightly per the mocks' "visual haptics" — see active:scale below.
 * Pass asChild to render as a Link/anchor with the same styling (Radix Slot).
 */
export const DsButton = React.forwardRef<HTMLButtonElement, DsButtonProps>(
  ({ className, variant = "primary", size = "lg", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-[var(--ds-radius-md)] font-[var(--ds-font-body)] font-semibold cursor-pointer border-none transition-[background,border-color,transform] duration-[var(--ds-duration-fast)] active:scale-[0.97] disabled:opacity-50 disabled:pointer-events-none",
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      />
    );
  },
);
DsButton.displayName = "DsButton";
