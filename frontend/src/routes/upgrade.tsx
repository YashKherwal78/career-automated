import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/upgrade")({
  head: () => ({ meta: [{ title: "Upgrade to Pro — CareerAutomated" }] }),
  component: Upgrade,
});

const FEATURES = [
  "Unlimited tailored resumes",
  "One-click ATS autofill",
  "Auto-apply queue",
  "Smart follow-ups & tracking",
];

function Upgrade() {
  return (
    <div
      className="flex items-center justify-center relative overflow-hidden"
      style={{
        minHeight: "100vh",
        padding: "40px 24px",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
      }}
    >
      <div
        className="pointer-events-none fixed"
        style={{
          top: -140,
          left: "15%",
          width: 480,
          height: 480,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(232,93,44,0.14), transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div className="relative z-10 text-center" style={{ width: "100%", maxWidth: 460 }}>
        <div
          className="mx-auto flex items-center justify-center"
          style={{
            width: 52,
            height: 52,
            borderRadius: 14,
            background: "var(--ds-brand-orange-tint-10)",
            marginBottom: 20,
            fontSize: 22,
          }}
        >
          ⚡
        </div>
        <div
          className="uppercase font-bold"
          style={{
            fontSize: 12.5,
            letterSpacing: "var(--ds-tracking-wide)",
            color: "var(--ds-brand-orange-text)",
            marginBottom: 10,
          }}
        >
          Pro feature
        </div>
        <h1
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: "clamp(24px,2.8vw,30px)", margin: "0 0 10px" }}
        >
          Auto-apply is a Pro feature
        </h1>
        <p
          style={{
            fontSize: 14.5,
            color: "var(--ds-ink-500)",
            lineHeight: 1.6,
            margin: "0 0 32px",
            maxWidth: 400,
            marginInline: "auto",
          }}
        >
          Upgrade to let CareerAutomated tailor and submit applications for you automatically, so
          the right roles never slip by.
        </p>

        <div
          className="text-left"
          style={{
            background: "var(--ds-surface-card)",
            border: "1px solid var(--ds-border-default)",
            borderRadius: "var(--ds-radius-xl)",
            padding: 28,
            marginBottom: 24,
          }}
        >
          <div className="flex items-baseline gap-1.5" style={{ marginBottom: 18 }}>
            <span className="font-[var(--ds-font-display)] font-bold" style={{ fontSize: 32 }}>
              ₹500
            </span>
            <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>/month</span>
          </div>
          <div className="flex flex-col gap-2.5">
            {FEATURES.map((f) => (
              <div
                key={f}
                className="flex items-center gap-2"
                style={{ fontSize: 13.5, color: "var(--ds-ink-600)" }}
              >
                <div
                  className="flex-shrink-0 rounded-full bg-[var(--ds-accent-primary)]"
                  style={{ width: 6, height: 6 }}
                />
                {f}
              </div>
            ))}
          </div>
        </div>

        <Link
          to="/checkout"
          className="block w-full box-border font-bold text-center"
          style={{
            padding: 14,
            borderRadius: "var(--ds-radius-md)",
            background: "var(--ds-accent-primary)",
            color: "var(--ds-text-on-brand)",
            fontSize: 14.5,
            boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
            marginBottom: 14,
          }}
        >
          Upgrade to Pro — ₹500/mo
        </Link>
        <Link to="/dashboard" style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
          Not now
        </Link>
      </div>
    </div>
  );
}
