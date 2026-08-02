# Autonomous Session Log — 2026-08-01

Branch: `autonomous-session-2026-08-01`
Rollback tag: `pre-autonomous-session-2026-08-01` @ `01aef0a` (pushed, verified)
Operator: unsupervised run. User unavailable. All forks decided locally and logged here.

---

## 11:45 IST — Safety net verified

- Tag `pre-autonomous-session-2026-08-01` exists locally and on `origin`. Confirmed.
- Branch `autonomous-session-2026-08-01` exists on `origin` at `01aef0a`. Confirmed.
- Working tree at session start: 44 modified, 2 deleted, 739 untracked.

**Decision — restored the 2 pending deletions instead of committing them.**
`graphify-out/graph.html` and `test_scheduler.py` were showing as deleted in the working
tree (deleted before this session began). The brief forbids deleting any file this session.
Committing the deletions would have recorded them permanently on this branch, so both files
were restored via `git checkout --`. If the user intended these gone, they can be removed
after review.

**Decision — graphify-out AST cache excluded from commits.**
~660 of the 739 untracked files are `backend/graphify-out/cache/ast/v0.9.15/*.json` content-hash
cache artifacts from the graphify tool. These are regenerable build cache, not source. They are
being left untracked (NOT deleted) rather than committed, to keep the session diff reviewable.
No `.gitignore` entry added for them — that would be a repo-wide change outside this session's
scope, and the user may want them tracked.

---

## 2026-08-02 — Continuation: mobile responsiveness, deploy, and CAPTCHA determination

**Audited every real/mocked screen at 375/414px (Playwright).** Found the codebase was
already substantially responsive (no hardcoded multi-column grids, no oversized fixed
widths anywhere). One real bug found and fixed: `resume-tailor.tsx`'s "Your resume" status
card packed icon + status text + a "Build your base resume" link into one unwrapped flex
row, causing text overlap at phone widths. Fixed with `flex-col sm:flex-row`, verified
unchanged at desktop width. Note for future audits: `full_page=True` Playwright screenshots
produce false positives for `position:fixed` elements (the dashboard's hamburger button
appeared to overlap content that it doesn't actually overlap in a real scrolled viewport) —
cross-check anything suspicious against a real viewport-only screenshot before "fixing" it.

**Decision — deployed frontend to production (`vercel --prod`, aliased to careerautomated.in).**
Build passed clean (SEO/accessibility/config validators all green) before deploying. This is
the first production deploy of this session's work. Live site verified directly afterward
(200 response, no horizontal overflow, mobile nav correctly collapsed).

**Backend NOT deployed to the GCP VM this session** — all backend fixes (this log's earlier
entries plus the two below) are committed to `autonomous-session-2026-08-01` but only live
locally. Flagging this explicitly since it's easy to assume "committed" means "deployed."

**Two more real bugs found via live (not dry-run) submission attempts against Bjak (Ashby):**
1. `question_engine.py` has its own internal classifier (separate from, confusingly
   same-named as, `question_classifier.py`'s) gating the deterministic-answer path. Its
   keyword list had "country" but not "nationality" — "What is your nationality?" fell
   through to the RAG/LLM path and got answered with a literal LLM hedge string instead of
   "India". Fixed.
2. Ashby's consent-checkbox pattern (data processing agreement) renders its standard
   question-title label completely empty and marks required-ness via a CSS class instead of
   an HTML attribute — `_extract_questions()` silently dropped the entire field. First live
   attempt clicked Submit with this required box unchecked; client-side validation caught it
   before any data reached Bjak's servers, and "NEVER RESUBMIT" correctly refused to retry
   on the same page. Fixed and re-verified (checkbox visibly checked in a fresh screenshot)
   before the second live attempt.

**Finding — reCAPTCHA/hCaptcha is a confirmed hard blocker on all three ATS platforms,
not just Lever.** Direct network-level evidence, not speculation: on the second live Bjak
attempt (after both bugs above were fixed and the form was genuinely clean), the browser's
network log showed a failed request to `recaptcha.net` (`net::ERR_ABORTED`) and **no
`SubmitApplication`-style GraphQL mutation ever fired** — only the form-fill calls
(`ApiSetFormValue`). Ashby's client-side JS appears to silently no-op the actual submission
when no valid reCAPTCHA token is obtained, rather than showing a visible error. Confirmed
the reCAPTCHA script/iframe is present on a second, unrelated Ashby posting (Northwood
Space) too, and confirmed Greenhouse also loads `recaptcha.net/recaptcha/enterprise/` on
a live posting (Anthropic) — so this is very likely a platform-wide default on all three,
not a single tenant's opt-in choice. **Neither live Bjak attempt actually reached Bjak's
servers** — both were safely blocked client-side, no duplicate-application risk.

This directly answers the open question from the original brief ("does reCAPTCHA Enterprise
turn out to be a hard blocker on Greenhouse/Ashby, same as hCaptcha on Lever") — yes, on all
three, based on direct network evidence rather than assumption.

---
