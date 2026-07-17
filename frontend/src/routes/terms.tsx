import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/terms")({
  head: () => ({
    meta: [
      { title: "Terms of Service — CareerAutomated" },
      { name: "description", content: "Terms under which you use CareerAutomated." },
      { property: "og:title", content: "Terms of Service — CareerAutomated" },
      { property: "og:description", content: "Plain-language terms of using CareerAutomated." },
    ],
  }),
  component: Terms,
});

function Terms() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-24">
      <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">Legal</div>
      <h1 className="mt-3 font-display text-5xl">Terms of Service</h1>
      <p className="mt-3 text-sm text-ink-soft">Last updated: {new Date().toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</p>

      <div className="mt-10 space-y-6 text-[15px] leading-relaxed text-ink-soft">
        <p className="text-ink">By using CareerAutomated, you agree to these terms. Read them carefully — they're written to be plain and short.</p>

        <Section title="1. Using the service">
          You must be at least 16 years old and provide accurate information. You are responsible for keeping your account credentials safe.
        </Section>

        <Section title="2. Your content">
          You keep ownership of your resume and any content you upload. You give us permission to process it to provide the service (matching, ranking, storage, retrieval).
        </Section>

        <Section title="3. Acceptable use">
          Don't use the service to scrape, resell, or misrepresent data. Don't upload content that isn't yours or that violates the law.
        </Section>

        <Section title="4. Paid plans">
          Pro is billed monthly or annually. Cancel any time from your dashboard — you keep access until the end of your billing period. Refunds within 7 days of first upgrade on request.
        </Section>

        <Section title="5. Availability">
          We work hard to keep the service reliable but we don't guarantee 100% uptime. We may change or discontinue features with reasonable notice.
        </Section>

        <Section title="6. Liability">
          The service is provided "as is". To the fullest extent permitted by law, we are not liable for indirect or consequential damages arising from your use of the service.
        </Section>

        <Section title="7. Termination">
          You may close your account at any time. We may suspend accounts that violate these terms.
        </Section>

        <Section title="8. Governing law">
          These terms are governed by the laws of India.
        </Section>

        <Section title="9. Contact">
          For any question about these terms, email <a href="mailto:hello@careerautomated.com" className="text-[color:var(--peach-deep)] underline">hello@careerautomated.com</a>.
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="font-display text-2xl text-ink">{title}</h2>
      <p className="mt-2">{children}</p>
    </div>
  );
}
