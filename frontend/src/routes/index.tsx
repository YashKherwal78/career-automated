import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { generateMetadata } from "../lib/seo";
import { useAuth } from "../lib/auth";
import { DsLogo } from "../components/ds/Logo";
import { DsNavLink } from "../components/ds/NavLink";
import { DsButton } from "../components/ds/Button";
import { DsStatCard } from "../components/ds/StatCard";
import { DsEcosystemCard } from "../components/ds/EcosystemCard";
import { DsPricingCard } from "../components/ds/PricingCard";
import { DsFaqItem } from "../components/ds/FaqItem";
import { DsReveal } from "../components/ds/Reveal";

export const Route = createFileRoute("/")({
  head: () => generateMetadata("/"),
  component: Landing,
});

const PIPELINE_ROWS = [
  { initial: "S", role: "Backend Engineer", company: "Stripe", match: "94%", avatarBg: "#635BFF" },
  { initial: "N", role: "Product Engineer", company: "Notion", match: "91%", avatarBg: "#2F2A26" },
  {
    initial: "L",
    role: "Full-stack Engineer",
    company: "Linear",
    match: "88%",
    avatarBg: "#5E5CE6",
  },
];

const ECOSYSTEMS = [
  {
    eyebrow: "Resume intelligence",
    headline: "You'll never wonder if you applied with the right resume.",
    desc: "Every application goes out tailored to the role — rewritten from what's already true about you, reviewed before it's sent. Never generic, never a guess.",
    tags: ["Parsing", "Tailoring", "Review"],
    iconBg: "var(--ds-lavender-tint-14)",
    iconColor: "var(--ds-lavender-500)",
  },
  {
    eyebrow: "Discovery",
    headline: "The right opportunities won't pass you by.",
    desc: "We watch company career pages and job boards around the clock, so a role doesn't disappear before you even see it. You don't have to remember to check back.",
    tags: ["Matching", "Company tracking", "Alerts"],
    iconBg: "var(--ds-brand-orange-tint-10)",
    iconColor: "var(--ds-accent-primary)",
  },
  {
    eyebrow: "Automation",
    headline: "Always know where every opportunity stands.",
    desc: "Forms filled, follow-ups drafted, every application logged the moment it happens. Nothing depends on you remembering to check, to send, or to follow up.",
    tags: ["Autofill", "Tracking", "Follow-ups"],
    iconBg: "var(--ds-sage-tint-12)",
    iconColor: "var(--ds-accent-success)",
  },
];

const FAQS = [
  {
    q: "Will my resume look like AI wrote it?",
    a: "No. It only reorganizes and rephrases what's already true about you — never invented, never generic.",
  },
  {
    q: "Is my data safe?",
    a: "Yes. Nothing is shared with any company until you personally approve that exact application.",
  },
  {
    q: "Does this actually work?",
    a: "People using CareerAutomated miss fewer deadlines and hear back more often — because nothing sits forgotten in a tab.",
  },
  { q: "Can I cancel anytime?", a: "Always. One click, no calls, no forms." },
];

