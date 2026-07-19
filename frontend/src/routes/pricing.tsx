import { createFileRoute, Link } from "@tanstack/react-router";
import { Check, ArrowRight, Sparkles } from "lucide-react";
import { Section, SectionHeading } from "@/components/primitives/section";
import { FadeIn, Stagger, StaggerItem } from "@/components/primitives/motion";
import { generateMetadata } from "../lib/seo";

export const Route = createFileRoute("/pricing")({
  head: () => generateMetadata("/pricing", {
    title: "Pricing Plans",
    description: "Simple pricing. Free plan to start. Upgrade only when you need custom organization limits.",
  }),
  component: Pricing,
});

const PLANS = [
  {
    id: "free",
    name: "Free Plan",
    price: "₹0",
    tagline: "High-agency matching with a robust monthly allocation.",
    features: [
      "500 applications / month",
      "AI-tailored resumes & profiles",
      "Real-time opportunity matching",
      "Distraction-free builder workspace",
    ],
    cta: "Start Free",
    highlight: true,
  },
  {
    id: "custom",
    name: "Custom",
    price: "Custom",
    tagline: "For career bootcamps, universities, and placement cells.",
    features: [
      "Bulk student onboarding",
      "Unlimited applications & tailoring",
      "Admin monitoring dashboards",
      "Dedicated integration support",
    ],
    cta: "Contact Sales",
    highlight: false,
  },
];

const FAQ = [
  { q: "Is it really free?", a: "Yes — the Free Plan gives you up to 500 applications matched and tailored every single month. No credit card required." },
  { q: "Do you offer student discounts?", a: "The 500/month plan is already completely free for all users, which is more than enough for most job seekers." },
  { q: "Do you offer team or enterprise plans?", a: "Yes — for career services teams, bootcamps, and placement cells. Contact us for custom limits." },
];

function Pricing() {
  return (
    <>
      {/* Header */}
      <Section className="pt-24 pb-8 md:pt-32 md:pb-8">
        <FadeIn>
          <SectionHeading
            align="center"
            eyebrow="Pricing"
            title="Simple pricing. No surprises."
            description="Start free. Upgrade only when you need custom limits."
          />
        </FadeIn>
      </Section>

      {/* Plans */}
      <Section className="py-8">
        <Stagger className="grid gap-6 md:grid-cols-2 max-w-4xl mx-auto">
          {PLANS.map((p) => {
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
                    <div className="font-display text-5xl tracking-tight">{p.price}</div>
                    <div className={`text-sm ${p.highlight ? "text-white/60" : "text-ink-soft"}`}>
                      {p.price === "₹0" ? "/month" : ""}
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
                    to={p.id === "custom" ? "/contact" : "/signup"}
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
