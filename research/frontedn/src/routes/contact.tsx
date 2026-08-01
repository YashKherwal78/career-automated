import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Mail, Send, CheckCircle2 } from "lucide-react";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact — CareerAutomated" },
      { name: "description", content: "Get in touch about your account, a bug, a partnership, or bringing CareerAutomated to your campus." },
      { property: "og:title", content: "Contact — CareerAutomated" },
      { property: "og:description", content: "Reach a real human. General questions, bug reports, campus partnerships and billing." },
    ],
  }),
  component: Contact,
});

type Topic = "General" | "Bug Report" | "Partnership/Campus" | "Billing";

function Contact() {
  const [sent, setSent] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", topic: "General" as Topic, message: "" });

  return (
    <div>
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-x-0 top-[-10%] h-[420px] peach-glow" />
        <div className="mx-auto max-w-3xl px-6 pb-12 pt-24 text-center">
          <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">Contact</div>
          <h1 className="mt-4 font-display text-5xl leading-tight md:text-6xl">
            Talk to <em className="italic">us</em>.
          </h1>
          <p className="mx-auto mt-4 max-w-lg text-[15px] text-ink-soft">
            Real humans, based in India. Usually reply within a business day.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="grid gap-8 lg:grid-cols-[1.4fr,1fr]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setSent(true);
            }}
            className="rounded-3xl border hairline bg-white p-8"
          >
            {sent ? (
              <div className="flex flex-col items-center py-8 text-center">
                <div className="grid h-14 w-14 place-items-center rounded-2xl peach-gradient">
                  <CheckCircle2 className="h-6 w-6 text-ink" />
                </div>
                <h2 className="mt-5 font-display text-3xl">Message received</h2>
                <p className="mt-2 max-w-sm text-sm text-ink-soft">Thanks for writing in. We'll get back to you soon.</p>
                <button onClick={() => { setSent(false); setForm({ name: "", email: "", topic: "General", message: "" }); }} className="btn-ghost-ink mt-6 text-sm">
                  Send another
                </button>
              </div>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Your name">
                    <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-xl border hairline bg-white px-3 py-2.5 text-sm outline-none focus:border-[color:var(--peach-deep)]" placeholder="Aarav Sharma" />
                  </Field>
                  <Field label="Email">
                    <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-xl border hairline bg-white px-3 py-2.5 text-sm outline-none focus:border-[color:var(--peach-deep)]" placeholder="you@example.com" />
                  </Field>
                </div>

                <Field label="Topic" className="mt-4">
                  <select
                    value={form.topic}
                    onChange={(e) => setForm({ ...form, topic: e.target.value as Topic })}
                    className="w-full rounded-xl border hairline bg-white px-3 py-2.5 text-sm outline-none focus:border-[color:var(--peach-deep)]"
                  >
                    <option>General</option>
                    <option>Bug Report</option>
                    <option>Partnership/Campus</option>
                    <option>Billing</option>
                  </select>
                </Field>

                <Field label="Message" className="mt-4">
                  <textarea
                    required
                    rows={6}
                    value={form.message}
                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                    className="w-full resize-none rounded-xl border hairline bg-white px-3 py-2.5 text-sm outline-none focus:border-[color:var(--peach-deep)]"
                    placeholder="Tell us what's on your mind…"
                    maxLength={2000}
                  />
                </Field>

                <button type="submit" className="btn-peach mt-6 text-sm">
                  <Send className="h-4 w-4" /> Send message
                </button>
              </>
            )}
          </form>

          <aside className="space-y-4">
            <div className="rounded-3xl border hairline bg-[color:var(--peach-soft)]/50 p-6">
              <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">Email</div>
              <a href="mailto:hello@careerautomated.com" className="mt-2 inline-flex items-center gap-2 text-sm font-medium">
                <Mail className="h-4 w-4" /> hello@careerautomated.com
              </a>
            </div>
            <div className="rounded-3xl border hairline bg-white p-6">
              <div className="text-xs font-medium uppercase tracking-widest text-ink-soft">Campus & partnerships</div>
              <p className="mt-2 text-sm text-ink-soft">Bringing CareerAutomated to your placement cell or student community? Pick <em>Partnership/Campus</em> in the form.</p>
            </div>
            <div className="rounded-3xl border hairline bg-white p-6">
              <div className="text-xs font-medium uppercase tracking-widest text-ink-soft">Also on</div>
              <div className="mt-2 flex gap-4 text-sm">
                <a className="hover:underline" href="https://linkedin.com" target="_blank" rel="noreferrer">LinkedIn</a>
                <a className="hover:underline" href="https://twitter.com" target="_blank" rel="noreferrer">Twitter</a>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children, className = "" }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={`block ${className}`}>
      <div className="mb-1.5 text-xs uppercase tracking-widest text-ink-soft">{label}</div>
      {children}
    </label>
  );
}
