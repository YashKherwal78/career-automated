import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/payment-success")({
  head: () => ({ meta: [{ title: "Payment Success — CareerAutomated" }] }),
  component: PaymentSuccess,
});

function PaymentSuccess() {
  return (
    <div
      className="flex items-center justify-center"
      style={{
        minHeight: "100vh",
        padding: "40px 24px",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
      }}
    >
      <div className="text-center" style={{ width: "100%", maxWidth: 420 }}>
        <div
          className="mx-auto flex items-center justify-center"
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: "#6B8F5E",
            marginBottom: 22,
          }}
        >
          <svg width="26" height="26" viewBox="0 0 16 16">
            <path
              d="M3 8.5l3 3 7-7"
              stroke="#FFFDFA"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
        </div>
        <h1
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: 24, margin: "0 0 10px" }}
        >
          You're on Pro.
        </h1>
        <p
          style={{
            fontSize: 14.5,
            color: "var(--ds-ink-500)",
            lineHeight: 1.6,
            margin: "0 0 28px",
          }}
        >
          Payment received. Unlimited tailoring, auto-apply, and smart follow-ups are live on your
          account now.
        </p>

        <div
          className="text-left"
          style={{
            background: "var(--ds-surface-card)",
            border: "1px solid var(--ds-border-default)",
            borderRadius: "var(--ds-radius-lg)",
            padding: 18,
            marginBottom: 28,
          }}
        >
          <div
            className="flex items-center justify-between"
            style={{ fontSize: 13, color: "var(--ds-ink-500)", marginBottom: 8 }}
          >
            <span>Plan</span>
            <span className="font-semibold" style={{ color: "var(--ds-ink-700)" }}>
              CareerAutomated Pro
            </span>
          </div>
          <div
            className="flex items-center justify-between"
            style={{ fontSize: 13, color: "var(--ds-ink-500)", marginBottom: 8 }}
          >
            <span>Amount paid</span>
            <span className="font-semibold" style={{ color: "var(--ds-ink-700)" }}>
              ₹590.00
            </span>
          </div>
          <div
            className="flex items-center justify-between"
            style={{ fontSize: 13, color: "var(--ds-ink-500)" }}
          >
            <span>Next billing date</span>
            <span className="font-semibold" style={{ color: "var(--ds-ink-700)" }}>
              —
            </span>
          </div>
        </div>

        <Link
          to="/dashboard"
          className="block w-full box-border font-bold text-center"
          style={{
            padding: 13,
            borderRadius: "var(--ds-radius-md)",
            background: "var(--ds-accent-primary)",
            color: "var(--ds-text-on-brand)",
            fontSize: 14,
            boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
          }}
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
