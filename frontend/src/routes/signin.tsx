import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { DsLogo } from "../components/ds/Logo";
import { DsInput } from "../components/ds/Input";

export const Route = createFileRoute("/signin")({
  head: () => ({
    meta: [{ title: "Sign in — CareerAutomated" }],
  }),
  component: SignIn,
});

function GoogleIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84c-.21 1.13-.85 2.09-1.81 2.73v2.26h2.92c1.7-1.57 2.69-3.88 2.69-6.63z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.87-3.04.87-2.34 0-4.32-1.58-5.03-3.71H.9v2.33C2.38 15.98 5.44 18 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72c-.18-.54-.28-1.11-.28-1.72s.1-1.18.28-1.72V4.95H.9C.33 6.13 0 7.53 0 9s.33 2.87.9 4.05l3.07-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0 5.44 0 2.38 2.02.9 4.95l3.07 2.33C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}

function Spinner({ dark = false }: { dark?: boolean }) {
  return (
    <div
      className="animate-spin rounded-full"
      style={{
        width: 16,
        height: 16,
        border: `2px solid ${dark ? "rgba(36,28,20,0.16)" : "rgba(255,249,244,0.35)"}`,
        borderTopColor: dark ? "var(--ds-ink-700)" : "#FFF9F4",
      }}
    />
  );
}

function SignIn() {
  const { user, loginWithEmail, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [googleLoading, setGoogleLoading] = useState(false);
  const [signInLoading, setSignInLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (user) navigate({ to: "/dashboard" });
  }, [user, navigate]);

  // Block rendering for signed-in users — redirect fires above, this
  // prevents a flash of the signin form in the meantime.
  if (user) return null;

  const handleGoogle = async () => {
    if (googleLoading) return;
    setGoogleLoading(true);
    setErrorMessage("");
    try {
      await loginWithGoogle();
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "Couldn't sign in with Google.");
      setGoogleLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (signInLoading) return;
    if (!email || !password) {
      setErrorMessage("Enter your email and password to continue.");
      return;
    }
    setSignInLoading(true);
    setErrorMessage("");
    try {
      await loginWithEmail(email, password);
      navigate({ to: "/dashboard" });
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "That didn't work — check your details and try again.",
      );
    } finally {
      setSignInLoading(false);
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

        <h2
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: 24, margin: "0 0 6px" }}
        >
          Welcome back
        </h2>
        <p style={{ fontSize: 14, color: "var(--ds-ink-500)", margin: "0 0 28px" }}>
          Sign in to keep your applications moving.
        </p>

        <button
          type="button"
          onClick={handleGoogle}
          className="w-full flex items-center justify-center gap-2.5 font-semibold active:scale-[0.98] transition-transform"
          style={{
            padding: "12px 16px",
            borderRadius: "var(--ds-radius-md)",
            border: "1px solid var(--ds-border-medium)",
            background: "var(--ds-surface-card)",
            color: "var(--ds-text-primary)",
            fontSize: 14,
          }}
        >
          {googleLoading ? <Spinner dark /> : <GoogleIcon />}
          <span>{googleLoading ? "Signing in…" : "Continue with Google"}</span>
        </button>

        <div className="flex items-center gap-3" style={{ margin: "22px 0" }}>
          <div className="flex-1" style={{ height: 1, background: "var(--ds-border-default)" }} />
          <span style={{ fontSize: 12.5, color: "var(--ds-ink-400)" }}>or</span>
          <div className="flex-1" style={{ height: 1, background: "var(--ds-border-default)" }} />
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <DsInput
              label="Email"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setErrorMessage("");
              }}
              required
            />
          </div>
          <DsInput
            label="Password"
            forgotHref="/forgot-password"
            type="password"
            placeholder="Your password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setErrorMessage("");
            }}
            required
          />

          {errorMessage && (
            <div
              style={{
                fontSize: 12.5,
                color: "var(--ds-ink-600)",
                background: "var(--ds-surface-page-alt)",
                border: "1px solid var(--ds-border-default)",
                borderRadius: 8,
                padding: "9px 12px",
                margin: "16px 0 0",
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
              marginTop: 20,
            }}
          >
            {signInLoading ? <Spinner /> : <span>Sign in</span>}
          </button>
        </form>

        <div
          className="text-center"
          style={{ marginTop: 22, fontSize: 13.5, color: "var(--ds-ink-500)" }}
        >
          Don't have an account? <Link to="/signup">Sign up</Link>
        </div>
      </div>
    </div>
  );
}
