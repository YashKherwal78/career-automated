import { Link } from "@tanstack/react-router";
import { Container } from "./primitives/container";

export function SiteFooter() {
  return (
    <footer className="border-t hairline bg-background">
      <Container className="py-16">
        <div className="grid gap-12 md:grid-cols-4">
          <div className="md:col-span-2">
            <Link to="/" className="flex items-center gap-2 font-medium">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-ink text-[10px] font-semibold text-white">CA</span>
              <span>CareerAutomated</span>
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink-soft">
              The AI career operating system. Spend less time applying, more time interviewing.
            </p>
          </div>

          <div>
            <div className="text-sm font-medium text-ink">Product</div>
            <ul className="mt-4 space-y-3 text-sm text-ink-soft">
              <li><Link to="/" className="hover:text-ink">Overview</Link></li>
              <li><Link to="/pricing" className="hover:text-ink">Pricing</Link></li>
              <li><Link to="/signup" className="hover:text-ink">Sign up</Link></li>
              <li><Link to="/faq" className="hover:text-ink">FAQ</Link></li>
            </ul>
          </div>

          <div>
            <div className="text-sm font-medium text-ink">Company</div>
            <ul className="mt-4 space-y-3 text-sm text-ink-soft">
              <li><Link to="/about" className="hover:text-ink">About</Link></li>
              <li><Link to="/contact" className="hover:text-ink">Contact</Link></li>
              <li><Link to="/privacy" className="hover:text-ink">Privacy</Link></li>
              <li><Link to="/terms" className="hover:text-ink">Terms</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-14 flex flex-col items-start justify-between gap-4 border-t hairline pt-6 text-xs text-ink-soft md:flex-row md:items-center">
          <div>© {new Date().getFullYear()} CareerAutomated. All rights reserved.</div>
          <div className="flex gap-5">
            <a href="https://linkedin.com" target="_blank" rel="noreferrer" className="hover:text-ink">LinkedIn</a>
            <a href="https://twitter.com" target="_blank" rel="noreferrer" className="hover:text-ink">Twitter</a>
          </div>
        </div>
      </Container>
    </footer>
  );
}
