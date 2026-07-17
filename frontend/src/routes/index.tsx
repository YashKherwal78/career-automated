import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Sparkles,
  Search,
  FileText,
  ClipboardList,
  Send,
  Bell,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Target,
  Wand2,
  ListChecks,
  Radar,
} from "lucide-react";
import { motion } from "framer-motion";
import { Container } from "@/components/primitives/container";
import { Section, SectionHeading } from "@/components/primitives/section";
import { FadeIn, Stagger, StaggerItem } from "@/components/primitives/motion";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CareerAutomated — The AI career operating system" },
      {
        name: "description",
        content:
          "CareerAutomated finds matching jobs, tailors your resume, drafts applications, and tracks every follow-up — so you can spend your time preparing for interviews instead of applying to them.",
      },
      { property: "og:title", content: "CareerAutomated — The AI career operating system" },
      {
        property: "og:description",
        content: "Spend less time applying, more time interviewing. You stay in control. AI does the repetitive work.",
      },
    ],
  }),
  component: Home,
});

function Home() {
  return (
    <>
      <Hero />
      <ProductOverview />
      <ProblemSection />
      <SolutionSection />
      <HowItWorks />
      <FeaturesGrid />
      <WhyDifferent />
      <PricingPreview />
      <FaqPreview />
      <FinalCTA />
    </>
  );
}

/* ────────────────────────── HERO ────────────────────────── */
function Hero() {
  return (
    <section className="relative overflow-hidden pt-16 pb-24 md:pt-28 md:pb-32">
      <div className="pointer-events-none absolute inset-0 grid-lines opacity-60" />
      <div className="pointer-events-none absolute inset-x-0 -top-24 h-[520px] peach-glow" />

      <Container className="relative">
        <FadeIn>
          <div className="mx-auto flex max-w-fit items-center gap-2 rounded-full border hairline bg-white/70 px-3 py-1 text-xs text-ink-soft backdrop-blur">
            <Sparkles className="h-3 w-3 text-[color:var(--peach-deep)]" />
            <span>Introducing your AI career operating system</span>
          </div>
        </FadeIn>

        <FadeIn delay={0.05} className="mt-6">
          <h1 className="mx-auto max-w-4xl text-balance text-center font-display text-5xl leading-[1.02] tracking-tight text-ink md:text-7xl">
            Spend less time applying. <br className="hidden md:block" />
            <span className="text-ink-soft">More time interviewing.</span>
          </h1>
        </FadeIn>

        <FadeIn delay={0.12} className="mt-6">
          <p className="mx-auto max-w-2xl text-center text-[17px] leading-relaxed text-ink-soft md:text-[18px]">
            CareerAutomated finds matching jobs, tailors your resume, and drafts every application — you review and
            approve. The repetitive work runs on autopilot. The decisions stay yours.
          </p>
        </FadeIn>

        <FadeIn delay={0.18} className="mt-9">
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link to="/signup" className="btn-dark text-sm">
              Get started free <ArrowRight className="h-4 w-4" />
            </Link>
            <a href="#how" className="btn-ghost-ink text-sm">
              See how it works
            </a>
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-ink-soft">
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" /> Free plan available
            </span>
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" /> No credit card required
            </span>
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" /> You approve every send
            </span>
          </div>
        </FadeIn>

        <FadeIn delay={0.28} y={24} className="mt-16">
          <HeroDashboard />
        </FadeIn>
      </Container>
    </section>
  );
}

