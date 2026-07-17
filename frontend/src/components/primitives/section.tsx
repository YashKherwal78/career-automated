import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";
import { Container } from "./container";

interface SectionProps extends HTMLAttributes<HTMLElement> {
  bleed?: boolean;
  bg?: "default" | "muted" | "ink";
  containerClassName?: string;
}

export function Section({
  className,
  bleed = false,
  bg = "default",
  containerClassName,
  children,
  ...props
}: SectionProps) {
  const bgClass =
    bg === "muted" ? "bg-[color:var(--surface-muted)]" : bg === "ink" ? "bg-ink text-white" : "";
  return (
    <section className={cn("py-24 md:py-32", bgClass, className)} {...props}>
      {bleed ? children : <Container className={containerClassName}>{children}</Container>}
    </section>
  );
}

interface HeadingProps {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  align?: "left" | "center";
  className?: string;
}

export function SectionHeading({ eyebrow, title, description, align = "left", className }: HeadingProps) {
  return (
    <div className={cn(align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl", className)}>
      {eyebrow ? (
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-soft">
          {eyebrow}
        </div>
      ) : null}
      <h2 className="mt-3 font-display text-4xl leading-[1.05] tracking-tight text-ink md:text-5xl">
        {title}
      </h2>
      {description ? (
        <p className="mt-5 text-[16px] leading-relaxed text-ink-soft md:text-[17px]">{description}</p>
      ) : null}
    </div>
  );
}
