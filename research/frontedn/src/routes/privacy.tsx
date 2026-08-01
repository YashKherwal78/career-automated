import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy Policy — CareerAutomated" },
      { name: "description", content: "How CareerAutomated collects, uses, stores and protects your resume and personal data." },
      { property: "og:title", content: "Privacy Policy — CareerAutomated" },
      { property: "og:description", content: "Plain-language summary of what data we collect, why, and your rights." },
    ],
  }),
  component: Privacy,
});

function Privacy() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-24">
      <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">Legal</div>
      <h1 className="mt-3 font-display text-5xl">Privacy Policy</h1>
      <p className="mt-3 text-sm text-ink-soft">Last updated: {new Date().toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</p>

      <div className="prose prose-neutral mt-10 max-w-none text-[15px] leading-relaxed text-ink-soft">
        <p className="text-ink">
          CareerAutomated ("we", "us") helps students discover job opportunities by matching their resume against openings we track on public company career pages. This policy explains what data we collect, why, and how you can control it.
        </p>

        <h2 className="mt-10 font-display text-2xl text-ink">1. What we collect</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li><strong className="text-ink">Resume data</strong> you upload or build — including name, contact information, education, skills, projects and work experience.</li>
          <li><strong className="text-ink">Account data</strong> — email address and authentication information.</li>
          <li><strong className="text-ink">Usage data</strong> — pages visited, matches viewed, applications tracked. Used to improve the product.</li>
        </ul>

        <h2 className="mt-10 font-display text-2xl text-ink">2. How we use your data</h2>
        <p className="mt-3">We use your resume to match you against openings we track. We do not sell your data. We do not share your resume with any company or recruiter without your explicit action or permission.</p>

        <h2 className="mt-10 font-display text-2xl text-ink">3. Storage & security</h2>
        <p className="mt-3">Your data is stored on encrypted infrastructure. Access is restricted to authorized personnel who need it to operate the service. We use industry-standard practices to protect against unauthorized access.</p>

        <h2 className="mt-10 font-display text-2xl text-ink">4. Your rights</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>Access or export your data at any time from your dashboard.</li>
          <li>Delete your account, which removes your resume and personal data from our systems.</li>
          <li>Contact us if you have any privacy question — see <a href="/contact" className="text-[color:var(--peach-deep)] underline">Contact</a>.</li>
        </ul>

        <h2 className="mt-10 font-display text-2xl text-ink">5. Third parties</h2>
        <p className="mt-3">We use a small number of well-known service providers (hosting, email, analytics) to run CareerAutomated. These providers process data on our behalf and are bound by their own privacy commitments.</p>

        <h2 className="mt-10 font-display text-2xl text-ink">6. Changes to this policy</h2>
        <p className="mt-3">If we make material changes, we'll notify you by email or in-product before they take effect.</p>

        <h2 className="mt-10 font-display text-2xl text-ink">7. Contact</h2>
        <p className="mt-3">Questions? Email <a className="text-[color:var(--peach-deep)] underline" href="mailto:hello@careerautomated.com">hello@careerautomated.com</a>.</p>
      </div>
    </div>
  );
}