function Landing() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && user) {
      navigate({ to: "/dashboard" });
    }
  }, [user, isLoading, navigate]);

  const [openFaq, setOpenFaq] = useState(0);
  const [mockStart, setMockStart] = useState(0);
  const [mockApplying, setMockApplying] = useState(false);

  useEffect(() => {
    const t = setInterval(() => {
      setMockApplying(true);
      setTimeout(() => {
        setMockStart((s) => (s + 1) % PIPELINE_ROWS.length);
        setMockApplying(false);
      }, 900);
    }, 4200);
    return () => clearInterval(t);
  }, []);

  const mockCards = [0, 1, 2].map((i) => {
    const src = PIPELINE_ROWS[(mockStart + i) % PIPELINE_ROWS.length];
    const isFront = i === 0;
    const applying = isFront && mockApplying;
    return { ...src, i, applying };
  });

  return (
    <div
      style={{
        position: "relative",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
        background: "var(--ds-surface-page)",
        lineHeight: 1.5,
        overflowX: "hidden",
      }}
    >
      <div
        style={{
          position: "fixed",
          top: -120,
          left: 120,
          width: 520,
          height: 520,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(232,93,44,0.18), transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: "fixed",
          top: 280,
          right: -140,
          width: 460,
          height: 460,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(139,123,192,0.14), transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />
      <div
        style={{
          position: "fixed",
          bottom: -160,
          left: "40%",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(217,164,65,0.12), transparent 70%)",
          filter: "blur(70px)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      {/* Sticky nav */}
      <div
        className="flex items-center justify-between"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          padding: "18px clamp(20px,4vw,64px)",
          background: "rgba(251,247,241,0.82)",
          backdropFilter: "blur(var(--ds-blur-nav))",
          borderBottom: "1px solid var(--ds-border-hairline)",
        }}
      >
        <Link to="/">
          <DsLogo size="sm" />
        </Link>
        <div className="flex items-center gap-7">
          <DsNavLink href="#pipeline">Product</DsNavLink>
          <DsNavLink href="#pricing">Pricing</DsNavLink>
          <DsNavLink href="#story">About</DsNavLink>
          <DsNavLink to="/signin" emphasis>
            Sign in
          </DsNavLink>
          <DsButton asChild variant="dark" size="md">
            <Link to="/signup">Get started</Link>
          </DsButton>
        </div>
      </div>

      {/* Hero */}
      <div
        className="flex flex-col items-center text-center mx-auto"
        style={{
          position: "relative",
          zIndex: 1,
          gap: 34,
          padding: "clamp(100px,15vw,180px) clamp(20px,6vw,64px) clamp(100px,13vw,150px)",
          maxWidth: 1180,
        }}
      >
        <div
          className="inline-flex items-center gap-2 font-semibold"
          style={{
            background: "var(--ds-brand-orange-tint-08)",
            color: "var(--ds-brand-orange-text)",
            fontSize: 13,
            padding: "7px 14px",
            borderRadius: "var(--ds-radius-pill)",
          }}
        >
          <span
            className="rounded-full bg-[var(--ds-accent-primary)]"
            style={{ width: 6, height: 6 }}
          />
          So opportunity doesn't depend on a good week
        </div>
        <h1
          className="font-[var(--ds-font-display)]"
          style={{
            fontWeight: 500,
            fontSize: "var(--ds-display-2xl)",
            lineHeight: 1.04,
            letterSpacing: "var(--ds-tracking-tight)",
            margin: 0,
            maxWidth: 1000,
          }}
        >
          Nothing falls through.
          <br />
          Not because of you.
        </h1>
        <p
          style={{
            fontSize: "var(--ds-text-3xl)",
            color: "var(--ds-ink-500)",
            maxWidth: 600,
            margin: 0,
          }}
        >
          Procrastination, overwhelm, one missed deadline — none of it should cost you the right
          opportunity. CareerAutomated finds the roles worth applying to, tailors your resume for
          each one, and keeps every application moving quietly in the background. You review. You
          approve. Nothing else is asked of you.
        </p>
        <div className="flex flex-wrap justify-center gap-3.5">
          <DsButton asChild variant="primary">
            <Link to="/signup">Get started free</Link>
          </DsButton>
          <DsButton asChild variant="outline">
            <a href="#pipeline">See how it works</a>
          </DsButton>
        </div>
      </div>

      {/* Product showcase */}
      <div
        id="pipeline"
        style={{ padding: "clamp(48px,6vw,72px) clamp(20px,6vw,64px) clamp(80px,9vw,120px)" }}
      >
        <div className="text-center mx-auto" style={{ maxWidth: 640, marginBottom: 40 }}>
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 13,
              letterSpacing: "var(--ds-tracking-wider)",
              color: "var(--ds-brand-orange-text)",
              marginBottom: 12,
            }}
          >
            Inside CareerAutomated
          </div>
          <h2
            className="font-[var(--ds-font-display)] font-bold"
            style={{ fontSize: "clamp(28px,3.4vw,38px)", margin: 0 }}
          >
            Everything in one place, so nothing gets lost.
          </h2>
        </div>
        <DsReveal
          style={{
            maxWidth: 1080,
            margin: "0 auto",
            position: "relative",
            zIndex: 1,
            background: "rgba(255,253,250,0.45)",
            backdropFilter: "blur(22px) saturate(160%)",
            border: "1px solid rgba(255,255,255,0.55)",
            borderRadius: "var(--ds-radius-2xl)",
            boxShadow: "var(--ds-shadow-modal)",
            overflow: "hidden",
          }}
        >
          <div
            className="flex items-center gap-2.5"
            style={{ padding: "14px 18px", borderBottom: "1px solid var(--ds-border-hairline)" }}
          >
            <div className="flex gap-1.5">
              <span
                className="rounded-full bg-[var(--ds-border-strong)]"
                style={{ width: 10, height: 10 }}
              />
              <span
                className="rounded-full bg-[var(--ds-border-strong)]"
                style={{ width: 10, height: 10 }}
              />
              <span
                className="rounded-full bg-[var(--ds-border-strong)]"
                style={{ width: 10, height: 10 }}
              />
            </div>
            <div
              className="ml-2"
              style={{
                fontSize: 12.5,
                color: "var(--ds-ink-400)",
                background: "var(--ds-cream-200)",
                padding: "5px 14px",
                borderRadius: "var(--ds-radius-pill)",
              }}
            >
              app.careerautomated.com
            </div>
          </div>
          <div className="flex">
            <div
              className="flex flex-col items-center gap-2.5"
              style={{
                width: 72,
                flexShrink: 0,
                borderRight: "1px solid var(--ds-border-hairline)",
                padding: "18px 10px",
              }}
            >
              <div
                className="flex items-center justify-center rounded-[9px] bg-[var(--ds-brand-orange-tint-10)]"
                style={{ width: 32, height: 32 }}
              >
                <div
                  className="grid gap-0.5"
                  style={{ gridTemplateColumns: "5px 5px", gridTemplateRows: "5px 5px" }}
                >
                  <div className="rounded-[1px] bg-[var(--ds-accent-primary)]" />
                  <div className="rounded-[1px] bg-[var(--ds-accent-primary)]" />
                  <div className="rounded-[1px] bg-[var(--ds-accent-primary)]" />
                  <div className="rounded-[1px] bg-[var(--ds-accent-primary)]" />
                </div>
              </div>
              <div
                className="rounded-[9px] bg-[var(--ds-cream-200)]"
                style={{ width: 32, height: 32 }}
              />
              <div
                className="rounded-[9px] bg-[var(--ds-cream-200)]"
                style={{ width: 32, height: 32 }}
              />
            </div>
            <div className="flex-1 min-w-0" style={{ padding: "22px 24px" }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 18 }}>
                <span
                  className="font-[var(--ds-font-display)] font-semibold"
                  style={{ fontSize: 16 }}
                >
                  Your jobs
                </span>
                <span
                  className="font-bold"
                  style={{
                    fontSize: 11.5,
                    color: "var(--ds-brand-orange-text)",
                    background: "var(--ds-brand-orange-tint-08)",
                    padding: "4px 10px",
                    borderRadius: "var(--ds-radius-pill)",
                  }}
                >
                  Auto Apply on
                </span>
              </div>
              <div
                style={{ position: "relative", overflow: "hidden", height: 108, marginBottom: 22 }}
              >
                {mockCards.map((r) => (
                  <div
                    key={r.i}
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: 140,
                      transform: `translateX(${r.i * 152}px)`,
                      transition:
                        "transform 0.7s cubic-bezier(0.4,0,0.2,1), background 0.4s ease, border-color 0.4s ease",
                      background: r.applying ? "rgba(200,224,190,0.55)" : "rgba(255,255,255,0.6)",
                      border: `1px solid ${r.applying ? "rgba(107,143,94,0.4)" : "rgba(255,255,255,0.7)"}`,
                      borderRadius: "var(--ds-radius-lg)",
                      padding: 12,
                      backdropFilter: "blur(10px)",
                    }}
                  >
                    <div className="flex items-center gap-1.5" style={{ marginBottom: 10 }}>
                      <div
                        className="flex items-center justify-center flex-shrink-0 text-white font-bold rounded-[5px]"
                        style={{ width: 18, height: 18, background: r.avatarBg, fontSize: 9 }}
                      >
                        {r.initial}
                      </div>
                      <div
                        className="whitespace-nowrap overflow-hidden text-ellipsis"
                        style={{ fontSize: 10.5, color: "var(--ds-ink-500)" }}
                      >
                        {r.company}
                      </div>
                    </div>
                    <div
                      className="font-[var(--ds-font-display)] font-semibold"
                      style={{ fontSize: 12.5, lineHeight: 1.25, marginBottom: 8 }}
                    >
                      {r.role}
                    </div>
                    <div
                      className="inline-block font-bold"
                      style={{
                        fontSize: 10,
                        padding: "2px 6px",
                        borderRadius: "var(--ds-radius-pill)",
                        color: r.applying ? "var(--ds-sage-text)" : "var(--ds-ink-600)",
                        background: r.applying
                          ? "var(--ds-sage-tint-12)"
                          : "var(--ds-surface-tint)",
                      }}
                    >
                      {r.applying ? "Applied ✓" : r.match}
                    </div>
                  </div>
                ))}
              </div>
              <div
                className="grid gap-2.5"
                style={{ gridTemplateColumns: "repeat(auto-fit,minmax(110px,1fr))" }}
              >
                <DsStatCard value="12" delta="+4" label="Applications" />
                <DsStatCard value="18%" delta="+6%" label="Response rate" />
                <DsStatCard value="3" delta="+2" label="Interviews" />
              </div>
            </div>
          </div>
        </DsReveal>
      </div>

      {/* Ecosystem */}
      <div
        style={{
          background: "var(--ds-surface-page-alt)",
          padding: "clamp(64px,8vw,100px) clamp(20px,6vw,64px)",
        }}
      >
        <DsReveal
          className="grid gap-6 mx-auto"
          style={{ maxWidth: 1160, gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))" }}
        >
          {ECOSYSTEMS.map((e) => (
            <DsEcosystemCard key={e.eyebrow} {...e} />
          ))}
        </DsReveal>
      </div>

      {/* Manifesto */}
      <div
        id="story"
        className="text-center"
        style={{
          background: "var(--ds-ink-800)",
          color: "var(--ds-text-on-dark)",
          padding: "clamp(56px,7vw,84px) clamp(20px,6vw,64px)",
        }}
      >
        <DsReveal className="mx-auto" style={{ maxWidth: 760 }}>
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 13,
              letterSpacing: "var(--ds-tracking-wider)",
              color: "var(--ds-dark-accent)",
              marginBottom: 16,
            }}
          >
            Why we built this
          </div>
          <h2
            className="font-[var(--ds-font-display)] mx-auto"
            style={{
              fontWeight: 500,
              fontSize: "clamp(21px,2.4vw,26px)",
              lineHeight: 1.55,
              letterSpacing: "-0.005em",
              margin: 0,
              maxWidth: 600,
            }}
          >
            Hiring rewards speed and prestige more than ability. We can't fix that. But we can make
            sure you never lose an opportunity to a missed deadline, a bad week, or a form you
            didn't have the energy to finish.
          </h2>
        </DsReveal>
      </div>

      {/* Pricing */}
      <div id="pricing" style={{ padding: "clamp(64px,8vw,96px) clamp(20px,6vw,64px)" }}>
        <div className="text-center mx-auto" style={{ maxWidth: 480, marginBottom: 44 }}>
          <h2
            className="font-[var(--ds-font-display)] font-bold"
            style={{ fontSize: "clamp(24px,3vw,32px)", margin: "0 0 10px" }}
          >
            Simple pricing.
          </h2>
          <p style={{ fontSize: 15.5, color: "var(--ds-ink-500)", margin: 0 }}>
            Start free. Upgrade only once it's clearly buying back your time.
          </p>
        </div>
        <DsReveal
          className="grid gap-5.5 mx-auto"
          style={{ gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", maxWidth: 1000 }}
        >
          <DsPricingCard
            name="Free"
            price="₹0"
            features={[
              "Continuous job matching",
              "3 tailored resumes / month",
              "Manual review & send",
            ]}
            cta="Get started"
            href="/signup"
          />
          <DsPricingCard
            name="Pro"
            price="₹500"
            period="/month"
            features={[
              "Unlimited tailored resumes",
              "One-click ATS autofill",
              "Smart follow-ups & tracking",
            ]}
            cta="Start Pro"
            recommended
            href="/pricing"
          />
          <DsPricingCard
            name="Custom"
            price="Let's talk"
            features={[
              "Dedicated placement strategist",
              "Multi-profile & team management",
              "Priority company outreach",
            ]}
            cta="Contact us"
            href="/contact"
          />
        </DsReveal>
      </div>

      {/* FAQ */}
      <div
        style={{
          background: "var(--ds-surface-page-alt)",
          padding: "clamp(56px,7vw,84px) clamp(20px,6vw,64px)",
        }}
      >
        <div className="mx-auto" style={{ maxWidth: 680 }}>
          <h2
            className="font-[var(--ds-font-display)] font-bold text-center"
            style={{ fontSize: "clamp(22px,2.6vw,28px)", margin: "0 0 28px" }}
          >
            A few honest answers.
          </h2>
          <DsReveal className="flex flex-col gap-2.5">
            {FAQS.map((f, i) => (
              <DsFaqItem
                key={f.q}
                question={f.q}
                answer={f.a}
                isOpen={openFaq === i}
                onToggle={() => setOpenFaq(openFaq === i ? -1 : i)}
              />
            ))}
          </DsReveal>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="text-center" style={{ padding: "clamp(64px,8vw,96px) clamp(20px,6vw,64px)" }}>
        <DsReveal>
          <h2
            className="font-[var(--ds-font-display)] font-bold"
            style={{ fontSize: "var(--ds-display-xl)", margin: "0 0 16px" }}
          >
            Stop worrying about what you might have missed.
          </h2>
          <p style={{ fontSize: 16, color: "var(--ds-ink-500)", margin: "0 0 28px" }}>
            Free to start. Two minutes, and it's already watching for you.
          </p>
          <DsButton asChild variant="primary">
            <Link to="/signup">Get started free</Link>
          </DsButton>
        </DsReveal>
      </div>

      {/* Footer */}
      <div
        className="flex flex-wrap justify-between gap-8"
        style={{
          borderTop: "1px solid var(--ds-border-default)",
          padding: "48px clamp(20px,6vw,64px) 32px",
        }}
      >
        <div style={{ maxWidth: 320 }}>
          <div className="flex items-center gap-2.5" style={{ marginBottom: 12 }}>
            <DsLogo size="sm" />
          </div>
          <div style={{ fontSize: 14, color: "var(--ds-ink-450)" }}>
            So a missed deadline never costs you the right opportunity.
          </div>
        </div>
        <div className="flex flex-wrap gap-10" style={{ fontSize: 14 }}>
          <a href="#pipeline" style={{ color: "var(--ds-ink-500)" }}>
            Product
          </a>
          <a href="#pricing" style={{ color: "var(--ds-ink-500)" }}>
            Pricing
          </a>
          <Link to="/legal" hash="privacy" style={{ color: "var(--ds-ink-500)" }}>
            Privacy
          </Link>
          <Link to="/legal" hash="terms" style={{ color: "var(--ds-ink-500)" }}>
            Terms
          </Link>
        </div>
      </div>
    </div>
  );
}
