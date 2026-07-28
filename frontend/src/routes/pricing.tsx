import { createFileRoute, Link } from "@tanstack/react-router";
import { generateMetadata } from "../lib/seo";
import { DsPricingCard } from "../components/ds/PricingCard";

export const Route = createFileRoute("/pricing")({
  head: () =>
    generateMetadata("/pricing", {
      title: "Pricing Plans",
      description: "Simple pricing. Start free. Upgrade only if it's saving you real time.",
    }),
  component: Pricing,
});

function Pricing() {
  return (
    <div
      style={{
        position: "relative",
        minHeight: "100vh",
        background: "var(--ds-surface-page)",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
      }}
    >
      <div
        className="pointer-events-none fixed"
        style={{
          top: -120,
          left: 120,
          width: 520,
          height: 520,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(232,93,44,0.12), transparent 70%)",
          filter: "blur(60px)",
          zIndex: 0,
        }}
      />
      <div
        className="relative mx-auto"
        style={{
          zIndex: 1,
          maxWidth: 1040,
          padding: "clamp(28px,5vw,56px) clamp(20px,5vw,32px) 80px",
        }}
      >
        <Link
          to="/dashboard/settings"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13.5,
            fontWeight: 600,
            color: "var(--ds-ink-500)",
            marginBottom: 32,
          }}
        >
          ← Back to settings
        </Link>

        <div className="text-center mx-auto" style={{ maxWidth: 480, marginBottom: 48 }}>
          <h1
            className="font-[var(--ds-font-display)] font-bold"
            style={{ fontSize: "clamp(26px,3.4vw,36px)", margin: "0 0 10px" }}
          >
            Simple pricing.
          </h1>
          <p style={{ fontSize: 15.5, color: "var(--ds-ink-500)", margin: 0 }}>
            Start free. Upgrade only if it's saving you real time.
          </p>
        </div>

        <div
          className="grid gap-5.5"
          style={{ gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))" }}
        >
          <DsPricingCard
            name="Free"
            price="₹0"
            features={[
              "Continuous job matching",
              "3 tailored resumes / month",
              "Manual review & send",
            ]}
            cta="Current plan"
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
            cta="Upgrade to Pro"
            recommended
            href="/checkout"
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
        </div>
      </div>
    </div>
  );
}
