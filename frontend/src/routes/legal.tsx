import { createFileRoute, Link } from "@tanstack/react-router";
import { DsLogo } from "../components/ds/Logo";

export const Route = createFileRoute("/legal")({
  head: () => ({
    meta: [
      { title: "Terms & Privacy — CareerAutomated" },
      { name: "description", content: "CareerAutomated's Terms of Service and Privacy Policy." },
    ],
  }),
  component: Legal,
});

function Legal() {
  return (
    <div
      style={{
        minHeight: "100vh",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
      }}
    >
      <div className="mx-auto" style={{ maxWidth: 720, padding: "56px 24px 100px" }}>
        <Link to="/" className="inline-flex" style={{ marginBottom: 40 }}>
          <DsLogo box={30} wordmark={16} weight={700} />
        </Link>

        <h2
          id="terms"
          className="font-[var(--ds-font-display)] font-bold"
          style={{ fontSize: 28, margin: "0 0 6px" }}
        >
          Terms of Service
        </h2>
        <p style={{ fontSize: 13, color: "var(--ds-ink-400)", margin: "0 0 24px" }}>
          Last updated July 2026
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          By using CareerAutomated, you agree to let us access your resume and career profile to
          find, tailor, and prepare job applications on your behalf. We never submit an application
          without your review and approval unless you've explicitly enabled auto-apply. You're
          responsible for the accuracy of information in your profile. We may suspend accounts that
          misuse the platform to spam employers.
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          The service is provided as-is. We continuously improve matching and tailoring quality but
          don't guarantee interview or offer outcomes.
        </p>

        <h2
          id="privacy"
          className="font-[var(--ds-font-display)] font-bold"
          style={{ fontSize: 28, margin: "48px 0 6px" }}
        >
          Privacy Policy
        </h2>
        <p style={{ fontSize: 13, color: "var(--ds-ink-400)", margin: "0 0 24px" }}>
          Last updated July 2026
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          We collect your resume, career profile, and job preferences to power matching and
          tailoring. This data is never sold or shared with employers beyond what you explicitly
          submit in an application. You can export or delete your data at any time from Settings.
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          We use industry-standard encryption in transit and at rest. Contact{" "}
          <a href="mailto:privacy@careerautomated.com">privacy@careerautomated.com</a> with any
          questions.
        </p>

        <h2
          id="extension-privacy"
          className="font-[var(--ds-font-display)] font-bold"
          style={{ fontSize: 28, margin: "48px 0 6px" }}
        >
          Browser Extension Privacy
        </h2>
        <p style={{ fontSize: 13, color: "var(--ds-ink-400)", margin: "0 0 24px" }}>
          Last updated August 2026 — covers the CareerAutomated Autofill Chrome extension
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          <strong>Single purpose:</strong> the extension fills in job application forms on
          supported ATS sites (Greenhouse, Lever, Ashby) using the profile you've already built in
          your CareerAutomated account. It does nothing else.
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          <strong>What it can see:</strong> the extension only runs on job application pages on
          job-boards.greenhouse.io, boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com, and
          careerautomated.in itself — it has no access to any other site you visit, and no
          "read all your browsing" permission.
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          <strong>What it does:</strong> when you start an autofill, it reads the visible form
          fields on that one page, sends the field labels/types to your CareerAutomated account to
          get back your own answers, and fills them in. It signs a filled window's job as "ready"
          for you to open, review, and submit yourself — it never clicks a final submit button on
          your behalf.
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          <strong>What it stores:</strong> nothing beyond the browser's own local session state
          needed to track an in-progress autofill window. No form data, resumes, or answers are
          stored by the extension itself — that all lives in your CareerAutomated account, covered
          by the Privacy Policy above.
        </p>
        <p style={{ fontSize: 14.5, color: "var(--ds-ink-600)", lineHeight: 1.7 }}>
          <strong>What it never does:</strong> no advertising or analytics use of your data, no
          selling or sharing data with third parties, no tracking outside the job-board pages
          listed above. Contact{" "}
          <a href="mailto:privacy@careerautomated.com">privacy@careerautomated.com</a> with any
          questions.
        </p>

        <div style={{ marginTop: 48 }}>
          <Link to="/">← Back to home</Link>
        </div>
      </div>
    </div>
  );
}
