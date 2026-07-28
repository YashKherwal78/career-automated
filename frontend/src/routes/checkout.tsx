import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

export const Route = createFileRoute("/checkout")({
  head: () => ({ meta: [{ title: "Checkout — CareerAutomated" }] }),
  component: Checkout,
});

function Spinner() {
  return (
    <div
      className="animate-spin rounded-full"
      style={{
        width: 16,
        height: 16,
        border: "2px solid rgba(255,249,244,0.35)",
        borderTopColor: "#FFF9F4",
      }}
    />
  );
}

function Checkout() {
  const navigate = useNavigate();
  const [processing, setProcessing] = useState(false);

  const startPayment = () => {
    if (processing) return;
    setProcessing(true);
    // Backend integration point: replace this simulated flow with a real Razorpay Checkout call, e.g.
    // const rzp = new window.Razorpay({ key, amount, order_id, handler: () => navigate({ to: "/payment-success" }), ... });
    // rzp.open();
    // No billing backend exists yet (see plan Phase 7) — this is intentionally simulated.
    setTimeout(() => navigate({ to: "/payment-success" }), 1500);
  };

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
      <div style={{ width: "100%", maxWidth: 420 }}>
        <Link
          to="/pricing"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13.5,
            fontWeight: 600,
            color: "var(--ds-ink-500)",
            marginBottom: 28,
          }}
        >
          ← Back
        </Link>

        <div
          className="uppercase font-bold"
          style={{
            fontSize: 12.5,
            letterSpacing: "var(--ds-tracking-wide)",
            color: "var(--ds-brand-orange-text)",
            marginBottom: 10,
          }}
        >
          Checkout
        </div>
        <h1
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: 24, margin: "0 0 24px" }}
        >
          Upgrade to Pro
        </h1>

        <div
          style={{
            background: "var(--ds-surface-card)",
            border: "1px solid var(--ds-border-default)",
            borderRadius: "var(--ds-radius-xl)",
            padding: 22,
            marginBottom: 16,
          }}
        >
          <div
            className="flex items-center justify-between"
            style={{
              paddingBottom: 16,
              marginBottom: 16,
              borderBottom: "1px solid var(--ds-border-default)",
            }}
          >
            <div>
              <div style={{ fontSize: 14.5, fontWeight: 600 }}>CareerAutomated Pro</div>
              <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)" }}>Billed monthly</div>
            </div>
            <div className="font-[var(--ds-font-display)] font-bold" style={{ fontSize: 18 }}>
              ₹500
            </div>
          </div>
          <div
            className="flex items-center justify-between"
            style={{ fontSize: 13.5, color: "var(--ds-ink-500)", marginBottom: 8 }}
          >
            <span>Subtotal</span>
            <span>₹500.00</span>
          </div>
          <div
            className="flex items-center justify-between"
            style={{ fontSize: 13.5, color: "var(--ds-ink-500)", marginBottom: 14 }}
          >
            <span>GST (18%)</span>
            <span>₹90.00</span>
          </div>
          <div
            className="flex items-center justify-between font-bold"
            style={{
              fontSize: 15,
              paddingTop: 14,
              borderTop: "1px solid var(--ds-border-default)",
            }}
          >
            <span>Total due today</span>
            <span>₹590.00</span>
          </div>
        </div>

        <button
          type="button"
          onClick={startPayment}
          disabled={processing}
          className="w-full flex items-center justify-center gap-2.5 font-bold"
          style={{
            boxSizing: "border-box",
            padding: 14,
            border: "none",
            borderRadius: "var(--ds-radius-md)",
            background: "#3395FF",
            color: "#fff",
            fontSize: 14.5,
            cursor: processing ? "default" : "pointer",
            opacity: processing ? 0.85 : 1,
          }}
        >
          {processing ? (
            <>
              <Spinner />
              <span>Opening Razorpay…</span>
            </>
          ) : (
            <span>Pay ₹590 with Razorpay</span>
          )}
        </button>

        <p
          style={{
            fontSize: 12,
            color: "var(--ds-ink-400)",
            textAlign: "center",
            marginTop: 14,
            lineHeight: 1.5,
          }}
        >
          Payments are securely processed by Razorpay. Cancel anytime from Settings.
        </p>
      </div>
    </div>
  );
}