function HeroDashboard() {
  const rows = [
    { company: "Stripe", role: "Backend Engineer", match: 94, status: "Draft ready", tone: "primary" },
    { company: "Notion", role: "Product Engineer", match: 91, status: "Applied · today", tone: "muted" },
    { company: "Linear", role: "Full-stack Engineer", match: 88, status: "Awaiting review", tone: "primary" },
    { company: "Ramp", role: "Software Engineer", match: 86, status: "Follow-up sent", tone: "muted" },
  ];
  return (
    <div className="relative mx-auto max-w-5xl">
      <div className="absolute -inset-8 rounded-[36px] peach-gradient opacity-30 blur-3xl" />
      <div className="relative overflow-hidden rounded-3xl border hairline bg-white shadow-[0_30px_80px_-30px_oklch(0.2_0.02_260/0.25)]">
        <div className="flex items-center justify-between border-b hairline px-5 py-3">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-[color:var(--peach)]" />
              <div className="h-2.5 w-2.5 rounded-full bg-secondary" />
              <div className="h-2.5 w-2.5 rounded-full bg-secondary" />
            </div>
            <span className="ml-3 text-xs text-ink-soft">app.careerautomated.com</span>
          </div>
          <div className="text-[10px] font-medium uppercase tracking-widest text-ink-soft">Pipeline</div>
        </div>

        <div className="grid gap-0 md:grid-cols-[1.4fr_1fr]">
          <div className="border-b border-r-0 hairline p-5 md:border-b-0 md:border-r">
            <div className="flex items-center justify-between text-xs text-ink-soft">
              <span>This week</span>
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[color:var(--peach-deep)]" />
                4 new matches
              </span>
            </div>
            <div className="mt-4 space-y-2">
              {rows.map((r, i) => (
                <motion.div
                  key={r.company}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 + i * 0.08 }}
                  className="flex items-center gap-3 rounded-2xl border hairline bg-white px-3 py-2.5"
                >
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-secondary text-xs font-semibold text-ink">
                    {r.company.slice(0, 1)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-sm font-medium">{r.role}</div>
                    <div className="truncate text-xs text-ink-soft">{r.company}</div>
                  </div>
                  <div className="hidden md:block">
                    <div className="text-[10px] uppercase tracking-widest text-ink-soft">Match</div>
                    <div className="text-sm font-semibold">{r.match}%</div>
                  </div>
                  <div
                    className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                      r.tone === "primary"
                        ? "bg-ink text-white"
                        : "border hairline bg-white text-ink-soft"
                    }`}
                  >
                    {r.status}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="space-y-4 bg-[color:var(--surface-muted)] p-5">
            <MiniCard label="Applications this week" value="12" delta="+4" />
            <MiniCard label="Response rate" value="18%" delta="+6%" />
            <MiniCard label="Interviews scheduled" value="3" delta="+2" />
            <div className="rounded-2xl border hairline bg-white p-4">
              <div className="flex items-center gap-2 text-xs font-medium text-ink">
                <Wand2 className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" />
                Resume tailored for Stripe
              </div>
              <p className="mt-1 text-xs leading-relaxed text-ink-soft">
                Emphasized payments, distributed systems, and Postgres experience. Awaiting your review.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniCard({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <div className="rounded-2xl border hairline bg-white p-4">
      <div className="text-[11px] uppercase tracking-widest text-ink-soft">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <div className="font-display text-2xl">{value}</div>
        <div className="text-xs font-medium text-[color:var(--peach-deep)]">{delta}</div>
      </div>
    </div>
  );
}

/* ────────────────────────── OVERVIEW ────────────────────────── */
function ProductOverview() {
  return (
    <Section className="py-20 md:py-24">
      <FadeIn>
        <p className="mx-auto max-w-3xl text-balance text-center font-display text-2xl leading-snug text-ink md:text-3xl">
          CareerAutomated is an AI career operating system. It handles the repetitive work of job searching —
          searching, tailoring, applying, tracking, following up — so your time goes toward becoming a better
          candidate.
        </p>
      </FadeIn>
    </Section>
  );
}

/* ────────────────────────── PROBLEM ────────────────────────── */
const PROBLEMS = [
  { title: "Searching across a dozen job boards", body: "LinkedIn, Wellfound, company pages, Slack groups. New tabs. New spreadsheets. Same job posted three times." },
  { title: "Tailoring your resume, again", body: "Every role asks for something slightly different. You keep four versions in Google Drive and can't remember which is current." },
  { title: "Filling the same ATS forms", body: "First name. Last name. Same five essay questions. Twenty minutes per application. Multiply by fifty." },
  { title: "Losing track of what you sent", body: "Did you already apply to that role? When? Who was the recruiter? Did they reply? Time to search your inbox." },
];

function ProblemSection() {
  return (
    <Section bg="muted" className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="The problem"
        title={<>Finding a job has quietly become <br className="hidden md:block" />a full-time job.</>}
        description="The mechanics of applying are repetitive, tedious, and consume the exact time you should be spending preparing for interviews."
      />

      <Stagger className="mt-14 grid gap-4 md:grid-cols-2">
        {PROBLEMS.map((p) => (
          <StaggerItem key={p.title}>
            <div className="h-full rounded-2xl border hairline bg-white p-6">
              <div className="text-base font-medium text-ink">{p.title}</div>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-soft">{p.body}</p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* ────────────────────────── SOLUTION ────────────────────────── */
const OUTCOMES = [
  { icon: Zap, title: "Apply faster", body: "What used to take an hour takes two minutes: review, edit if needed, send." },
  { icon: ListChecks, title: "Stay organized", body: "Every application, resume version, and follow-up in one place — no spreadsheet." },
  { icon: Target, title: "Better applications", body: "Each resume is tailored to the role using your real experience. No generic sends." },
];

function SolutionSection() {
  return (
    <Section className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="The solution"
        title={<>AI does the repetitive work. <br className="hidden md:block" />You keep the judgment.</>}
        description="CareerAutomated watches the market for roles that fit you, prepares a tailored application for each one, and hands it to you ready to review. Nothing goes out without your approval."
      />

      <Stagger className="mt-14 grid gap-6 md:grid-cols-3">
        {OUTCOMES.map((o) => (
          <StaggerItem key={o.title}>
            <div className="h-full rounded-2xl border hairline bg-white p-7">
              <div className="grid h-10 w-10 place-items-center rounded-xl peach-gradient">
                <o.icon className="h-5 w-5 text-ink" />
              </div>
              <div className="mt-5 text-lg font-medium text-ink">{o.title}</div>
              <p className="mt-2 text-[15px] leading-relaxed text-ink-soft">{o.body}</p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* ────────────────────────── HOW IT WORKS ────────────────────────── */
const STEPS = [
  { icon: FileText, title: "Upload your resume", body: "One upload. We parse your skills, projects, and experience — no re-typing." },
  { icon: Search, title: "We find matching roles", body: "We continuously scan company career pages and ATS platforms for roles that fit your background." },
  { icon: Wand2, title: "AI tailors each application", body: "Every resume and cover letter is customized for the role — grounded only in your real experience." },
  { icon: Send, title: "You approve, we send", body: "Review the draft, edit if you want, then send. Follow-ups are drafted for you too." },
];

function HowItWorks() {
  return (
    <Section id="how" bg="muted" className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="How it works"
        title="Four steps. That's the whole workflow."
        description="You set it up once. Then it runs — quietly, in the background, until you have interviews to prepare for."
      />

      <Stagger className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s, i) => (
          <StaggerItem key={s.title}>
            <div className="relative h-full rounded-2xl border hairline bg-white p-6">
              <div className="absolute right-5 top-5 font-display text-2xl text-ink-soft/40">0{i + 1}</div>
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-ink text-white">
                <s.icon className="h-4 w-4" />
              </div>
              <div className="mt-5 text-base font-medium text-ink">{s.title}</div>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{s.body}</p>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* ────────────────────────── FEATURES ────────────────────────── */
const FEATURES = [
  {
    icon: Radar,
    title: "Continuous job discovery",
    benefit: "We watch career pages and ATS platforms 24/7.",
    outcome: "You stop refreshing LinkedIn — new matches arrive on their own.",
  },
  {
    icon: Wand2,
    title: "Resume tailoring, per role",
    benefit: "AI rewrites your resume for each application, grounded in your real experience.",
    outcome: "Every submission reads like it was written for that team.",
  },
  {
    icon: ClipboardList,
    title: "ATS autofill",
    benefit: "One-click autofill for Greenhouse, Lever, Ashby, and Workday.",
    outcome: "Applications that took 20 minutes now take two.",
  },
  {
    icon: ListChecks,
    title: "Application CRM",
    benefit: "Every send, response, and next step tracked in one view.",
    outcome: "You never lose track of where you stand.",
  },
  {
    icon: Bell,
    title: "Smart follow-ups",
    benefit: "Drafted follow-up emails at the right moment.",
    outcome: "You reply on time without setting reminders.",
  },
  {
    icon: ShieldCheck,
    title: "Human in the loop",
    benefit: "Nothing is submitted without your review.",
    outcome: "Automation without losing control of your brand.",
  },
];

function FeaturesGrid() {
  return (
    <Section className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="Core features"
        title="Every feature earns its place."
        description="No dashboards for the sake of dashboards. Each capability maps to a real thing you'd otherwise do by hand."
      />

      <Stagger className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f) => (
          <StaggerItem key={f.title}>
            <div className="group h-full rounded-2xl border hairline bg-white p-6 transition-all hover:-translate-y-0.5 hover:border-ink/20 hover:shadow-[0_20px_50px_-25px_oklch(0.2_0.02_260/0.25)]">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-[color:var(--peach-soft)]">
                <f.icon className="h-5 w-5 text-[color:var(--peach-deep)]" />
              </div>
              <div className="mt-5 text-base font-medium text-ink">{f.title}</div>
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{f.benefit}</p>
              <div className="mt-4 flex items-start gap-2 border-t hairline pt-4 text-xs text-ink-soft">
                <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[color:var(--peach-deep)]" />
                <span>{f.outcome}</span>
              </div>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </Section>
  );
}

/* ────────────────────────── WHY DIFFERENT ────────────────────────── */
const COMPARE = [
  {
    label: "Job boards",
    what: "Show you listings.",
    limit: "You still search, apply, and track every step by hand.",
  },
  {
    label: "Resume builders",
    what: "Format a single resume nicely.",
    limit: "One resume, one shot — no tailoring per role.",
  },
  {
    label: "AI chatbots",
    what: "Write text when you ask.",
    limit: "You still copy, paste, submit, and remember to follow up.",
  },
  {
    label: "CareerAutomated",
    what: "Runs the whole workflow end-to-end.",
    limit: "Find → tailor → apply → track → follow up. You approve, it executes.",
    highlight: true,
  },
];

function WhyDifferent() {
  return (
    <Section bg="ink" className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="Why it's different"
        title={<span className="text-white">Not another job board. Not another AI writer.</span>}
        description={
          <span className="text-white/70">
            CareerAutomated is the layer that connects them — the operating system for your career search.
          </span>
        }
      />

      <div className="mt-14 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
        {COMPARE.map((c, i) => (
          <div
            key={c.label}
            className={`grid gap-1 border-b border-white/10 p-6 last:border-b-0 md:grid-cols-[200px_1fr_1.4fr] md:items-center md:gap-6 md:p-8 ${
              c.highlight ? "bg-[color:var(--peach-soft)]/10" : ""
            }`}
          >
            <div className={`text-sm font-medium ${c.highlight ? "text-white" : "text-white/70"}`}>
              {c.highlight ? (
                <span className="inline-flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-[color:var(--peach)]" />
                  {c.label}
                </span>
              ) : (
                c.label
              )}
            </div>
            <div className={`text-sm ${c.highlight ? "text-white" : "text-white/60"}`}>{c.what}</div>
            <div className={`text-sm ${c.highlight ? "text-white/90" : "text-white/50"}`}>{c.limit}</div>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ────────────────────────── PRICING PREVIEW ────────────────────────── */
const PRICING_MINI = [
  { name: "Free", price: "$0", desc: "Everything you need to try it seriously.", cta: "Get started" },
  { name: "Pro", price: "$19", suffix: "/mo", desc: "Full workflow, real-time matches, unlimited resumes.", cta: "Start Pro", highlight: true },
  { name: "Premium", price: "$49", suffix: "/mo", desc: "Priority discovery, deeper tailoring, concierge support.", cta: "Go Premium" },
];

function PricingPreview() {
  return (
    <Section className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="Pricing"
        title="Start free. Upgrade when it pays for itself."
        description="If it doesn't save you real hours, downgrade in a click."
      />

      <Stagger className="mt-14 grid gap-6 md:grid-cols-3">
        {PRICING_MINI.map((p) => (
          <StaggerItem key={p.name}>
            <div
              className={`relative h-full rounded-2xl border p-7 ${
                p.highlight
                  ? "border-transparent bg-ink text-white shadow-[0_30px_80px_-30px_oklch(0.2_0.02_260/0.35)]"
                  : "border-[color:var(--border)] bg-white"
              }`}
            >
              {p.highlight ? (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full peach-gradient px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-ink">
                  Most popular
                </div>
              ) : null}
              <div className={`text-sm font-medium ${p.highlight ? "text-white" : "text-ink"}`}>{p.name}</div>
              <div className="mt-4 flex items-baseline gap-1">
                <div className="font-display text-5xl">{p.price}</div>
                {p.suffix ? <div className={`text-sm ${p.highlight ? "text-white/60" : "text-ink-soft"}`}>{p.suffix}</div> : null}
              </div>
              <p className={`mt-3 text-sm ${p.highlight ? "text-white/70" : "text-ink-soft"}`}>{p.desc}</p>
              <Link
                to="/pricing"
                className={`mt-8 flex w-full items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition ${
                  p.highlight
                    ? "bg-white text-ink hover:bg-white/90"
                    : "border hairline bg-white text-ink hover:border-ink/30"
                }`}
              >
                {p.cta} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </StaggerItem>
        ))}
      </Stagger>

      <div className="mt-8 text-center">
        <Link to="/pricing" className="text-sm font-medium text-ink underline underline-offset-4 hover:text-[color:var(--peach-deep)]">
          Compare all plans →
        </Link>
      </div>
    </Section>
  );
}

/* ────────────────────────── FAQ ────────────────────────── */
const FAQS = [
  {
    q: "Does it apply to jobs without me approving?",
    a: "No. Every application is drafted for you to review. Nothing is sent until you click approve. You can edit anything before it goes out.",
  },
  {
    q: "Will my resume look like AI wrote it?",
    a: "The AI only uses details already in your resume. It reorganizes, emphasizes, and rephrases — it doesn't invent experience. You always get the final say.",
  },
  {
    q: "What if a job asks for a custom cover letter?",
    a: "We draft it based on the role's description and your background. You review, edit, and send. It becomes a two-minute task.",
  },
  {
    q: "Which ATS platforms are supported?",
    a: "Greenhouse, Lever, Ashby, and Workday cover the majority of roles. We add new integrations regularly.",
  },
  {
    q: "Is my data safe?",
    a: "Your resume is never shared with any company without your explicit action. We don't sell data. Full details in our privacy policy.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes, in one click from your dashboard. You keep access until the end of your billing period.",
  },
];

function FaqPreview() {
  return (
    <Section bg="muted" className="py-24 md:py-32">
      <SectionHeading
        align="center"
        eyebrow="FAQ"
        title="Questions people actually ask."
      />

      <div className="mx-auto mt-12 max-w-3xl divide-y hairline overflow-hidden rounded-2xl border hairline bg-white">
        {FAQS.map((f) => (
          <details key={f.q} className="group px-6 py-5">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[15px] font-medium text-ink">
              {f.q}
              <span className="grid h-6 w-6 place-items-center rounded-full border hairline text-ink-soft transition group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 text-[15px] leading-relaxed text-ink-soft">{f.a}</p>
          </details>
        ))}
      </div>
    </Section>
  );
}

/* ────────────────────────── FINAL CTA ────────────────────────── */
function FinalCTA() {
  return (
    <Section className="py-24 md:py-32">
      <div className="relative overflow-hidden rounded-3xl border hairline bg-white p-10 text-center md:p-16">
        <div className="pointer-events-none absolute inset-x-0 -top-24 h-[380px] peach-glow" />
        <div className="relative">
          <h2 className="mx-auto max-w-3xl text-balance font-display text-4xl leading-[1.05] tracking-tight text-ink md:text-6xl">
            Get your time back. Get more interviews.
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-[16px] leading-relaxed text-ink-soft">
            Free to start. Two minutes to set up. Cancel anytime.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/signup" className="btn-dark text-sm">
              Get started free <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/pricing" className="btn-ghost-ink text-sm">
              See pricing
            </Link>
          </div>
        </div>
      </div>
    </Section>
  );
}
