import { cn } from "@/lib/utils";
import { forwardRef, type ButtonHTMLAttributes, type AnchorHTMLAttributes, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "peach";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-50 disabled:pointer-events-none";

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-[13px]",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-[15px]",
};

const variants: Record<Variant, string> = {
  primary:
    "bg-ink text-white hover:bg-ink/90 shadow-[0_1px_0_oklch(1_0_0/0.08)_inset,0_10px_30px_-15px_oklch(0.16_0.012_260/0.5)]",
  peach:
    "text-ink border border-[color:var(--peach-deep)]/40 bg-[linear-gradient(135deg,oklch(0.94_0.05_55),oklch(0.85_0.11_45))] hover:-translate-y-px shadow-[0_1px_0_oklch(1_0_0/0.9)_inset,0_10px_24px_-12px_oklch(0.7_0.14_45/0.55)]",
  secondary:
    "border border-[color:var(--border)] bg-white text-ink hover:border-ink/30 hover:bg-secondary/60",
  ghost: "text-ink hover:bg-secondary/70",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leading?: ReactNode;
  trailing?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", size = "md", loading, leading, trailing, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cn(base, sizes[size], variants[variant], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
      ) : leading}
      {children}
      {!loading && trailing}
    </button>
  );
});

export interface LinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: Variant;
  size?: Size;
  leading?: ReactNode;
  trailing?: ReactNode;
}

export const LinkButton = forwardRef<HTMLAnchorElement, LinkButtonProps>(function LinkButton(
  { className, variant = "primary", size = "md", leading, trailing, children, ...props },
  ref,
) {
  return (
    <a ref={ref} className={cn(base, sizes[size], variants[variant], className)} {...props}>
      {leading}
      {children}
      {trailing}
    </a>
  );
});
