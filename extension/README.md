# CareerAutomated Autofill (browser extension, v0.1)

Runs the same answer-generation engine as the server-side auto-apply system
(`QuestionEngine`, same profile/RAG data), but inside your own real Chrome
instead of a headless VM. That's the whole point: your real browser, your
real IP, your real session — so when a CAPTCHA shows up, it's just yours to
solve normally, no automation-vs-CAPTCHA arms race, no remote-browser
handoff infra needed.

## What it does today (v1 scope)

- Adds an "Autofill (CareerAutomated)" button to Greenhouse job application
  pages (`job-boards.greenhouse.io`, `boards.greenhouse.io`).
- Fills text inputs, textareas, and native `<select>` dropdowns using
  `POST /api/v1/applications/autofill`.
- Attaches the right resume variant via `GET /api/v1/applications/resume-for-job`.
- **Never auto-submits, never touches a CAPTCHA widget.** You review every
  answer and click Submit yourself.

## What it doesn't do yet

- Radio buttons / checkbox groups (label-matching them reliably needs more
  work — left for you to fill by hand for now, same as before this existed).
- Only Greenhouse. Lever/Ashby content scripts would follow the same pattern
  (see `content-greenhouse.js`) once this one's proven out.
- No cancel/undo — it's a one-shot fill per page load.

## Loading it locally

1. `chrome://extensions` → enable "Developer mode" → "Load unpacked" → select
   this `extension/` folder.
2. Log into `careerautomated.in` in a normal tab — `bridge-auth.js` picks up
   your session token automatically and hands it to the extension. Check the
   extension popup for "Connected ✓".
3. Open any Greenhouse job application page. Click the button in the
   bottom-right corner.

## Auth

`bridge-auth.js` scans `localStorage` on careerautomated.in for the Supabase
session key (`sb-*-auth-token`) and forwards `access_token` to the
extension's background worker via `chrome.storage.local` — no separate login
inside the extension. If that ever breaks (e.g. Supabase changes its storage
key shape), the popup has a manual token-paste fallback.
