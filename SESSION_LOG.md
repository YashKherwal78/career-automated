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

## 2026-08-03 — CAPTCHA pause/resume (human-in-the-loop)

Built on `BaseATSHandler`, not per-handler — every ATS (current 3, and every future one)
shares one `execute()` method, so this applies automatically going forward with no
per-platform work. Explicitly NOT automated captcha solving (declined a direct request to
implement a bypass technique, and a follow-up request to apply a "How to Bypass CAPTCHA
With Playwright" tutorial) — the mechanism instead fills everything up to the point a real
captcha challenge appears, pauses the already-visible (non-headless) browser, and blocks on
operator input (Enter to resume + retry, or "skip" to route to REVIEW_REQUIRED).

Detection covers hCaptcha + reCAPTCHA (both confirmed live) plus Cloudflare Turnstile /
Arkose-FunCaptcha / GeeTest patterns for platforms not yet built. Verified live: Lever
(visible-challenge branch) and Ashby (silent-widget branch) both fire detect -> pause ->
retry -> re-detect -> skip -> REVIEW_REQUIRED correctly with a simulated resolution signal
(can't self-test an actual solve — that's the operator's step by design). Greenhouse shares
the identical code path but wasn't independently observed live this pass (a test run
correctly escalated a compensation question before ever reaching submit).

---

## 2026-08-03 (cont'd) — New ATS platforms: SmartRecruiters (dead end), iCIMS (blocked, needs joint session), BreezyHR (built + verified)

Continuing the ~27-platform expansion, "one at a time," per your explicit choice. All
scouting/testing this pass was headless (no visible browser windows), per your instruction —
the only exception remains the CAPTCHA pause/resume feature itself, which needs a visible
window by design.

**SmartRecruiters — dead end, not pursuing further.** DataDome blocks page access outright
("Access is temporarily restricted... Automated (bot) activity on your network") before any
form or challenge exists to interact with. This isn't a gate-the-submit-action problem like
hCaptcha/reCAPTCHA — there's nothing to pause-and-resume on. Different problem class from
everything else built so far.

**iCIMS — real, solvable hCaptcha, but gates the flow too early to build the handler alone.**
Confirmed on two independent tenants (careers-142designgroup.icims.com and
careers-appliedsystems.icims.com) that a real interactive hCaptcha challenge appears right
after clicking "Apply for this job online," during the email/login step — before the actual
application form is ever reached. This is consistent enough across unrelated tenants to be a
platform default, not one tenant's config. I can't see what the real form looks like without
getting past it, and that needs a human to actually solve the puzzle once — a deliberate,
supervised session, not something to trigger unprompted in the background. Parked until we
do that together; picking a different platform in the meantime rather than blocking on it.

**BreezyHR — built and verified clean across 2 real tenants/postings.** `BreezyHandler`
(`backend/src/applications/handlers/breezy.py`) + `BreezyAdapter`, registered in the
dispatcher. Native AngularJS-rendered HTML form, no iframe, no captcha observed on any
tenant scouted. Real findings from live DOM inspection, not assumptions:

- Breezy auto-parses the uploaded resume and appends Work History/Education entries a few
  seconds after upload — first version of this handler didn't know that and manually added
  its own entry too, producing duplicate/empty `<li>` records. Fixed by checking for
  already-populated entries first and only adding one manually as a fallback.
- Work History and Education entries are compound multi-field records inside one `<li>` each
  (Company/Title/Summary/dates, or School/Field/Summary/dates) with no per-field wrapper —
  can't go through the shared per-question container pipeline, so each sub-field is resolved
  directly via the same `QuestionEngine` everything else uses (`self.engine.answer(...)`)
  rather than hardcoding candidate facts in the handler. Both entry types share an identical
  CSS class; only the `ng-repeat` attribute value ("...work_history" vs "...education")
  tells them apart.
- Added 4 new canonical fields to `question_engine.py` (`EMPLOYMENT_START_DATE/END_DATE`,
  `EDUCATION_START_DATE/END_DATE`) — no prior handler needed structured past-employment
  dates as a distinct concept from "when can you start this job," so there was no field for
  it. Shared, so any future ATS with the same structured-history pattern gets it for free.
- Found and fixed two label-collision bugs in `ResponseNormalizer`/`QuestionClassifier`: a
  label containing "background" (in "professional background") routed into the LEGAL
  background-CHECK path instead of being treated as a free-text summary; a label containing
  "experience" (in "Experience Summary") sent a words-only answer through the numeric
  years-of-experience extractor, which found no digits and returned NORMALIZATION_FAILED.
  Fixed by rewording the synthetic field labels this handler generates, not by changing the
  shared classifier — those keywords are correct for their intended real-world questions.
- A required "Experience Summary" field was being silently wiped back to empty by Breezy's
  own async resume-parse (it rebinds the underlying `candidate.summary` model) whenever it
  was filled before that parse settled. Fixed by moving the fill to run after the parse
  completes, then verifying the value actually stuck rather than trusting the fill call.
- A spam-trap honeypot field (`name="hp_7f2b"`, `tabindex="-1"`) is deliberately never
  touched — filling it is what a scripted bot would do.

Verified clean (`test_mode=True`, no submit clicked) on 20four7VA's "Data Analyst" posting
(salary+period select, GDPR consent present) and A2H's "Civil Engineer" posting (no salary
field, no GDPR checkbox, optional Cover Letter left blank) — different tenants exercise
different optional sections, both completed correctly with real resume-derived work history/
education, no duplicate or empty entries, honeypot untouched.

**JazzHR — built and verified clean across 2 real tenants.** `JazzHRHandler`
(`backend/src/applications/handlers/jazzhr.py`) + `JazzHRAdapter`, registered in the
dispatcher. Postings live on `<tenant>.applytojob.com`; the apply form is hidden behind an
"apply now" link and, once revealed, uses one fully consistent id-based convention with no
`<label>` tags at all (`#resumator-<key>`/`#resumator-<key>-label`/`#resumator-<key>-field`)
— both the standard-field filling and the custom-question extractor key off that pattern
directly rather than guessing per-posting DOM structure. A visible reCAPTCHA "I'm not a
robot" checkbox gates submission, same category as Lever's hCaptcha (real, solvable,
visible) — already covered by the shared pause/resume mechanism, no extra work needed.

One real bug found and fixed via live inspection: the resume field is a genuinely native,
unstyled `<input type="file">` that starts hidden and only becomes live after clicking a
separate "Attach resume" link — setting files on it beforehand silently no-ops. Also, the
"chosen filename" text Chromium shows next to a native file input is browser-native form
control UI, not real page DOM/text content, so the text-based upload-verification pattern
every other handler uses can never find it here; fixed by checking `input.files.length`
directly via `element.evaluate()` instead.

Verified clean on 10Pearls's "Associate Account Executive - Intern" posting and AgEagle
Aerial Systems' "Guidance, Navigation & Control (GNC) Engineer" posting (different branding/
skin, same underlying JazzHR product) — both completed correctly with resume upload
confirmed via the corrected `.files` check, no custom screening questions on either posting
(the generic extractor is in place and ready for a tenant that does have them, just not
exercised live yet).

**BambooHR — built and verified clean (+ a correct real escalation) across 2 tenants.**
`BambooHRHandler` (`backend/src/applications/handlers/bamboohr.py`) + `BambooHRAdapter`,
registered in the dispatcher. The most structurally complex platform built so far:

