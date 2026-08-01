import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/faq")({
  head: () => ({
    meta: [
      { title: "FAQ — CareerAutomated" },
      { name: "description", content: "Answers to common questions about matching, data privacy, coverage and billing." },
      { property: "og:title", content: "FAQ — CareerAutomated" },
      { property: "og:description", content: "How CareerAutomated works, how your resume data is handled, which companies we cover, and how billing works." },
    ],
  }),
  component: FAQPage,
});

const SECTIONS = [
  {
    title: "Getting started",
    items: [
      { q: "How does matching work?", a: "We read your resume, extract skills, projects and experience, and continuously match you against openings on company career pages and ATS platforms. Every match includes a fit score so you know why we surfaced it." },
      { q: "How long until I see results?", a: "You'll usually see your first matches within minutes of uploading your resume. Real-time alerts start immediately for Pro; Free users get a weekly digest." },
      { q: "Do I need to pay to start?", a: "No. The Free plan is designed to be useful on its own. Pro is optional and adds real-time alerts and full coverage." },
    ],
  },
  {
    title: "Your data",
    items: [
      { q: "Is my resume kept private?", a: "Yes. We never share your resume with a company without your explicit permission. See our Privacy Policy for the full detail." },
      { q: "Do you share my data with companies?", a: "No. We match you to public job listings. You choose which roles to apply to. We do not send your resume to companies on your behalf without you asking." },
      { q: "Can I delete my account?", a: "Yes, any time, from your dashboard. Deletion removes your resume and personal data from our systems." },
    ],
  },
  {
    title: "Coverage",
    items: [
      { q: "Which companies and ATS platforms do you track?", a: "We track thousands of company career pages and major ATS platforms including Greenhouse, Lever, Ashby and Workday, with focus on companies hiring in India." },
      { q: "Do you cover my city or sector?", a: "Coverage is broadest for engineering and tech roles across major Indian hubs (Bengaluru, Hyderabad, Pune, NCR) and remote roles. We're actively expanding sector and geography coverage." },
      { q: "How often is data refreshed?", a: "We continuously monitor for changes. New openings usually show up the same day they're published." },
    ],
  },
  {
    title: "Billing",
    items: [
      { q: "How do I cancel?", a: "One click from your dashboard. You keep Pro access until the end of your billing period." },
      { q: "Refund policy?", a: "If Pro isn't a fit within the first 7 days, write to us and we'll refund you." },
    ],
  },
];

function FAQPage() {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return SECTIONS;
    return SECTIONS.map((s) => ({
      ...s,
      items: s.items.filter((i) => i.q.toLowerCase().includes(q) || i.a.toLowerCase().includes(q)),
    })).filter((s) => s.items.length > 0);
  }, [query]);

  return (
    <div>
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-x-0 top-[-10%] h-[420px] peach-glow" />
        <div className="mx-auto max-w-3xl px-6 pb-12 pt-24 text-center">
          <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">FAQ</div>
          <h1 className="mt-4 font-display text-5xl leading-tight md:text-6xl">
            Questions, <em className="italic">answered clearly</em>.
          </h1>
          <div className="mx-auto mt-8 flex max-w-md items-center gap-2 rounded-full border hairline bg-white px-4 py-2 shadow-sm">
            <Search className="h-4 w-4 text-ink-soft" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search questions"
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-ink-soft"
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 pb-24">
        <div className="space-y-10">
          {filtered.map((s) => (
            <div key={s.title}>
              <h2 className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">{s.title}</h2>
              <div className="mt-4 divide-y hairline rounded-3xl border hairline bg-white">
                {s.items.map((i) => (
                  <details key={i.q} className="group px-6 py-5">
                    <summary className="flex cursor-pointer items-center justify-between gap-6 text-sm font-medium">
                      {i.q}
                      <span className="text-ink-soft transition group-open:rotate-45">+</span>
                    </summary>
                    <p className="mt-3 text-sm leading-relaxed text-ink-soft">{i.a}</p>
                  </details>
                ))}
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="rounded-3xl border hairline bg-white p-10 text-center text-sm text-ink-soft">
              No matches. Try a different word — or <Link to="/contact" className="text-[color:var(--peach-deep)] underline underline-offset-2">ask us directly</Link>.
            </div>
          )}
        </div>

        <div className="mt-16 rounded-3xl border hairline bg-[color:var(--peach-soft)]/50 p-8 text-center">
          <h3 className="font-display text-2xl">Didn't find your answer?</h3>
          <Link to="/contact" className="btn-peach mt-4 text-sm">Contact support <ArrowRight className="h-4 w-4" /></Link>
        </div>
      </section>
    </div>
  );
}
