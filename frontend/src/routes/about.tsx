import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Radar, Target, Bell, Scale, Compass, Zap } from "lucide-react";

import { generateMetadata } from "../lib/seo";

export const Route = createFileRoute("/about")({
  head: () => generateMetadata("/about", {
    title: "About Us",
    description: "A student-built platform, for students who don't have the advantages some campuses do."
  }),
  component: About,
});


const PILLARS = [
  { icon: Radar, title: "Coverage", body: "We track company hiring directly, not just what's posted on job boards." },
  { icon: Scale, title: "Fairness", body: "Every student gets the same visibility, regardless of college tier." },
  { icon: Compass, title: "Focus", body: "Less time searching means more time actually preparing for interviews." },
];

const STEPS = [
  { icon: Radar, title: "Track", body: "We continuously monitor career pages and ATS platforms across India." },
  { icon: Target, title: "Match", body: "We rank roles by how well they fit your resume, not just keywords." },
  { icon: Bell, title: "Notify", body: "You hear about roles the same day they open — not the same week." },
];

function About() {
  return (
    <div>
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-x-0 top-[-10%] h-[520px] peach-glow" />
        <div className="mx-auto max-w-4xl px-6 pb-16 pt-24 text-center">
          <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">About</div>
          <h1 className="mt-4 font-display text-5xl leading-tight md:text-6xl">
            We built the placement cell we <em className="italic">wished we had</em>.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-[15px] text-ink-soft">
            A student-built platform, for students who don't have the advantages some campuses do.
          </p>
        </div>
      </section>

      {/* Story */}
      <section className="mx-auto max-w-3xl px-6 pb-24">
        <div className="glass-card rounded-3xl p-10">
          <div className="text-xs font-medium uppercase tracking-widest text-ink-soft">The story</div>
          <div className="mt-4 space-y-5 font-display text-2xl leading-snug text-ink md:text-[26px]">
            <p>
              I'm a final-year engineering student at IIT Roorkee. Even at a college known for strong placements, I watched classmates at other colleges — just as talented, sometimes more — miss out on opportunities simply because recruiters never visited their campus.
            </p>
            <p className="italic">That felt unfair in a way that had nothing to do with ability.</p>
            <p>
              So I built CareerAutomated: a system that watches company career pages the way a placement cell would, for students who don't have one.
            </p>
          </div>
        </div>
      </section>

      {/* Mission */}
      <section className="border-y hairline bg-[color:var(--peach-soft)]/40">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="text-center">
            <h2 className="font-display text-4xl md:text-5xl">
              Opportunity shouldn't depend on <em className="italic">geography or reputation</em>.
            </h2>
          </div>
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {PILLARS.map((p) => {
              const Icon = p.icon;
              return (
                <div key={p.title} className="rounded-3xl border hairline bg-white p-8">
                  <div className="grid h-11 w-11 place-items-center rounded-xl peach-gradient">
                    <Icon className="h-5 w-5 text-ink" />
                  </div>
                  <h3 className="mt-5 text-lg font-medium">{p.title}</h3>
                  <p className="mt-2 text-sm text-ink-soft">{p.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How we work */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <h2 className="font-display text-3xl md:text-4xl">How we work</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.title} className="relative rounded-3xl border hairline bg-white p-6">
                <div className="absolute right-6 top-6 text-xs text-ink-soft">0{i + 1}</div>
                <div className="grid h-10 w-10 place-items-center rounded-xl peach-gradient">
                  <Icon className="h-4 w-4 text-ink" />
                </div>
                <h3 className="mt-4 text-lg font-medium">{s.title}</h3>
                <p className="mt-1 text-sm text-ink-soft">{s.body}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Team */}
      <section className="border-t hairline bg-white">
        <div className="mx-auto max-w-4xl px-6 py-24">
          <div className="text-xs font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">Team</div>
          <h2 className="mt-3 font-display text-3xl md:text-4xl">A solo founder, building in public.</h2>

          <div className="mt-10 flex flex-col items-start gap-6 rounded-3xl border hairline bg-[color:var(--peach-soft)]/40 p-8 md:flex-row md:items-center">
            <div className="grid h-20 w-20 shrink-0 place-items-center rounded-full peach-gradient font-display text-2xl">
              A
            </div>
            <div>
              <div className="text-lg font-medium">Founder</div>
              <div className="text-sm text-ink-soft">Final-year engineering student · IIT Roorkee</div>
              <p className="mt-3 max-w-lg text-sm text-ink-soft">
                Building CareerAutomated openly — sharing progress, coverage, and honest limits. If you're a student who wants early access, write to us.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t hairline bg-[color:var(--peach-soft)]/40">
        <div className="mx-auto max-w-3xl px-6 py-24 text-center">
          <h2 className="font-display text-4xl md:text-5xl">
            Come be part of the <em className="italic">early story</em>.
          </h2>
          <Link to="/upload" className="btn-peach mt-8"><Zap className="h-4 w-4" /> Upload your resume <ArrowRight className="h-4 w-4" /></Link>
        </div>
      </section>
    </div>
  );
}