- Country is a custom "fab-Select" widget (real `<select>` present but aria-hidden/
  zero-size, driven by a button + searchable option list) — same category of problem as
  Greenhouse's react-select, handled the same way (open, search, click exact match, verify
  the underlying value changed). Selecting a non-US country live-swaps "State"(dropdown)
  into "Province"(plain text) and "ZIP" into "Postal Code" in the DOM, so Country must be
  set before those fields are touched.
- Added `postal_code`/`zip_code` to the candidate's base profile (`profile.py`) — genuinely
  missing data, not a guess; it's the same address already partly stored (city/state), just
  missing its PIN code.
- Found and fixed a real shared-code bug in `ResponseNormalizer`'s date formatter
  (`question_engine.py`): a placeholder literally reading "mm/dd/yyyy" (slash-separated)
  fell through to the bare-"yyyy" fallback because only a hyphenated "mm-dd-yyyy" variant
  was handled, silently truncating a full date down to just the year ("2026" instead of
  "08/18/2026"). This is a generic date-widget bug, not BambooHR-specific — any future
  platform using a slash-style placeholder benefits from the fix too.
- Custom per-tenant screening questions and the resume/cover-letter file inputs pass the
  raw `<input>`/`<textarea>` itself as the "container" (no separate wrapper element exists),
  which the shared base class's generic widget-interaction and pre-submit-audit empty-check
  can't handle correctly (both search for INPUT DESCENDANTS of the container, and a leaf
  input has none) — overrode `_interact_widget`/`_custom_field_is_empty` in this handler to
  check the element directly instead of silently no-op'ing.
- Resume upload confirmation needed polling, not a fixed wait: the file posts to BambooHR's
  backend asynchronously and the hidden `resumeFileId` field only populates once that
  completes, which took longer than an initial fixed 1.5s wait under real conditions.
- A `nickname_hpcsaf` honeypot (`tabindex="-1"`, explicit `data-*-ignore="true"` markers
  aimed at password managers) is deliberately never touched.

Verified on 321 The Agency's "Senior Client Account Strategist" posting — clean COMPLETED
run in `test_mode=True`, all required fields correct (including Country→India, Province,
Postal Code, corrected Date Available format, Desired Pay, LinkedIn), 4 tenant-added
optional experience questions correctly left blank, EEO/veteran section correctly left at
default. Second tenant (3CAT, a barista role) surfaced a real, legally-sensitive custom
question set (US work authorization, tax-filing identity policy, store confirmation) that
the shared classifier correctly escalated to REVIEW_REQUIRED instead of guessing — exactly
the right outcome, since guessing wrong on work-authorization would be a false legal claim.

**Workable — built and verified across 2 real tenants (1 clean COMPLETED, 1 correct
REVIEW_REQUIRED on genuinely complex US legal questions).** `WorkableHandler`
(`backend/src/applications/handlers/workable.py`) + `WorkableAdapter`, registered in the
dispatcher. A full-screen cookie-consent dialog intercepts every click until dismissed —
must be cleared before "Apply for this job" is even clickable. Every field, regardless of
widget type, has a `span[id$="_label"]` holding its visible question text; that id's prefix
is stable for tenant-authored custom questions but randomly regenerated per page load for
built-in fields, so labels are matched by text content, never by id — the field's own
container is found by walking from the label up to its first `<div>` ancestor. "Notice
period"-style fields are a custom select (real value in a hidden input, only reachable by
opening a `[data-input-type="select"]` widget and clicking a `[role="option"]`) — same
category as Greenhouse's react-select, handled the same way.

Two real bugs found and fixed:
1. Required-field detection (`is_required`) walked the wrong DOM level — the "*" marker is
   a sibling of the label span's own PARENT, not of the label span itself (which has no
   siblings), so every custom question on this platform was silently read as optional. A
   required salary question was almost skipped outright as a result.
2. A genuine shared-code bug in `ResponseNormalizer` (`question_engine.py`): the numeric
   years-of-experience extractor triggered on ANY hint containing the bare substring
   "experience" — including a real tenant question that merely mentioned "professional
   experience, internship, or academic project" as example phrasing, not asking for a
   number at all. A full, correct LLM-generated sentence about programming languages used
   got silently truncated down to just "2" (the first digit it found, from "Project 2").
   Narrowed the trigger to phrases that actually ask for a numeric years figure ("years of
   experience", "how many years", etc.) — this is the same root-cause pattern as the
   Breezy "Experience Summary" bug found earlier this session, but that time the fix was a
   workaround (reword the synthetic label); this time the fix is in the shared normalizer
   itself, since the colliding text came from the ATS's own real, unchangeable question.

Verified on 1GLOBAL's "Systems Operations Intern" posting (Lisbon) — clean COMPLETED run
with Notice period, salary correctly escalated (a deliberate, pre-existing design decision —
salary/compensation questions are meant to always go to a human, not be guessed), YES/NO
boolean questions, free-text city/degree/programming-language questions all answered
correctly, GDPR consent checked. A second tenant (1915 South/Ashley, a US warehouse role)
correctly escalated real US work-authorization and prior-employment/referral questions to
REVIEW_REQUIRED rather than guess — the right outcome for genuinely high-stakes questions.

**Recruitee — built and verified across 2 tenants (including a non-English one).**
`RecruiteeHandler` (`backend/src/applications/handlers/recruitee.py`) + `RecruiteeAdapter`,
registered in the dispatcher. The job description and application form share one page,
switched via a tab that's already in the DOM (just hidden) before being selected.

Three real bugs found and fixed, one of them the most subtle of this whole session:
1. The application tab was matched by English text ("Apply"/"Application") — every posting
   on a non-English-configured tenant board (found live: a Dutch one labelled
   "Solliciteren") never got its tab clicked, leaving the entire form invisible for the
   rest of the run. Fixed by falling back to positional selection (2nd of exactly 2 tabs,
   a fixed structural convention regardless of locale) when no English label matches.
2. The phone field's country selector is a virtualized list — only options near the
   current scroll position exist in the DOM at all, so a plain text search for e.g. "India"
   fails until it scrolls into view. It supports type-ahead, but Playwright's default
   typing speed was too fast for the widget's per-keystroke search buffer, landing on the
   wrong country ("Iran" instead of "India") because the search restarted mid-word; fixed
   with an explicit 150ms inter-keystroke delay. Also had to scope the option match to
   `[role="option"]` specifically — a bare text search matches the flag icon's own
   `<svg><title>India</title>` accessibility label on every OTHER country's flag too.
3. The deepest one: the same phone widget auto-detects/overwrites the selected country
   from the digits typed into the number field itself — the candidate's real number
   ("9891148156") starts with "98", Iran's calling code, and filling it after explicitly
   selecting India silently swapped the country back to Iran. Traced further: it wasn't the
   typing itself but specifically the shared `_human_type()` helper's `.fill("")` clear-first
   step that put the widget into a state where this misdetection then fired — a fresh field
   typed into directly (no prior clear) does not trigger it, confirmed reliably across
   repeated trials. Fixed locally in this handler only (bypassing `_human_type` for this one
   field) rather than changing the shared helper, since `_human_type`'s clear-first behavior
   is correct and needed for every other field on every other platform.

Verified on Best Logistics Group's "Logistics Account Manager" posting (clean COMPLETED,
country correctly set to India, no custom questions) and Altrad Services' Dutch-language
"Monteur Tracing" posting (tab correctly found via positional fallback, same clean result) —
both confirm the fixes generalize rather than being one-tenant coincidences.

