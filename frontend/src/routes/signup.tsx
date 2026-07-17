import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { z } from "zod";
import { ArrowRight, Eye, EyeOff, CheckCircle2, Sparkles } from "lucide-react";
import { Button } from "@/components/primitives/button";
import { FadeIn } from "@/components/primitives/motion";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create or Sign In to your account — CareerAutomated" },
      { name: "description", content: "Sign in or create a CareerAutomated account. Free to start. Two minutes to set up." },
    ],
  }),
  component: SignUpPage,
});

const signUpSchema = z
  .object({
    email: z.string().trim().email("Enter a valid email"),
    password: z.string().min(8, "At least 8 characters").max(72, "Too long"),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Passwords don't match",
    path: ["confirm"],
  });

const signInSchema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type FieldErrors = Partial<Record<"email" | "password" | "confirm" | "form", string>>;

function SignUpPage() {
  const { user, profile, loginWithEmail, signUpWithEmail, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const [isSignUp, setIsSignUp] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (user) {
      if (profile && !profile.onboarding_complete) {
        navigate({ to: "/onboarding" });
      } else if (profile?.onboarding_complete) {
        navigate({ to: "/dashboard" });
      }
    }
  }, [user, profile, navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});
    
    if (isSignUp) {
      const parsed = signUpSchema.safeParse({ email, password, confirm });
      if (!parsed.success) {
        const fe: FieldErrors = {};
        for (const issue of parsed.error.issues) {
          const key = issue.path[0] as keyof FieldErrors;
          if (!fe[key]) fe[key] = issue.message;
        }
        setErrors(fe);
        return;
      }
      setLoading(true);
      try {
        await signUpWithEmail(email, password);
        setDone(true);
      } catch (err: any) {
        setErrors({ form: err.message || "Failed to create account. Try again." });
      } finally {
        setLoading(false);
      }
    } else {
      const parsed = signInSchema.safeParse({ email, password });
      if (!parsed.success) {
        const fe: FieldErrors = {};
        for (const issue of parsed.error.issues) {
          const key = issue.path[0] as keyof FieldErrors;
          if (!fe[key]) fe[key] = issue.message;
        }
        setErrors(fe);
        return;
      }
      setLoading(true);
      try {
        await loginWithEmail(email, password);
      } catch (err: any) {
        setErrors({ form: err.message || "Invalid email or password." });
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-2">
      {/* Form side */}
      <div className="flex items-center justify-center px-6 py-16">
        <FadeIn className="w-full max-w-md">
          <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-ink-soft">
            {isSignUp ? "Get started" : "Welcome back"}
          </div>
          <h1 className="mt-3 font-display text-4xl leading-[1.05] tracking-tight text-ink md:text-5xl">
            {isSignUp ? "Create your account" : "Sign in to your account"}
          </h1>
          <p className="mt-3 text-[15px] text-ink-soft">
            {isSignUp ? "Already have one? " : "Don't have one? "}
            <button
              type="button"
              onClick={() => {
                setIsSignUp(!isSignUp);
                setErrors({});
              }}
              className="font-medium text-ink underline underline-offset-4 hover:text-[color:var(--peach-deep)]"
            >
              {isSignUp ? "Sign in" : "Sign up"}
            </button>
          </p>

          <div className="mt-8">
            <button
              type="button"
              onClick={loginWithGoogle}
              className="w-full inline-flex h-11 items-center justify-center gap-2 rounded-xl border hairline bg-white text-sm font-medium text-ink transition hover:border-ink/30"
            >
              <GoogleIcon />
              Continue with Google
            </button>
          </div>

          <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-widest text-ink-soft">
            <div className="h-px flex-1 bg-[color:var(--border)]" />
            or
            <div className="h-px flex-1 bg-[color:var(--border)]" />
          </div>

          {done ? (
            <div className="rounded-2xl border hairline bg-[color:var(--peach-soft)] p-6">
              <div className="flex items-center gap-2 text-sm font-medium text-ink">
                <CheckCircle2 className="h-4 w-4 text-[color:var(--peach-deep)]" />
                Check your inbox
              </div>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                We sent a confirmation link to <span className="font-medium text-ink">{email}</span>. Click it to activate
                your account.
              </p>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="space-y-4" noValidate>
              <Field
                label="Work email"
                type="email"
                value={email}
                onChange={setEmail}
                error={errors.email}
                placeholder="you@company.com"
                autoComplete="email"
              />
              <Field
                label="Password"
                type={showPw ? "text" : "password"}
                value={password}
                onChange={setPassword}
                error={errors.password}
                placeholder={isSignUp ? "At least 8 characters" : "Enter your password"}
                autoComplete="current-password"
                trailing={
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    className="text-ink-soft transition hover:text-ink"
                    aria-label={showPw ? "Hide password" : "Show password"}
                  >
                    {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
              />
              {isSignUp && (
                <Field
                  label="Confirm password"
                  type={showPw ? "text" : "password"}
                  value={confirm}
                  onChange={setConfirm}
                  error={errors.confirm}
                  placeholder="Re-enter your password"
                  autoComplete="new-password"
                />
              )}

              {errors.form ? (
                <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {errors.form}
                </div>
              ) : null}

              <Button type="submit" loading={loading} className="w-full" size="lg" trailing={!loading ? <ArrowRight className="h-4 w-4" /> : undefined}>
                {loading ? (isSignUp ? "Creating account…" : "Signing in…") : (isSignUp ? "Create account" : "Sign in")}
              </Button>

              <p className="pt-1 text-xs leading-relaxed text-ink-soft">
                By continuing, you agree to our{" "}
                <Link to="/terms" className="underline underline-offset-4 hover:text-ink">Terms</Link> and{" "}
                <Link to="/privacy" className="underline underline-offset-4 hover:text-ink">Privacy Policy</Link>.
              </p>
            </form>
          )}
        </FadeIn>
      </div>

      {/* Brand side */}
      <div className="relative hidden overflow-hidden bg-ink lg:block">
        <div className="pointer-events-none absolute inset-0 grid-lines opacity-10" />
        <div className="pointer-events-none absolute -right-24 -top-24 h-[520px] w-[520px] rounded-full peach-gradient opacity-30 blur-3xl" />
        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-white/70 backdrop-blur">
            <Sparkles className="h-3 w-3 text-[color:var(--peach)]" />
            AI career operating system
          </div>

          <div className="max-w-md">
            <blockquote className="font-display text-3xl leading-snug tracking-tight text-white md:text-4xl">
              "Applying stopped feeling like a second job. I opened the dashboard, approved three drafts, and moved on
              with my day."
            </blockquote>
            <div className="mt-6 text-sm text-white/60">— Beta user, Software Engineer</div>
          </div>

          <ul className="grid gap-3 text-sm text-white/80">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[color:var(--peach)]" />
              Free plan — no credit card required
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[color:var(--peach)]" />
              You approve every application before it's sent
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-[color:var(--peach)]" />
              Cancel or downgrade anytime, one click
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  error,
  placeholder,
  autoComplete,
  trailing,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  placeholder?: string;
  autoComplete?: string;
  trailing?: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 text-[13px] font-medium text-ink">{label}</div>
      <div
        className={`flex h-11 items-center gap-2 rounded-xl border bg-white px-3 transition focus-within:border-ink/40 focus-within:ring-2 focus-within:ring-ink/10 ${
          error ? "border-destructive/50" : "hairline"
        }`}
      >
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-soft/60"
        />
        {trailing}
      </div>
      {error ? <div className="mt-1.5 text-xs text-destructive">{error}</div> : null}
    </label>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4">
      <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.24 1.4-1.7 4.1-5.5 4.1-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.1.8 3.8 1.5l2.6-2.5C16.7 3.3 14.6 2.3 12 2.3 6.6 2.3 2.3 6.6 2.3 12s4.3 9.7 9.7 9.7c5.6 0 9.3-3.9 9.3-9.5 0-.6-.1-1.1-.2-1.6H12z" />
    </svg>
  );
}
