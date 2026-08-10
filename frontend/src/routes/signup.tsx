import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { DsLogo } from "../components/ds/Logo";
import { DsInput } from "../components/ds/Input";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create your account — CareerAutomated" },
      {
        name: "description",
        content: "Create a CareerAutomated account. Free to start. Two minutes to set up.",
      },
    ],
  }),
  component: SignUpPage,
});

const ROTATING_LINES = [
  "Finding matching jobs…",
  "Tailoring your resume…",
  "Tracking applications…",
  "Preparing interview-ready resumes…",
  "Discovering hidden opportunities…",
  "Saving hours every week…",
  "Building your career system…",
];

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

function SignUpPage() {
  const { user, profile, signUpWithEmail, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [lineIndex, setLineIndex] = useState(0);

  useEffect(() => {
    if (!user) return;
    // Wait for the real profile before deciding where to send them — it
    // starts null while the async fetch is in flight, and treating "not
    // loaded yet" the same as "onboarding complete" was sending brand-new
    // signups straight to an empty dashboard, skipping onboarding entirely.
    if (!profile) return;
    if (!profile.onboarding_complete) {
      navigate({ to: "/onboarding" });
    } else {
      navigate({ to: "/dashboard" });
    }
  }, [user, profile, navigate]);

  // Block rendering for signed-in users — redirect fires above, this
  // prevents a flash of the signup form in the meantime.
  if (user) return null;

  useEffect(() => {
    const t = setInterval(() => setLineIndex((i) => (i + 1) % ROTATING_LINES.length), 6500);
    return () => clearInterval(t);
  }, []);

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
    if (createLoading) return;
    if (!email || !password) {
      setErrorMessage("Enter your email and password to continue.");
      return;
    }
    if (password.length < 8) {
      setErrorMessage("Password should be at least 8 characters.");
      return;
    }
    if (!agreed) {
      setErrorMessage("Please agree to the Terms and Privacy Policy.");
      return;
    }
    setCreateLoading(true);
    setErrorMessage("");
    try {
      await signUpWithEmail(email, password);
      navigate({ to: "/onboarding" });
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "That didn't go through. Please try again.",
      );
    } finally {
      setCreateLoading(false);
    }
  };

  return (
    <div
      className="flex"
      style={{
        minHeight: "100vh",
        background: "var(--ds-surface-page)",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
      }}
    >
      <div
        className="hidden md:flex flex-col justify-between relative overflow-hidden"
        style={{
          width: "40%",
          minWidth: 380,
          padding: 56,
          background: "var(--ds-surface-page-alt)",
          borderRight: "1px solid var(--ds-border-default)",
        }}
      >
        <div
          className="pointer-events-none absolute"
          style={{
            top: -140,
            left: -100,
            width: 420,
            height: 420,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(232,93,44,0.14), transparent 70%)",
            filter: "blur(60px)",
          }}
        />
        <Link to="/" className="relative z-10">
          <DsLogo box={33} wordmark={18} weight={600} />
        </Link>
        <div className="relative z-10">
          <h1
            className="font-[var(--ds-font-display)] font-semibold"
            style={{
              fontSize: "clamp(28px,3vw,36px)",
              lineHeight: 1.18,
              margin: "0 0 16px",
              letterSpacing: "-0.01em",
            }}
          >
            Start your career operating system.
          </h1>
          <p
            style={{
              fontSize: 16,
              color: "var(--ds-ink-500)",
              lineHeight: 1.6,
              margin: 0,
              maxWidth: 380,
            }}
          >
            Spend less time applying. More time preparing for opportunities.
          </p>
        </div>
        <div className="relative z-10" style={{ height: 22 }}>
          <div style={{ fontSize: 13.5, color: "var(--ds-ink-450)", fontWeight: 500 }}>
            {ROTATING_LINES[lineIndex]}
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center" style={{ padding: "40px 24px" }}>
        <div style={{ width: "100%", maxWidth: 400 }}>
          <h2
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: 24, margin: "0 0 28px", letterSpacing: "-0.01em" }}
          >
            Create your account
          </h2>

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
            <div style={{ marginBottom: 12 }}>
              <DsInput
                label="Password"
                type="password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setErrorMessage("");
                }}
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

            <div className="flex items-start gap-2" style={{ margin: "16px 0 24px" }}>
              <input
                type="checkbox"
                checked={agreed}
                onChange={() => setAgreed((a) => !a)}
                style={{
                  marginTop: 2,
                  width: 15,
                  height: 15,
                  accentColor: "#E27448",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: 12.5, color: "var(--ds-ink-500)", lineHeight: 1.55 }}>
                I agree to the{" "}
                <Link to="/legal" hash="terms">
                  Terms
                </Link>{" "}
                and{" "}
                <Link to="/legal" hash="privacy">
                  Privacy Policy
                </Link>
                .
              </span>
            </div>

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
              {createLoading ? <Spinner /> : <span>Create account</span>}
            </button>
          </form>

          <div
            className="text-center"
            style={{ marginTop: 22, fontSize: 13.5, color: "var(--ds-ink-500)" }}
          >
            Already have an account? <Link to="/signin">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
