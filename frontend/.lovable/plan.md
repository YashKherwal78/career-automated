## Goal

Refactor the existing CareerAutomated site into a premium, product-first SaaS experience. Reposition from "job tracker for Indian engineering students" to **AI Career Operating System** — automates repetitive job-hunt work (search, tailor, apply, follow up) so users focus on interviews.

Keep existing architecture (TanStack Start + Tailwind v4 + shadcn). Improve, don't rewrite.

## Scope

### 1. Design + typography system (`src/styles.css`)
- Swap display font from Instrument Serif → **General Sans**, keep **Inter** for body (load via Fontshare `<link>` in `__root.tsx`).
- Define a strict type scale via `@theme` tokens: `display`, `h1`–`h4`, `body-lg`, `body`, `caption`, `label`.
- Tone down peach: keep as a single accent (buttons, subtle highlights), remove decorative glows/gradients from section backgrounds. Neutral off-white base, more whitespace.
- Preserve `btn-peach` / `btn-ghost-ink` utilities; add `btn-primary-dark` (ink-filled) for high-conviction CTAs.

### 2. Reusable primitives (`src/components/ui/*` and `src/components/primitives/*`)
New/normalized:
- `Container`, `Section`, `Eyebrow`, `SectionHeading`, `Prose`
- `Button` (variants: primary, secondary, ghost, dark)
- `Card`, `FeatureCard`, `PricingCard`, `FAQItem`
- `Navbar`, `Footer` (refactor existing `SiteNav`/`SiteFooter` to use primitives)
- `MotionFadeIn`, `MotionStagger` (framer-motion wrappers respecting `prefers-reduced-motion`)
- `AuthCard`, `SocialButton`, `FormField` (for Sign Up, presentation-only)

Install `framer-motion`.

### 3. Landing page (`src/routes/index.tsx`) — full rewrite
Section order + copy intent:
1. **Nav** — logo, links (Product, Pricing, FAQ), Sign in / Get started
2. **Hero** — H1 answers what+who+outcome in one line. Sub-copy: 2 lines max. Two CTAs. Product visual (application-pipeline mock) with subtle entrance motion.
3. **Product overview** — one paragraph: "CareerAutomated is an AI career OS…"
4. **The problem** — 4 concrete frustrations (searching boards, retailoring resumes, ATS forms, tracking).
5. **The solution** — outcome-led paragraph + 3 outcome pillars (apply faster, stay organized, better applications).
6. **How it works** — 4 steps: Upload resume → We find matches → AI tailors + drafts → You approve & apply.
7. **Core features** — 6 feature cards, each Feature → Benefit → Outcome.
8. **Why we're different** — comparison strip vs job boards / resume builders / AI chatbots.
9. **Pricing preview** — 3 compact cards linking to `/pricing`.
10. **FAQ** — 6 questions.
11. **Final CTA** — one action.
12. **Footer.**

Copy rewritten to remove SaaS clichés and Indian-student-only framing (broaden to any job seeker; keep "made with care" tone).

### 4. Pricing page (`src/routes/pricing.tsx`) — refactor
- Rename tiers to **Free / Pro / Premium** with monthly/yearly toggle (yearly = ~20% off shown inline).
- Rebuild cards via `PricingCard` primitive.
- Keep comparison table + FAQ, restyled through primitives.
- Enterprise contact row at bottom → links to `/contact`.

### 5. Sign Up page (new: `src/routes/signup.tsx`)
Frontend only, no auth wiring.
- Email, Password, Confirm Password fields with client-side zod validation, error + loading UI states.
- Google + GitHub social buttons (disabled placeholders with tooltip "Coming soon").
- Split layout: form left, brand/quote panel right on desktop; stacked on mobile.
- Submit handler = stubbed async delay, then toast; TODO comment marking the Supabase integration point.
- Add `/signup` link to nav CTA.

### 6. Nav + Footer refactor
- Nav: Product, Pricing, FAQ, Sign in (ghost) + Get started (primary → `/signup`).
- Remove "Upload Resume" primary CTA from nav (moves to hero/final CTA).
- Footer trimmed, aligned to new IA.

### 7. Housekeeping
- Update `__root.tsx` head meta + fonts.
- Update sitemap to include `/signup`.
- Keep About / FAQ / Contact / Privacy / Terms / Upload routes; lightly restyle only if they break under new typography. No copy rewrite for those in this pass.
- Ensure `prefers-reduced-motion` respected across motion wrappers.

## Out of scope
- Backend, auth, DB wiring (Supabase deferred).
- Rewriting About/FAQ/Contact/Privacy/Terms/Upload copy.
- Real dashboard.
- Analytics / feature flags.

## Technical notes
- Framer Motion via `bun add framer-motion`.
- Fonts via `<link>` in `__root.tsx` head (Tailwind v4 rule — no remote `@import` in CSS).
- All colors continue to route through semantic tokens in `styles.css`; no hardcoded hex in components.
- Auth-ready structure: `signup.tsx` calls a local `onSignup(values)` function stub kept in the component; form UI is pure presentation so swapping in a Supabase call later is one function body.

## GitHub push
I can't run git myself. After this ships, connect the repo via the Lovable Plus menu → GitHub → Connect project; from then on every change auto-syncs to GitHub.