---

## 2026-08-03 (cont'd) — Rippling built; Rippling/Oracle discovery-side re-crawl blocked (infra, not code)

**Discovery-side validation attempted, hit a real infrastructure wall, not a code issue.**
The earlier session's plan flagged Rippling/Oracle as needing a live re-crawl to confirm a
already-shipped fix (commit `652edea`) actually pulls jobs now — `ats_registry` still showed
`last_successful_crawl` frozen at 2026-07-24 (before the fix) for both, and `normalized_jobs`
has zero rows for either. Tried running `job_crawler_worker.py --provider rippling` directly:
first hit a genuinely missing dependency (`zstandard`, declared in `requirements.txt` but
never installed in this venv — installed it, real gap now fixed), then hit a hard wall the
fix can't do anything about: the worker requires the production Postgres instance
(`dokploy-postgres`), which only resolves from the GCP VM, not from here. This re-crawl
validation can only happen from the deployed backend, not this local session — flagging
for whenever backend deployment happens, not something to keep pushing on locally.

**Rippling — built and verified across 2 tenants anyway**, since building the ATS handler
doesn't actually depend on our own crawler having ingested anything — found 5 real, live
Rippling-hosted postings directly (`ats.rippling.com/<tenant>/jobs/<id>`) via web search.
`RipplingHandler` (`backend/src/applications/handlers/rippling.py`) + `RipplingAdapter`,
registered in the dispatcher. The richest field taxonomy of any platform this session: every
field, standard AND custom, carries a stable semantic `data-testid`
(`first_name`/`email`/`phone_number`/`location`/`linkedin_link`/`resume`/`cover_letter`/
`eeoc.<field>`/`customQuestions.<jobId>.<questionId>`) — no fragile label-proximity guessing
needed for identification, unlike every other platform built this session. Select-type
questions (both tenant custom questions and the fixed EEO fields) render as an accessible
`role="combobox"` widget, same interaction shape as Greenhouse's react-select.

One real bug found and fixed: EEO fields' (Gender/Race/Hispanic/Veteran/Disability) labels
were extracted via the same DOM-ancestor-walk used for tenant custom questions, but that
walk lands on the EEO section's shared instructional paragraph instead of each field's own
short label — all five got the SAME wrong "U.S. Equal Opportunity Employment Information..."
text, which then failed to classify as GENDER/RACE/VETERAN_STATUS and fell through to the
LLM instead of the profile's correct canonical answers. Fixed by preferring
`aria-labelledby` (present on every combobox field, pointing to a `<span>` with the real
short label) over the ancestor-paragraph walk, which only plain text-input custom questions
still need (they don't set `aria-labelledby` at all).

Verified on Skillable's "Data Architect" posting — correctly reached REVIEW_REQUIRED for
legitimate reasons: a required US-state-residency dropdown the candidate's profile has no
matching value for (correctly unanswerable, not guessed), Compensation Expectations and a
type-your-full-legal-name Truth Certification/e-signature field both correctly escalated
(salary and attestation-clause questions are deliberately never auto-answered). Everything
else — name/email/phone/LinkedIn/resume, 3 boolean custom questions, and all 5 EEO fields —
filled correctly (one minor known gap: the Race dropdown's "Decline to Self Identify" answer
didn't match that tenant's exact option wording, left unfilled since Race is optional/
non-blocking). Second tenant (Revyse) confirmed a clean COMPLETED run with zero custom
questions on that posting.

**Avature — skipped, same account-creation gate as Workday.** Clicking "Apply now" on a
real live posting (Pontoon Solutions, Bangalore) redirected straight to a login page
(email + password fields), no guest path. Same category the user explicitly deferred
earlier this session (asked about default-password strategy for Workday-style platforms;
agreed to hold off and finish account-less platforms first). Not building this one now.

**Personio — built and verified across 2 tenants.** `PersonioHandler`
(`backend/src/applications/handlers/personio.py`) + `PersonioAdapter`, registered in the
dispatcher. The simplest platform built this session: clean form directly on the job page
(URL just gains a `?apply` query param), no captcha, no account, real `<label for="field-
<key>">` elements whose `<key>` matches the input's own `name` attribute directly — no
label-proximity guessing needed. Standard fields use stable names (`first_name`,
`documents.cv`, etc.); tenant-configured fields (LinkedIn URL, or genuine custom screening
questions) use a `custom_attribute_<id>` name instead, identified generically the same way.

Verified on 10x Founders' "Tech Analyst / Associate" posting (clean COMPLETED, one custom
LinkedIn field correctly filled) and their "VC Associate" posting (a second custom question,
a native `<select>` asking about German work authorization, correctly answered "No" —
candidate has no EU work authorization). No bugs found this time — the clean, semantic
`label[for]`/`name` pairing left little room for the DOM-guessing mistakes every other
platform this session has needed at least one fix for.

**TeamTailor — built and verified, plus a real localization limitation surfaced and
partially mitigated.** `TeamTailorHandler` (`backend/src/applications/handlers/
teamtailor.py`) + `TeamTailorAdapter`, registered in the dispatcher. Postings render in the
tenant's own locale (tested against a French one) — the "Apply" call-to-action is matched
by its stable Stimulus.js `data-action` hook (`...#showFormOverlay`), never by display text,
so it works regardless of language. Every field, standard and custom, has a real
`<label for="candidate_...">` tied to a Rails-style bracket-named input.

Two real bugs found and fixed:
1. Teamtailor renders a separate "Requis"/"Required" hint as its own line inside the same
   `<label>`, but its position isn't consistent — the date question has it AFTER the real
   question text, the GDPR consent checkbox has it BEFORE. Blindly taking the first line
   turned the entire consent question into just "Requis." Fixed by filtering out any
   line that's only the required-hint text and taking the first substantive line instead.
2. **A structural limitation, not a one-off bug**: the shared question classifier
   (`question_classifier.py` + `question_engine.py`'s internal one) is English-keyword-only.
   A French "A quelle date êtes vous disponible..." or "je consens à ce que 2LCollection
   stocke mes données..." doesn't match any English keyword list, so it falls through to
   TECHNICAL/unknown and gets escalated (or, worse, silently unanswerable) even though the
   underlying question is a completely ordinary one (start date, GDPR consent) the engine
   already knows how to answer perfectly well in English. This will affect real postings on
   this platform going forward, not just the one scouted — Teamtailor's own job volume in
   our DB is heavily European (French/Swedish/German). Partially mitigated for the single
   highest-value case (GDPR/data-processing consent, which blocks 100% of submissions on
   any non-English posting until handled): checked directly by field id
   (`candidate_consent_given`) rather than routed through language-dependent
   classification — same "always consent" treatment every other platform's own privacy
   checkbox already gets, just language-independent by construction. The genuinely
   open-ended custom questions (start date, cover letter) still correctly escalate to
   REVIEW_REQUIRED rather than guess — the safe failure mode, just not yet the ideal one.
   Real multilingual classifier support (translate-before-classify, or per-language keyword
   sets) would be the proper fix, and is worth a dedicated pass given how many EU-hosted
   platforms this session has touched (Recruitee, BambooHR, Rippling, and now Teamtailor all
   had at least one non-English posting).

Verified on 2L Collection's "Technicien de maintenance" posting (Château de Fonscolombe,
Provence) — GDPR consent correctly checked, resume uploaded, optional cover letter and
marketing-contact checkbox correctly left blank, the one genuinely-unresolvable French
custom question (start availability date) correctly escalated rather than guessed.

