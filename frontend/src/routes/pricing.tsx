import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Check, ArrowRight, Sparkles } from "lucide-react";
import { Section, SectionHeading } from "@/components/primitives/section";
import { FadeIn, Stagger, StaggerItem } from "@/components/primitives/motion";

import { generateMetadata } from "../lib/seo";

export const Route = createFileRoute("/pricing")({
  head: () => generateMetadata("/pricing", {
    title: "Pricing Plans",
    description: "Simple pricing. Free plan to start. Upgrade only when it pays for itself in time saved.",
  }),
  component: Pricing,
});


type Cycle = "monthly" | "yearly";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: { monthly: 0, yearly: 0 },
    tagline: "Everything you need to try it seriously.",
    features: [
      "Up to 10 job matches / month",
      "Manual applications with AI-tailored resume",
      "Weekly digest of new roles",
      "Basic application tracker",
    ],
    cta: "Get started",
    highlight: false,
  },
  {
    id: "pro",
    name: "Pro",
    price: { monthly: 19, yearly: 15 },
    tagline: "Full workflow. Real-time matches. Unlimited resumes.",
    features: [
      "Unlimited job matches, real-time",
      "AI-tailored resume + cover letter per role",
      "One-click ATS autofill (Greenhouse, Lever, Ashby, Workday)",
      "Application CRM with reminders",
      "Smart follow-up drafts",
    ],
    cta: "Start Pro",
    highlight: true,
  },
  {
    id: "premium",
    name: "Premium",
    price: { monthly: 49, yearly: 39 },
    tagline: "Priority discovery, deeper tailoring, concierge support.",
    features: [
      "Everything in Pro",
      "Priority job discovery (roles surface first)",
      "Deeper AI tailoring with per-role research",
      "Interview prep briefs for each application",
      "Priority human support",
    ],
    cta: "Go Premium",
    highlight: false,
  },
];

const COMPARE: { row: string; free: string | boolean; pro: string | boolean; premium: string | boolean }[] = [
  { row: "Job matches", free: "10 / month", pro: "Unlimited", premium: "Unlimited, priority" },
  { row: "Match frequency", free: "Weekly digest", pro: "Real-time", premium: "Real-time, priority queue" },
  { row: "AI resume tailoring", free: "Basic", pro: "Per-role", premium: "Per-role + research" },
  { row: "Cover letter drafting", free: false, pro: true, premium: true },
  { row: "ATS autofill", free: false, pro: true, premium: true },
  { row: "Application tracker", free: "Basic", pro: "Full CRM", premium: "Full CRM" },
  { row: "Follow-up drafts", free: false, pro: true, premium: true },
  { row: "Interview prep briefs", free: false, pro: false, premium: true },
  { row: "Support", free: "Community", pro: "Email", premium: "Priority" },
];

const FAQ = [
  { q: "Can I switch plans anytime?", a: "Yes — upgrade, downgrade, or cancel from your dashboard in one click. Downgrades take effect at the end of the current billing period." },
  { q: "What's included in the free plan?", a: "Enough to see if this works for you: real matching, AI-tailored resumes, and a weekly digest. No credit card required." },
  { q: "Do you offer a yearly discount?", a: "Yes — yearly billing is about 20% off the monthly price. Toggle above to compare." },
  { q: "Is there a student or non-profit discount?", a: "Write to us. If you're a student or building non-profit impact, we'll find something that works." },
  { q: "Do you offer team or enterprise plans?", a: "Yes — for career services teams, bootcamps, and placement cells. Contact us for a quote." },
];

