import { createFileRoute } from "@tanstack/react-router";
import { generateMetadata } from "../../lib/seo";

export const Route = createFileRoute("/about/product")({
  head: () => generateMetadata("/about/product", {
    title: "AI Product Architecture & Features",
    description: "Learn how CareerAutomated AI Career Operating System uses intelligent agents to search jobs, optimize resumes, and automate applications.",
  }),
  component: AboutProduct,
});

function AboutProduct() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <header className="mb-12">
        <h1 className="font-display text-4xl leading-tight md:text-5xl">
          CareerAutomated AI Product Architecture
        </h1>
        <p className="mt-4 text-lg text-ink-soft">
          A deep dive into how our AI agents automate career workflows while keeping you in full control.
        </p>
      </header>

      <main className="space-y-12">
        <section>
          <h2 className="text-2xl font-semibold mb-4">1. Intelligent Job Discovery</h2>
          <p className="text-ink-soft leading-relaxed">
            Unlike traditional job boards that rely on keyword matching, CareerAutomated uses LLM agents to analyze the semantics of job descriptions. Our system directly scrapes company career pages, identifies matching open roles, and rates their eligibility based on your resume profile.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">2. ATS Optimization & Resume Tailoring</h2>
          <p className="text-ink-soft leading-relaxed">
            Our ATS resume tailoring engine breaks down target job descriptions to identify key skills, keywords, and qualifications. It then suggests precise adjustments to your resume, formatting bullet points to highlight your relevant experience and ensure maximum compatibility with Applicant Tracking Systems.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">3. Application Automation</h2>
          <p className="text-ink-soft leading-relaxed">
            We automate the tedious application submission process by parsing portals and forms. Crucially, CareerAutomated enforces a strict approval workflow: our agents draft the cover letters and forms, but no application is ever submitted without your explicit review and sign-off on the dashboard.
          </p>
        </section>
      </main>
    </div>
  );
}