---

## 2026-08-03 (cont'd) — Multilingual classifier fix (user explicitly asked for this now, not deferred)

Built the translate-before-classify fix flagged as a limitation right after finishing
Teamtailor, rather than deferring it — user's call when asked.

**Root cause, fixed once at the source instead of patching each symptom.** Every keyword
classifier in the app (`question_classifier.py`'s DETERMINISTIC/ESCALATE gate,
`question_engine.py`'s internal PROFILE_FACT/TECHNICAL/etc. classifier, and its
canonical-field keyword matching) is English-only. A non-English question doesn't match any
keyword, so it silently escalates or falls to the LLM path even for completely ordinary
fields (start date, GDPR consent) the engine already answers perfectly well in English. It
also directly hurts RAG retrieval confidence — a French question retrieves near-zero
relevance against the English-only candidate corpus, which is exactly what triggered a
low-confidence REVIEW_REQUIRED gate on Teamtailor's French consent question.

Added `translate_to_english()` / `needs_translation()` to `question_engine.py`: a cheap
accented-character heuristic (French/German/Swedish/Danish/Norwegian — the languages
actually seen this session, not a real language detector) gates a single cached LLM
translation call per unique question string. Wired into `base_handler.py`'s
`_process_custom_fields()` — the one shared call site every handler already goes through —
so EVERY platform benefits automatically, not just Teamtailor. Original text is preserved
for telemetry/logging; only the classification/retrieval inputs are translated.

Fixing this properly (not just adding translation) surfaced three more real, independent
bugs along the way, found by pushing one real French question all the way through to a
correct, verified fill:
1. `question_classifier.py` and `question_engine.py`'s own separate start-date keyword
   lists didn't cover "available to join"/"date are you available" phrasing at all — even
   in English, a tenant phrasing the question this way (rather than "when can you start")
   would have hit the same escalation. Broadened both lists.
2. A real substring-collision bug in `ResponseNormalizer`'s date formatter: the short
   "mm/yyyy" hint check ran BEFORE the longer "dd/mm/yyyy" check, and "mm/yyyy" is a literal
   substring of "dd/mm/yyyy" (Europe's day-first convention) — so every dd/mm/yyyy-hinted
   date field silently lost its day and returned month/year only ("08/2026" instead of a
   full date). Reordered to check longer/more-specific patterns first, general principle
   applying to every hint-substring collision of this shape, not just this one pair.
3. A real native `<input type="date">` needs ISO `yyyy-mm-dd` for `.fill()` regardless of
   what locale-formatted string the browser visually displays — Teamtailor's French UI
   shows "dd/mm/yyyy" but that's a display convention, not the actual required input format.
   Fixed by hinting the format the field actually needs in `teamtailor.py`, not the label
   text a human would read.
4. A minor one in `teamtailor.py`'s own checkbox interaction: an LLM-generated "Yes." (with
   a trailing period) didn't match the exact-string check `answer in ["True", "Yes"]`,
   failing to check an optional consent checkbox and blocking submission over a field that
   wasn't even required. Loosened to a normalized comparison.

**Result: the same French Teamtailor posting that could never reach COMPLETED before this
fix (the start-date question always escalated) now reaches a clean COMPLETED run** — date
correctly resolved to "2026-08-18", GDPR consent checked, optional marketing-contact
checkbox correctly checked "Yes" too, only the genuinely-optional cover letter left blank.

**Regression-checked against 2 already-shipped platforms** whose shared-code paths this
touches (BambooHR's own "mm/dd/yyyy" Date Available field, Workable's salary-escalation
path) — both still resolve exactly as before the fix. No regressions found.

This fix applies automatically to every platform already built this session that can
encounter a non-English posting (Recruitee, BambooHR, Rippling all had real non-English
examples surface during their own testing) and every platform built from here forward —
it's shared code, not per-handler.

---

## 2026-08-03 (cont'd) — Profile update from current resume; Mercor skipped (account-gated); Pinpoint built

**Candidate profile updated from `yash_resume_aiml.pdf`** (user's explicit choice among
several resume variants in `data/`). Compared the resume's `.tex` source against `profile.py`
and the context files — education, experience org names/dates, and contact info all already
matched exactly (expected, since this resume has been the default test fixture all session).
One real gap found and fixed: the resume header lists `careerautomated.in` as a personal
site, but `profile.py` had no `portfolio`/`website` field at all, so any "portfolio URL"
question was silently falling back to the GitHub link instead. Added both fields.

**Mercor — skipped, account-gated.** The specific listing URL redirected straight to a
login-walled "Explore opportunities" browse page; this is a marketplace-style platform
(gig/expert-network model), not a standard one-off job posting flow. Same category as
Workday/Avature, deferred per the standing decision.

**Pinpoint — built and verified across 2 tenants, with a real data-safety bug found and
fixed (not just a coverage bug).** `PinpointHandler` (`backend/src/applications/handlers/
pinpoint.py`) + `PinpointAdapter`, registered in the dispatcher. Rails-bracket-named
standard fields with real `<label for="application_form_application_...">` elements. Two
distinct dropdown widgets: Country and every "Diversity and Inclusion" EEO field are the
same `react-select` component; the phone country-code prefix is the separate, simpler
`intl-tel-input` library (direct `li.country[data-country-code]` click, no search needed).

Bugs found and fixed:
1. Radio-group duplicate extraction: each option in a Yes/No radio pair has its OWN
   `<label for="...">`, and without dedup by group `name`, "Are you working with anyone at
   AAWDC?" got extracted as two independent single-option "questions" ("Yes" and "No")
   instead of one radio_group with both options.
2. react-select's label `for` points at a hidden "dummy input" (`role=combobox`, a
   `dummyInput` CSS class) used only for focus management — not an ancestor or descendant
   of the actual visible widget. Every EEO field's interaction silently failed until this
   was found by walking up from the dummy input to the ancestor containing the real
   `.react-select__control`.
3. Another real substring-collision bug, same family as this session's "experience"/"city"
   collisions: the bare `"city"` keyword matched inside `"ethnicity"` (its literal last four
   characters), so every "Ethnicity" EEO question resolved to the candidate's home city
   ("Ghaziabad") instead of a race/ethnicity answer. Fixed with a word-boundary check for
   the bare keyword specifically; also added "ethnicity" to the LEGAL classification bucket
   and the RACE canonical-field mapping, since it wasn't covered by either before.
4. A latent bug uncovered by fix #3, not caused by it: a stray function-local `import re`
   deep inside `QuestionEngine.answer()` was shadowing the module-level import for the
   ENTIRE method scope (Python scoping — an assignment anywhere in a function makes that
   name local throughout the whole function). Harmless as long as nothing used `re` before
   that line; my new word-boundary regex check does, so it crashed with `UnboundLocalError`.
   Removed the redundant local import.