function Pricing() {
  const [cycle, setCycle] = useState<Cycle>("monthly");

  return (
    <>
      {/* Header */}
      <Section className="pt-24 pb-8 md:pt-32 md:pb-8">
        <FadeIn>
          <SectionHeading
            align="center"
            eyebrow="Pricing"
            title="Simple pricing. No surprises."
            description="Start free. Upgrade when the time you save is worth more than the plan costs."
          />
        </FadeIn>

        <FadeIn delay={0.1} className="mt-10">
          <div className="mx-auto flex w-fit items-center rounded-full border hairline bg-white p-1 text-sm">
            <ToggleBtn active={cycle === "monthly"} onClick={() => setCycle("monthly")}>
              Monthly
            </ToggleBtn>
            <ToggleBtn active={cycle === "yearly"} onClick={() => setCycle("yearly")}>
              Yearly <span className="ml-1.5 rounded-full bg-[color:var(--peach-soft)] px-2 py-0.5 text-[10px] font-medium text-ink">Save 20%</span>
            </ToggleBtn>
          </div>
        </FadeIn>
      </Section>

      {/* Plans */}
      <Section className="py-8">
        <Stagger className="grid gap-6 lg:grid-cols-3">
          {PLANS.map((p) => {
            const price = p.price[cycle];
            return (
              <StaggerItem key={p.id}>
                <div
                  className={`relative h-full rounded-2xl border p-8 ${
                    p.highlight
                      ? "border-transparent bg-ink text-white shadow-[0_30px_80px_-30px_oklch(0.2_0.02_260/0.35)]"
                      : "border-[color:var(--border)] bg-white"
                  }`}
                >
                  {p.highlight ? (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full peach-gradient px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-ink">
                      <span className="inline-flex items-center gap-1"><Sparkles className="h-3 w-3" /> Most popular</span>
                    </div>
                  ) : null}

                  <div className={`text-sm font-medium ${p.highlight ? "text-white" : "text-ink"}`}>{p.name}</div>

                  <div className="mt-4 flex items-baseline gap-1">
                    <div className="font-display text-5xl tracking-tight">${price}</div>
                    <div className={`text-sm ${p.highlight ? "text-white/60" : "text-ink-soft"}`}>
                      {price === 0 ? "forever" : cycle === "monthly" ? "/mo" : "/mo, billed yearly"}
                    </div>
                  </div>

                  <p className={`mt-3 text-sm ${p.highlight ? "text-white/70" : "text-ink-soft"}`}>{p.tagline}</p>

                  <ul className="mt-7 space-y-3">
                    {p.features.map((f) => (
                      <li key={f} className={`flex items-start gap-2.5 text-sm ${p.highlight ? "text-white/85" : "text-ink"}`}>
                        <Check className={`mt-0.5 h-4 w-4 shrink-0 ${p.highlight ? "text-[color:var(--peach)]" : "text-[color:var(--peach-deep)]"}`} />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>

                  <Link
                    to="/signup"
                    className={`mt-8 flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium transition ${
                      p.highlight
                        ? "bg-white text-ink hover:bg-white/90"
                        : "bg-ink text-white hover:bg-ink/90"
                    }`}
                  >
                    {p.cta} <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </StaggerItem>
            );
          })}
        </Stagger>
      </Section>

      {/* Comparison */}
      <Section className="py-20">
        <SectionHeading align="center" title="Compare plans" />
        <div className="mt-10 overflow-x-auto rounded-2xl border hairline bg-white">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-[color:var(--surface-muted)]">
              <tr>
                <th className="px-6 py-4 text-left font-medium text-ink">Feature</th>
                <th className="px-6 py-4 text-left font-medium text-ink">Free</th>
                <th className="px-6 py-4 text-left font-medium text-ink">Pro</th>
                <th className="px-6 py-4 text-left font-medium text-ink">Premium</th>
              </tr>
            </thead>
            <tbody>
              {COMPARE.map((row, i) => (
                <tr key={row.row} className={i % 2 ? "bg-secondary/40" : ""}>
                  <td className="px-6 py-4 font-medium text-ink">{row.row}</td>
                  <Cell v={row.free} />
                  <Cell v={row.pro} />
                  <Cell v={row.premium} />
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      {/* Enterprise */}
      <Section className="py-8">
        <div className="rounded-2xl border hairline bg-white p-8 md:flex md:items-center md:justify-between md:gap-8">
          <div>
            <div className="text-sm font-medium text-ink">For teams & institutions</div>
            <h3 className="mt-2 font-display text-2xl tracking-tight text-ink md:text-3xl">
              CareerAutomated for career services and bootcamps
            </h3>
            <p className="mt-2 max-w-xl text-sm text-ink-soft">
              Bulk onboarding, admin dashboards, and dedicated support. Bring CareerAutomated to your students or cohort.
            </p>
          </div>
          <Link to="/contact" className="btn-dark mt-6 text-sm md:mt-0">
            Contact sales <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Section>

      {/* FAQ */}
      <Section className="py-20">
        <SectionHeading align="center" title="Pricing FAQ" />
        <div className="mx-auto mt-10 max-w-3xl divide-y hairline overflow-hidden rounded-2xl border hairline bg-white">
          {FAQ.map((f) => (
            <details key={f.q} className="group px-6 py-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[15px] font-medium text-ink">
                {f.q}
                <span className="grid h-6 w-6 place-items-center rounded-full border hairline text-ink-soft transition group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-[15px] leading-relaxed text-ink-soft">{f.a}</p>
            </details>
          ))}
        </div>
      </Section>

      {/* Final CTA */}
      <Section className="py-24">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="font-display text-4xl leading-[1.05] tracking-tight md:text-5xl">
            Try it free. Decide later.
          </h2>
          <p className="mt-4 text-[16px] text-ink-soft">Two minutes to set up. Cancel anytime.</p>
          <Link to="/signup" className="btn-dark mt-8 text-sm">
            Get started free <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Section>
    </>
  );
}

function ToggleBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-full px-4 py-1.5 text-sm font-medium transition ${
        active ? "bg-ink text-white" : "text-ink-soft hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function Cell({ v }: { v: string | boolean }) {
  if (typeof v === "boolean") {
    return (
      <td className="px-6 py-4">
        {v ? <Check className="h-4 w-4 text-[color:var(--peach-deep)]" /> : <span className="text-ink-soft">—</span>}
      </td>
    );
  }
  return <td className="px-6 py-4 text-ink-soft">{v}</td>;
}
