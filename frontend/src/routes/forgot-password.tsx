import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { supabase } from "../lib/supabase";
import { DsLogo } from "../components/ds/Logo";
import { DsInput } from "../components/ds/Input";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [{ title: "Reset your password — CareerAutomated" }],
  }),
  component: ForgotPassword,
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

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || !email) return;
    setLoading(true);
    setErrorMessage("");
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/signin`,
      });
      if (error) throw error;
      setSent(true);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "That didn't go through. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

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
          left: "10%",
          width: 480,
          height: 480,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(232,93,44,0.14), transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div className="relative z-10" style={{ width: "100%", maxWidth: 400 }}>
        <Link to="/" className="inline-flex" style={{ marginBottom: 36 }}>
          <DsLogo box={33} wordmark={18} weight={600} />
        </Link>

        {!sent ? (
          <>
            <h2
              className="font-[var(--ds-font-display)] font-semibold"
              style={{ fontSize: 24, margin: "0 0 6px" }}
            >
              Reset your password
            </h2>
            <p
              style={{
                fontSize: 14,
                color: "var(--ds-ink-500)",
                margin: "0 0 28px",
                lineHeight: 1.5,
              }}
            >
              Enter your email and we'll send you a link to reset it.
            </p>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 20 }}>
                <DsInput
                  label="Email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              {errorMessage && (
                <div
                  style={{
                    fontSize: 12.5,
                    color: "var(--ds-ink-600)",
                    background: "var(--ds-surface-page-alt)",
                    border: "1px solid var(--ds-border-default)",
                    borderRadius: 8,
                    padding: "9px 12px",
                    marginBottom: 16,
                  }}
                >
                  {errorMessage}
                </div>
              )}
              <button
                type="submit"
                className="w-full flex items-center justify-center font-bold active:scale-[0.98] transition-transform"
                style={{
                  padding: "13px 16px",
                  borderRadius: "var(--ds-radius-md)",
                  border: "none",
                  background: "#E27448",
                  color: "var(--ds-text-on-brand)",
                  fontSize: 14.5,
                  boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
                }}
              >
                {loading ? <Spinner /> : <span>Send reset link</span>}
              </button>
            </form>
          </>
        ) : (
          <>
            <div
              className="flex items-center justify-center"
              style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                background: "rgba(107,143,94,0.14)",
                marginBottom: 18,
              }}
            >
              <svg width="22" height="22" viewBox="0 0 16 16">
                <path
                  d="M3 8.5l3 3 7-7"
                  stroke="#4A6B3E"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
            </div>
            <h2
              className="font-[var(--ds-font-display)] font-semibold"
              style={{ fontSize: 22, margin: "0 0 8px" }}
            >
              Check your email
            </h2>
            <p style={{ fontSize: 14, color: "var(--ds-ink-500)", margin: 0, lineHeight: 1.6 }}>
              We sent a reset link to{" "}
              <strong style={{ color: "var(--ds-ink-700)" }}>{email}</strong>. It expires in 30
              minutes.
            </p>
          </>
        )}

        <div
          className="text-center"
          style={{ marginTop: 26, fontSize: 13.5, color: "var(--ds-ink-500)" }}
        >
          <Link to="/signin">← Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