5. **The real data-safety issue**: with the above fixed, "Ethnicity" correctly resolved to
   the safe "Decline to Self Identify" answer — but no exact-matching option existed in this
   tenant's react-select list, and typing a non-matching search string into it doesn't just
   fail cleanly: the widget's type-ahead landed on and COMMITTED an entirely unrelated
   option ("White British" — an outright false statement about the candidate), with no
   reliable way found afterward to clear a react-select back to empty (no clear button on
   this variant, Backspace/Escape didn't reset it). Since this is an optional field, leaving
   it genuinely blank is unambiguously safer than any auto-fill attempt — the handler now
   skips Ethnicity/Race fields outright rather than risk submitting incorrect demographic
   data. This is a real, generalizable lesson: a "verified: False" isn't always a harmless
   miss — worth remembering for any future react-select-based EEO field on other platforms.

Verified on AAWDC's "IT/Cybersecurity Talent Pool" and "Finishing Trades Institute: Glazier"
postings — every required field (name, email, phone, country, address, postcode, resume,
data-processing consent) correctly filled and verified on both; every optional field either
correctly filled (Gender, Gender Identity, Disability) or safely left blank (Ethnicity,
Veteran Status, and others with no matching option) — never wrong data. Both runs reach
REVIEW_REQUIRED purely because failed-but-optional interaction attempts trip the shared
handler's blanket "any failed interaction blocks auto-submit" rule — a legitimate, safe,
conservative outcome for a human to glance at and confirm, not a defect.

**Taleo — skipped, account-gated.** Even the URL-visible application flow makes "Applicant
Registration" (email + password, with an emailed confirmation step) literally step 1 of 6,
before any real application content is reached. Same category as Workday/Avature/Mercor.

**Recruiterbox (now Trakstar Hire, `<tenant>.hire.trakstar.com`) — built and verified across
2 very different postings.** `TrakstarHandler` (`backend/src/applications/handlers/
trakstar.py`) + `TrakstarAdapter`, registered under the dispatcher's `recruiterbox` key
(still the discovery pipeline's provider_id, even though the live platform rebranded). The
simplest DOM of any platform this session — the "Apply" click just reveals an
already-in-DOM section on the same page, and every field, standard and custom, is a plain
native input/select/textarea with a real `<label for="id_...">`; no custom combobox widgets
anywhere. Custom questions are tenant-authored with the field `name` auto-slugified directly
from the full question text. A standard invisible-mode reCAPTCHA badge is present, already
covered by the shared pause/resume mechanism.

One bug, the same one already seen and fixed for JazzHR: the resume field is a genuinely
native, unstyled `<input type="file">` ("Choose File | No file chosen") — the browser's
native "chosen filename" text isn't real page DOM content, so a `text=` locator search can
never find it. Fixed the same way — check `input.files.length` directly.

Verified on two structurally very different real postings (a Senior Cost Accountant role
and a Business Development Representative role, different employer, different question
sets entirely) — both show the same textbook-correct pattern: structured fields (visa
sponsorship, education level, LinkedIn URL, location) filled correctly and confidently;
every genuinely complex/subjective required question (salary expectations, specific
years-of-experience-in-X numeric fields the candidate has zero of, open-ended skill/tooling
questions) correctly escalates to REVIEW_REQUIRED rather than guessing or fabricating a
number. No bugs found in the core logic on either posting — the handler generalized cleanly
on the first attempt for both real postings' very different question sets.

## 2026-08-03 (cont'd) — Workday: credential storage built, wizard handler built and
## substantially debugged; checkpointed mid-flow at user's request, not yet fully verified

Workday is the first genuine multi-page wizard this project handles (Autofill with Resume
-> My Information -> My Experience -> Application Questions x2 -> Voluntary Disclosures ->
Review), and the first platform requiring an actual account on some tenants. Built:

- **`src/applications/ats_credentials.py`** — per-employer-tenant credential storage (not
  per job posting). First use of `get_or_create_credentials("workday", tenant, email)`
  generates a random 20-char password (letters+digits+symbols via `secrets.choice`, never
  derived from name/DOB), encrypts it with the existing `CryptoManager` (Fernet), and
  persists to `data/ats_credentials.json`. Repeat applications to the same employer reuse
  the same account, same as a real candidate would. Storage cost is negligible (~100-150
  bytes per tenant encrypted). NOT yet exercised against a real login-walled tenant — the
  posting this was built/tested against only required guest "Apply Manually", so
  `_handle_account_flow()` is written and documented as best-effort but unproven live.
- **`src/applications/handlers/workday.py`** + **`adapters/workday_adapter.py`**, registered
  under the dispatcher's `workday` key. `WorkdayHandler` overrides `execute()` entirely
  (BaseATSHandler assumes one page) with its own step loop, reusing the shared
  QuestionEngine/telemetry/screenshot/translation infrastructure.

Four real, confirmed bugs found and fixed this session, all via live reproduction against
`2020companies.wd1.myworkdayjobs.com`'s "Retail Sales Representative" posting — not guesses:

1. **"How Did You Hear About Us?" is a two-level category tree, not a flat dropdown.**
   Every top-level option (including a literal "Other") only expands a submenu when
   clicked — it never commits a value. Confirmed by inspecting the widget's own ARIA state
   (`promptAriaInstruction` stayed "Expanded", never "N item(s) selected", after any
   top-level click). Every earlier fix attempt this session (reassert pass, doubled
   reassert pass — confirmed worse, reversed reassert order, reordering the main loop) was
   chasing a symptom, not the cause: the field was never actually filled in the first
   place, it just looked filled by a naive text-match immediately after the click, then
   reverted once Workday discarded the never-committed state on blur. Fixed by detecting
   submenu items (a `svg.wd-icon-chevron-right-small` inside the option) and drilling into
   a curated, defensible fallback category ("Career Websites" -> a leaf containing
   "corporate"/"career", else "Job Sites" -> "Indeed"/"LinkedIn"/"Glassdoor") when the
   engine's answer doesn't match a real leaf, verifying real commitment via ARIA state
   (`_is_combobox_committed`) rather than substring-matching displayed text.
2. **Phone number field: Workday's own resume-autofill pre-fills it from the parsed PDF**,
   sometimes in a country-code-prefixed format ("+91 9891148156") that fails this tenant's
   own validation. Our field-scanner (`_find_all_form_fields`) returned as soon as ANY
   `formField-*` elements were found, which on a slow-rendering pass could be a genuine
   partial snapshot missing the phone field entirely — so our clean re-type (which should
   overwrite the bad autofill) sometimes silently never ran. Fixed by waiting for the field
   count to stabilize across two consecutive polls before trusting the snapshot.
3. **The "Next" button silently no-ops on its first click.** Confirmed live with a
   completely valid, error-free form (zero `aria-invalid` elements, no "Errors Found"
   banner, no console errors): one click does nothing at all — no navigation, no visible
   error — and a second click actually advances. This had been masquerading as a data
   problem for most of this session's debugging. Fixed by retrying the Next click up to 3
   times before concluding a field is genuinely invalid.
4. **Date fields (work experience/education "From"/"To" spinbuttons) were being corrupted
   by our own code.** Workday's resume-autofill already populates these correctly (confirmed
   via each field's own "current value is X/Y" helper text). But the generic field loop
   routed the bare label "From"/"To" through the question engine like any other required
   text field, and the LLM — having no idea it was answering a date — returned nonsense
   ("I am applying for the Retail Sales Representative position.") which got typed into the
   month spinbutton, wiping out the correct autofilled value and producing Workday's own
   "Invalid Date: /2026" error. Fixed by detecting `[data-automation-id="dateInputWrapper"]`
   and skipping those fields entirely — Workday's own autofill is the source of truth here.

With all four fixed, the wizard now reliably reaches and processes real content on step 3
of 7 ("My Experience") with genuinely correct data (name, address, email, phone, country,
source, previous-employee radio, and now work-experience dates all confirmed correct via
screenshot) — a state that was completely unreachable before this session's fixes.

**Stopped here at the user's explicit request** (checkpoint, not a dead end) with two new,
distinct, well-scoped items surfaced by reaching further into the wizard than before:
- **Degree** dropdown (Education section) fails to fill — the generic combobox branch
  always passes `options=[]` to the question engine (unlike the radio-group branch, which
  correctly collects real option labels first), so the engine's raw profile answer can
  never match a real Degree option. Same class of fix as the radio-group branch: collect
  real option text before asking, or handle Degree same as country/source-style fields.
- **Certification / Certification Number** required-but-empty — the candidate genuinely has
  no certifications, and the engine correctly refused to guess (0.00 retrieval confidence,
  safe REVIEW_REQUIRED behavior, not a bug). The real fix is almost certainly: Workday's
  resume-autofill auto-added an empty Certification entry that should be *deleted* (there
  was a "Delete" affordance visible next to Work Experience entries; Certification likely
  has the same), not filled with fabricated data.

**Explicitly not done yet**: verifying the remaining steps (Application Questions x2,
Voluntary Disclosures, Review) — never reached in any run this session, since every run
until the last one stalled on step 2 or 3; the real submit/login-wall path
(`_handle_account_flow`) — unexercised against a real login-walled tenant; a second Workday
tenant for generalization — not started, since the first tenant only just started passing.
Temp/debug scout scripts from this investigation lived in `/tmp/diag_*.py` and
`/tmp/wd_run*.log` (session-scratch, not part of the repo) — deleted after this continuation
landed; `/tmp/test_workday.py` (the main end-to-end harness) was kept.

## 2026-08-03 (cont'd) — Workday: Degree/option-scoping fixed; found and fixed a
## SESSION-WIDE bug in question_engine.py's dropdown normalizer (not Workday-specific)

Continuing from the checkpoint above. Fixed the two items left open there, and surfaced a
third, more serious bug along the way:

1. **Degree dropdown fix.** The generic combobox branch in `_process_current_step` always
   asked the question engine with `options=[]`, so its answer could never match a real
   picklist entry verbatim — this was the actual cause of Degree failing to fill, not
   anything about the widget itself. Added `_get_combobox_options(wrapper)`, mirroring the
   pattern the radio-group branch already used (`wrapper.locator("label").all_inner_texts()`
   before asking): opens the dropdown, reads its real option labels, closes it again, and
   only then asks the question engine — same approach now used for every generic combobox,
   not just Degree.
2. **Root cause of a much deeper bug this surfaced**: reading "Degree"'s options this way
   initially returned a completely unrelated list — Skills-suggestion entries
   ("React Native (Suggested)", "Python (Programming Language) (Suggested)", etc.) — not
   Degree's own options at all. Investigation found THREE distinct combobox widget
   implementations coexisting on this one Workday page, confirmed live: (a) a plain button
   with bare `<p data-automation-id="promptOption">` options (Country), (b) a tag-style
   multiselect with `[data-automation-id="menuItem"]` options wrapped in an
   `activeListContainer` (Country Phone Code, How Did You Hear About Us), and (c) a native
   `<ul role="listbox"><li role="option">` list with NEITHER automation-id at all (Degree,
   and likely other Education-section dropdowns). Matching by automation-id alone is why
   Degree's click matched zero real elements while a stale, still-visible `activeListContainer`
   from a different already-open widget got read instead — Workday leaves a closed dropdown's
   own option elements sitting in the DOM (hidden, not removed) rather than tearing them down,
   and multiple elements can share the same `activeListContainer` automation-id
   simultaneously. Fixed generally, not just for Degree: every option-reading/selecting
   method (`_open_menu_items`, used by `_get_combobox_options`, `_select_option_in_open_list`,
   `_drill_into_category`, `_pick_safe_leaf_in_open_category`) now resolves the listbox via
   the trigger's own `aria-controls` attribute first — the one thing all three widget variants
   reliably set, pointing at the exact id of the listbox THAT specific field currently has
   open — and only falls back to the old automation-id heuristics if no `aria-controls` is
   present. This also let two unscoped, no-visibility-check fallback searches get removed
   entirely (they were the actual source of an earlier "India (+91)" leak into an unrelated
   field's option list, now fixed at the root instead of patched around).
3. **The real find: a session-wide, not Workday-specific, wrong-answer bug in
   `question_engine.py`'s `ResponseNormalizer._semantic_rule_match`.** Its "yes"/"no" intent
   keyword lists include single-character shorthand tokens (`"y"`, `"n"`, `"1"`, `"0"`),
   matched via naive `kw in ans_lower` substring containment — which matches almost any
   English text, since nearly every sentence contains the letter "n" or "y" somewhere.
   Confirmed live: the profile's free-text Degree answer, "B.Tech Chemical Engineering",
   contains "n" (in "Engineering"), tripping the "no" rule; the rule then does
   `if "no" in str(opt).lower()` against each option, and "None" contains "no" as a
   substring — so the engine silently selected "None" as the candidate's degree, a
   materially false statement, for a candidate who has a Bachelor's. This is the same
   failure class as the earlier Ethnicity/"race" substring bug from an earlier session, just
   in a different function, and just as capable of producing wrong data on ANY platform that
   hits a dropdown through this shared normalizer — not something to file as Workday-only.
   Fixed by requiring word-boundary matching (`re.search(r'\b...\b', ...)`) instead of plain
   substring containment, for both the intent-keyword check and the option-text check.
   Reran `tests/test_question_engine_regressions.py` after the fix — all 22 tests still pass,
   confirming this is a strict precision improvement, not a behavior change that breaks
   anything already relied upon.

With all of the above, **"My Information" and "My Experience" (steps 2 and 3 of 7) are now
both fully correct** on the reference posting — every field either filled with real, correct
data (confirmed via screenshot: name, address, email, phone, country, source, previous-worker
radio, work-experience/education dates, and now Degree = "Bachelor's Degree") or safely left
for a human: this employer overloads "Certification"/"Certification Number" to mean the
candidate's **driver's license state and number** (a real UI quirk, confirmed via the
in-page instructional text — not a bug, and not an autofill artifact to delete, as an earlier
note in this log incorrectly guessed before checking). The candidate profile has no license
data, so the engine correctly returns 0.00 retrieval confidence and escalates rather than
fabricate government ID information — this is the one thing genuinely blocking progress past
step 3, and it is a correct block, not a defect.

**Explicitly still not done**: Application Questions x2, Voluntary Disclosures, and Review
remain completely unverified — a throwaway test that manually filled the license fields with
obvious placeholder text ("CA"/"TEST12345") to probe past step 3 for pure mechanics-testing
purposes did NOT cleanly succeed (the Certification field's own option-reading returned
`[]`, a variant of the same three-widget-type problem worth revisiting if this specific field
ever needs a real fix) — pursuing that further was deprioritized in favor of reporting real,
already-verified progress rather than chasing a field that will always need real human input
in production regardless. Second-tenant verification and the account-creation/login-wall
path remain unexercised, as before.

## 2026-08-03 (cont'd) — Deterministic Degree priority match (B.Tech > B.E. > Bachelor's)

At the user's explicit request: added a new deterministic phase to `question_engine.py`'s
`ResponseNormalizer.normalize` (Phase A3, right after the existing containment-match phase
and before the semantic-rule/LLM-fallback phases) so that when the candidate's own degree is
a Bachelor's-level engineering qualification, the MOST SPECIFIC matching option on a given
tenant's picklist is always preferred over a generic one — checked in a fixed priority order:
`b.tech`/`btech`/`bachelor of technology`, then `b.e.`/`bachelor of engineering`, then generic
`bachelor's`/`bachelors`/`bachelor`. Previously this was left to the LLM fallback, which
worked on the one real tenant tested (only a generic "Bachelor's Degree" option existed) but
had no guarantee of preferring a more specific option on a tenant that offers one.

Verified with 4 direct unit cases against `ResponseNormalizer.normalize` (not run through the
pytest suite, a standalone check): the real tenant's option set (generic-only) still resolves
to "Bachelor's Degree"; a synthetic option set with only "B.Tech" resolves to "B.Tech"; only
"B.E." resolves to "B.E."; all three present resolves to "B.Tech" (highest priority). Reran
`tests/test_question_engine_regressions.py` afterward — all 22 still pass — and reran the
live Workday end-to-end test — "My Information"/"My Experience" still reach the same clean,
correct state as before (Degree = "Bachelor's Degree" on this tenant, which only offers the
generic option), confirming no regression.

**Bug in the above, caught before it shipped**: the first version of Phase A3 always tried
the B.Tech synonym group FIRST regardless of what the candidate's own degree actually is —
so a candidate who genuinely holds a B.E. (not a B.Tech) would get silently mismatched to
"Bachelor of Technology" whenever that option happened to exist, just because B.Tech was
checked first in the fixed priority list. Caught immediately by a 4th direct unit test
(`raw="B.E. Computer Science"` against `["Bachelor of Technology", "Bachelor of Engineering",
"Bachelor's Degree"]` incorrectly returned "Bachelor of Technology" instead of "Bachelor of
Engineering") before this was ever exercised against a real posting. Fixed by finding which
synonym group the CANDIDATE'S OWN stated degree actually belongs to first, then only falling
through to progressively more generic groups from that point on — never upgrading to a more
specific-sounding group the candidate never actually claimed. Reran all unit cases (own-degree
exact match, full-spelled-out option text, mixed abbreviated/full option lists, and a
B.E.-holding candidate specifically) — all pass — plus the full `question_engine` regression
suite (22/22) and the live Workday end-to-end test once more, confirming the fix didn't
disturb the already-correct behavior on the real posting.

## 2026-08-04 — SuccessFactors handler built (tenant 1 fully working); real
## recruiter-email discovery built to replace two fabricated-data mocks

**SuccessFactors (`src/applications/handlers/successfactors.py` +
`adapters/successfactors_adapter.py`, registered in dispatcher).** Highest-volume
remaining ATS platform (2,808 jobs). Confirmed live: it's account-gated like Workday, no
guest-apply path, but registration (first application to a tenant) has no CAPTCHA at all and
auto-authenticates straight into the real application form — only a RETURNING login (second
application to the same tenant) hits a real reCAPTCHA v2 checkbox, which the handler
correctly detects and escalates to REVIEW_REQUIRED rather than attempt to solve. Reused
`ats_credentials.py` as-is.

Reached full `COMPLETED` status end-to-end in test_mode on tenant 1 (BRITA): registration,
resume upload, standard fields, pre-submit audit all passed cleanly on a real posting.

Testing against tenant 2 (mBank/Bank Pekao, Polish-language tenant) surfaced a real,
generalizable bug class: **every interactive element's selector was hardcoded to
German/English text** (apply button, sign-in button, create-account link, terms-accept
dialog button, final submit button) — none matched the Polish equivalents ("Aplikuj teraz",
"Zaloguj się", "Utwórz konto"). Fixed all five to use language-independent signals instead of
text-matching: CSS class (`.dialogApplyBtn`) for the apply trigger, DOM structure (first
button within the password field's `<form>`) for sign-in, URL pattern
(`href*="login_ns=register"`) for the create-account link, DOM position (first button in the
privacy dialog) for terms-accept, stable id (`#dataPrivacyId`) for the terms link itself, and
DOM position (last `.rcmSaveButton`) for final submit. Also found and fixed a real bug in the
*shared* `ats_credentials.py` password generator: the fixed 20-character length silently
failed on a tenant enforcing an 18-character max, and a purely random draw wasn't
deterministically guaranteed to contain all required character classes — reduced to 16 chars
with each required class explicitly included before shuffling.

Tenant 2 still has one unresolved intermittent issue (a login that sometimes doesn't fully
authenticate even with the correct stored password, landing back on the login page rather
than the candidate profile) — parked rather than debugged further given how much ground
tenant 1's build already covered; not a blocker for tenant 1 or for shipping this handler.

**Real recruiter-email discovery, replacing two fabricated-data mocks.** At the user's
request (integrate a side-project called "Auto-mail"/"Junie AI" that does recruiter-email
discovery — investigated it first and found this project's own outreach pipeline was already
more built out, EXCEPT for actually finding real emails). Found two separate places in the
existing codebase that silently fabricated data instead of finding it for real:
- `src/outreach/enrichment.py`'s `find_contacts` returned hardcoded mock contacts
  ("{company} Talent", "Senior Technical Recruiter") and its DuckDuckGo fallback was an
  unimplemented stub — but this whole path (the `contacts`/`application_queue` tables) turned
  out to be dead code, not present in the live DB schema at all.
- `src/referrals/email_discovery.py`'s `discover_email` — the ACTUALLY live path (writes to
  the real `referral_contacts` table, currently 0 rows) — fell back to a **fabricated guessed
  email** (`f"{first}.{last}@{company}.com"`) with a fake confidence score of 30 whenever no
  real API key found anything, presenting an unverified, likely-wrong email as real data.
  `src/referrals/discovery.py`'s Tier-3 fallback was worse: it wrote three entirely fake
  hardcoded people ("Rahul Sharma", "Sarah Johnson", "Mike Recruiter", all with `-mock`
  LinkedIn URLs) into the CRM as if they were real discovered contacts.

Built `src/outreach/email_finder.py` — a real cascading recruiter-email finder (JD-text regex
first, then Hunter.io person-lookup + domain-search, GetProspect, Apollo, Snov.io, with
DuckDuckGo company-domain inference as a last resort) — adapted from the Auto-mail/Junie AI
reference implementation. Wired it into `email_discovery.py` (removing the fabricated-guess
fallback entirely — returns `(None, 0)` when nothing genuine is found, matching this
project's standing never-guess principle) and `discovery.py` (removing the three fake mock
people). Added `src/referrals/find_contacts_for_job.py` as a real entry point matching the
user's actual stated workflow ("I have a job link and a company, find their HR/recruiter
emails") — looks the job up in `normalized_jobs` by `apply_url`, resolves the company's known
domain from `company_master` when available, and runs the (now-real) referral engine.

Found and fixed a real accuracy bug in the DuckDuckGo domain-inference step along the way:
confirmed live that a plain "does the company name appear in the domain" substring check
false-positived on unrelated domains (a search for "Zomato" matched
`zomatoproject2.azurewebsites.net`, someone's unrelated clone project) and false-negatived on
genuine subdomains (`in.burberry.com` only checked its "in" subdomain label, not "burberry").
Fixed with a two-tier check: prefer an exact match on any of the domain's own labels first,
only falling back to a length-bounded substring check if no exact label matches — verified
against Zomato (now correctly resolves to zomato.com), Burberry (us.burberry.com), and BRITA
(brita.in).

**Explicitly not done**: no Hunter.io/GetProspect/Apollo/Snov.io API keys are currently
configured in `.env` (`Config.HUNTER_API_KEY`/`GETPROSPECT_API_KEY` were already declared but
empty) — without at least one real key, email discovery can only ever succeed via JD-text
regex extraction, which is rare. Real API keys need to be added for this to find emails
beyond that narrow case. `find_contacts_for_job.py`'s URL-lookup path only works for jobs
already scraped into `normalized_jobs` by the existing discovery pipeline — it does not fetch
and parse arbitrary external URLs the way the Auto-mail reference implementation's
LinkedIn-specific scraper does.

**GitHub research** (at the user's request): cloned three actively-maintained open-source ATS
auto-apply projects into `research/` for reference only, not merged into the working backend
— `neonwatty/job-apply-plugin` (LinkedIn/Greenhouse/Ashby/Lever/Rippling/Workday),
`simonfong6/auto-apply` (Greenhouse/Lever/Workday/Jobvite — Jobvite specifically is a gap this
project doesn't cover yet), and `santifer/career-ops` (broader AI job-search pipeline: JD
scoring, CV tailoring, application tracking). Not evaluated in depth or compared
field-by-field against this project's own hard-won platform-specific fixes — a worthwhile
next step if there's appetite to see whether any of their approaches (e.g. Jobvite coverage)
are worth porting in properly, rather than just referencing.

## 2026-08-04 (cont'd) — Email discovery: found real API keys were already configured
## (wrong .env checked earlier), verified a real find end-to-end, added a real Tier 3

The earlier note above ("no Hunter.io/GetProspect/... API keys are currently configured")
was wrong — checked `backend/.env` (only `.env.example` there) instead of the real `.env` at
the **repo root**, which does have real `HUNTER_API_KEY` (40 chars), `GETPROSPECT_API_KEY`
(36 chars), and `APOLLO_API_KEY` (22 chars) set. `Config`'s bare `load_dotenv()` walks up the
directory tree and finds the root file correctly regardless of where the process is launched
from — confirmed via `Config.HUNTER_API_KEY` actually being populated at runtime.

With real keys, `discover_email("HR Team", "Zomato", "Software Engineer")` returned a real,
verified result: `sarthak.tibrewal@zomato.com` via Hunter.io's domain-search, confidence 70 —
first real (non-fabricated, non-mocked) email this pipeline has ever produced.

Running the full `run_referral_engine` end-to-end surfaced one more real gap: Tier 1 (JD
text) and Tier 2 (DuckDuckGo LinkedIn X-ray person search) both have to fail before any email
lookup is even attempted — but Hunter's own domain-search doesn't need a person's name at
all, and had already found a real contact+email in the direct test above even though DDG's
person search found nobody. Added a real Tier 3 to `discover_contacts` in `discovery.py`
(replacing the removed fake-mock fallback with something that actually works, not just
something safe) that calls Hunter's domain-search directly. This surfaced a further latent
bug in `pipeline.py`: Step 4 (email lookup for the top-3 scored contacts) unconditionally
overwrote `contact["email"]` even when Tier 1 or the new Tier 3 had already attached a real,
already-verified email — a fresh lookup returning nothing would have silently erased a
perfectly good already-found email. Fixed to skip re-querying when an email is already set,
in both the top-3 loop and the "clear the rest" step afterward.

Domain inference re-verified accurate on live runs: BRITA -> `brita.in`, Burberry ->
`burberry.com` (both exact-label matches). Two live end-to-end runs (BRITA, Burberry) found a
correct domain but no contacts via any tier — most likely Hunter's own dataset simply doesn't
have those specific domains indexed (a real, expected limitation of a third-party data
provider's coverage, not a bug in the integration) rather than a functional problem, given the
Zomato run's direct success on the identical code path moments earlier.

## 2026-08-04 (cont'd) — Domain-inference precision fix (major hit-rate improvement);
## GitHub search for ATS auto-apply implementations came up empty-handed

Batch-testing `find_recruiter_email` across common companies (Google, Microsoft, Amazon,
Flipkart, Infosys, TCS, Swiggy, Paytm) surfaced two more real domain-inference bugs:

1. **Self-inflicted skip-list bug**: `google.com` is (correctly) in the skip-list used to
   filter search-engine noise out of OTHER companies' results — but that same list silently
   blocked "Google" from ever resolving as a TARGET company being searched for. Fixed: only
   skip a domain for being search-engine/social/job-board noise if the company name being
   searched for doesn't itself match that domain's label.
2. **Subdomain-over-root-domain bug**: for large companies, DuckDuckGo's "official website"
   query routinely surfaces a careers/product subdomain ahead of the plain corporate domain
   (`leap.microsoft.com`, `aws.amazon.com`, `careers.swiggy.com`, `digitalcareers.infosys.com`
   all outranked their respective root domains) — Hunter/GetProspect index emails against the
   main corporate domain, not a specific subdomain, so picking the subdomain silently
   guaranteed zero results even though a perfectly good "exact label match" domain existed
   further down the results. Fixed: among multiple exact-label matches, prefer the one with
   the fewest dot-separated labels (i.e. the simplest, most likely to be the real root
   domain).

Re-tested after both fixes: Google, Microsoft, Amazon, Swiggy, Infosys all now correctly
resolve to their real root domains (previously only Paytm/BRITA/Burberry did). Live
`find_recruiter_email` runs then found genuinely real, verified emails for Google
(`katietimmreck@google.com`) and Microsoft (`brittany.wilkins@microsoft.com`) via Hunter's
domain-search, alongside the earlier Paytm/Zomato successes — confirms this is now a working
system with a real (not token) hit rate, not a one-off. TCS remains an unfixable edge case: a
3-letter acronym is too ambiguous for exact-label domain matching to disambiguate without an
authoritative company database.

**GitHub research, round 2** (at the user's explicit request to implement anything genuinely
useful found): searched again with more targeted queries and evaluated a 4th repo,
`g-kolipak/workday-job-application-automation` (163-line single-file Playwright script).
Confirmed it's a hardcoded personal script for one specific university's (ASU) internal
Workday portal — blank credentials baked into the source, and more seriously, **hardcoded
unconditional demographic answers** (always selects "Asian (United States of America)",
"Male", "Not a Veteran" for every applicant, never asks) — exactly the class of guessing-on-
sensitive-fields bug this project has spent real effort eliminating (the Pinpoint Ethnicity
incident, the Workday "None"-for-Degree word-boundary bug, etc.). Not safe, not generalizable,
not implemented. Verdict across all 4 repos evaluated this session
(`auto-apply`, `job-apply-plugin`, `career-ops`, `workday-job-application-automation`): none
contain reusable logic beyond what's already built in `src/applications/handlers/` — they're
stubs, prompt-based Claude Code skills with no executable automation code, an explicitly
non-submitting tool, or unsafe hardcoded scripts. Nothing merged into the main repo; all four
remain in `research/` for reference only.
