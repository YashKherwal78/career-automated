import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ServiceRegistry } from "../lib/services";
import { useAuth } from "../lib/auth";

export const Route = createFileRoute("/checkout")({
  head: () => ({ meta: [{ title: "Checkout — CareerAutomated" }] }),
  component: Checkout,
});

declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => {
      open: () => void;
      on: (event: string, handler: (response: unknown) => void) => void;
    };
  }
}

function loadRazorpayScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay checkout script"));
    document.body.appendChild(script);
  });
}

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
  const { profile } = useAuth();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startPayment = async () => {
    if (processing) return;
    setProcessing(true);
    setError(null);

    try {
      await loadRazorpayScript();
      const billing = ServiceRegistry.getBillingService();
      const order = await billing.createOrder();

      const rzp = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        order_id: order.order_id,
        name: "CareerAutomated",
        description: "CareerAutomated Pro — monthly",
        prefill: {
          name: profile?.full_name || undefined,
          email: profile?.email || undefined,
        },
        theme: { color: "#E85D2C" },
        handler: async (response: unknown) => {
          try {
            const r = response as {
              razorpay_order_id: string;
              razorpay_payment_id: string;
              razorpay_signature: string;
            };
            await billing.verifyPayment(r);
            navigate({ to: "/payment-success" });
          } catch {
            setProcessing(false);
            setError(
              "Payment succeeded but verification failed. Contact support if you were charged.",
            );
          }
        },
        modal: {
          ondismiss: () => setProcessing(false),
        },
      });
      rzp.on("payment.failed", () => {
        setProcessing(false);
        setError("Payment failed. Please try again.");
      });
      rzp.open();
    } catch {
      setProcessing(false);
      setError("Couldn't start checkout. Please try again.");
    }
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

        {error && (
          <p
            style={{
              fontSize: 12.5,
              color: "var(--ds-accent-danger, #C4432B)",
              textAlign: "center",
              marginTop: 12,
              lineHeight: 1.5,
            }}
          >
            {error}
          </p>
        )}

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
