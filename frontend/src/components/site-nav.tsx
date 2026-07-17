import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Container } from "./primitives/container";

const NAV_LINKS = [
  { to: "/" as const, label: "Product", exact: true },
  { to: "/pricing" as const, label: "Pricing" },
  { to: "/about" as const, label: "About" },
  { to: "/faq" as const, label: "FAQ" },
];

export function SiteNav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled ? "border-b hairline bg-background/80 backdrop-blur-xl" : "border-b border-transparent bg-transparent"
      }`}
    >
      <Container className="flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-medium tracking-tight">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-ink text-[10px] font-semibold text-white">
            CA
          </span>
          <span>CareerAutomated</span>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-ink-soft md:flex">
          {NAV_LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={l.exact ? { exact: true } : undefined}
              activeProps={{ className: "text-ink" }}
              className="transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Link to="/signup" className="text-sm text-ink-soft transition-colors hover:text-ink">
            Sign in
          </Link>
          <Link to="/signup" className="btn-dark text-sm">
            Get started
          </Link>
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          className="grid h-9 w-9 place-items-center rounded-full border hairline bg-white md:hidden"
          aria-label="Toggle menu"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </Container>

      {open ? (
        <div className="border-t hairline bg-background/95 backdrop-blur-xl md:hidden">
          <Container className="flex flex-col gap-3 py-5 text-sm">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className="py-1 text-ink-soft hover:text-ink"
              >
                {l.label}
              </Link>
            ))}
            <div className="mt-3 flex gap-2">
              <Link to="/signup" onClick={() => setOpen(false)} className="btn-ghost-ink flex-1 text-sm">
                Sign in
              </Link>
              <Link to="/signup" onClick={() => setOpen(false)} className="btn-dark flex-1 text-sm">
                Get started
              </Link>
            </div>
          </Container>
        </div>
      ) : null}
    </header>
  );
}
