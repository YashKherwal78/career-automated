import * as React from "react";
import { Link, type LinkComponentProps } from "@tanstack/react-router";

export interface DsNavLinkProps extends Omit<Partial<LinkComponentProps>, "className" | "style"> {
  href?: string;
  emphasis?: boolean;
  children: React.ReactNode;
}

/** Nav link — plain `<a>` for same-page anchors (`href="#section"`), TanStack `Link` for routes (`to="/signin"`). */
export function DsNavLink({ href, emphasis = false, children, ...linkProps }: DsNavLinkProps) {
  const style: React.CSSProperties = {
    color: "var(--ds-text-primary)",
    fontSize: "14.5px",
    fontWeight: emphasis ? "var(--ds-weight-semibold)" : "var(--ds-weight-medium)",
    opacity: emphasis ? 1 : 0.8,
  };
  const className = "hover:opacity-100 transition-opacity";

  if (href) {
    return (
      <a href={href} className={className} style={style}>
        {children}
      </a>
    );
  }

  return (
    <Link {...(linkProps as LinkComponentProps)} className={className} style={style}>
      {children}
    </Link>
  );
}
