# Session Summary — autonomous-session-2026-08-01

Covers both the original autonomous run (2026-08-01) and its direct continuation
(2026-08-02, same branch). Full decision-by-decision detail is in `SESSION_LOG.md`.

## What shipped

**Auto-apply engine (Priority 1) — substantially hardened, real submission still not confirmed.**
- Dispatcher wiring, `test_mode` safety threading, and ~15 live-handler bugs from the prior
  session were committed (were sitting uncommitted).
- This continuation found and fixed 4 more real bugs via live testing against real postings:
  work-authorization answered "Yes" regardless of country (a false statement on a US
  posting), an EEO race question defaulting to "Hispanic or Latino" on a punctuation
  mismatch, a nationality question answered with a literal LLM hedge string instead of
  "India", and a required consent checkbox silently dropped entirely by the extractor
  (caught before any bad data was sent — see below).
- Built `scripts/real_submit_runner.py` and `scripts/check_job_liveness.py` — a safe,
  capped (5 live submissions max, disk-persisted counter), evidence-logging way to run real
  attempts, plus a liveness preflight (36% of DB-"ACTIVE" jobs turned out to already be
  closed).
- **Confirmed, load-bearing finding: reCAPTCHA/hCaptcha is a real, hard blocker on all
  three supported platforms (Greenhouse, Lever, Ashby), not just Lever.** For Lever this
  shows up as a visible interactive puzzle challenge. For Ashby it's silent — the browser's
  network log shows the reCAPTCHA request failing (`net::ERR_ABORTED`) and the actual submit
  GraphQL mutation simply never fires, no error shown to the automation. Confirmed present
  on a second unrelated Ashby posting and on a live Greenhouse posting too. This was
  confirmed via two live (not dry-run) attempts against a real Bjak posting — both were
  safely blocked before any data reached Bjak's servers (no duplicate-application risk), but
  neither succeeded either.
- **Net result: 0/5 live-submission budget used toward a confirmed success.** The auto-apply
  pipeline itself is working correctly (form-filling, question-answering, safety escalation
  are all solid) — the actual ceiling right now is the CAPTCHA wall, which no amount of
  field-mapping/keyword fixing solves.

**Mobile responsiveness (Priority 2) — done and deployed.**
- Audited every real and mocked screen at 375/414px. Found the app was already
  substantially responsive-ready (no hardcoded multi-column grids, no oversized fixed
  widths). One real bug fixed (overlapping text on the Tailoring page's resume-status card).
- Full production build passed clean (SEO/accessibility/config validators all green).
- **Deployed to production** via `vercel --prod`, live at careerautomated.in, verified
  directly post-deploy (200 response, no horizontal overflow, mobile nav collapses
  correctly).
- Backend is NOT deployed to the GCP VM — all backend fixes are committed to this branch
  but only live locally right now.

**Referral system + automail integration (Priority 3) — not started**, in either the
original autonomous run or this continuation. No `automail` repo found locally; per the
original brief's instruction, this should be flagged rather than guessed at.

## What's still open / needs your judgment

1. **The CAPTCHA finding is the big one.** Getting past it reliably likely needs a real
   architecture change — e.g. a browser-extension-based approach running in your actual
   logged-in Chrome (real cookies/session/history), which inherently looks far less
   bot-like to risk-scoring systems than a fresh Playwright-launched context, stealth
   patches or not. That's a genuinely bigger rebuild, not a quick fix, and is worth a
   deliberate conversation before starting.
2. Backend fixes need deploying to the GCP VM — separate step, not done this session.
3. Priority 3 (referral/automail) needs a decision: do you have the `automail` repo
   somewhere specific, or should I search your GitHub account for it?
4. The dead `engine.py`/`executor.py`/`app_queue.py` system (references DB tables that
   don't exist in the live Postgres DB) is still in place, documented as dead, not deleted —
   your call on whether/when to remove it.
5. Everything is on `autonomous-session-2026-08-01`, not merged to `v2`/`main` — that merge
   is your call too.
