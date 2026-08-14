# Chrome Web Store listing — CareerAutomated Autofill

Everything below is ready to paste into the Developer Dashboard
(chrome.google.com/webstore/devconsole) when you submit. I can't submit
this myself — it needs your Google account, the one-time $5 registration
fee, and a live browser session — but this covers everything the listing
form will ask for.

## Package to upload

`extension/dist/careerautomated-autofill-0.2.0.zip` (built by
`python3 build_store_package.py` — already run, zip is in place). This is
a stripped copy of the dev manifest with the two localhost dev permissions
removed; it does **not** replace `extension/manifest.json`, which you keep
using for "Load unpacked" during development.

If you change any extension file, rerun `python3 build_store_package.py`
before re-uploading — it doesn't auto-run on save.

## Store listing fields

**Name**: CareerAutomated Autofill

**Summary** (132 char max):
> Autofills job application forms on Greenhouse, Lever, and Ashby using your CareerAutomated profile. You always review and submit.

**Category**: Productivity

**Language**: English (or add Hindi if you want — not required)

**Detailed description**:
> CareerAutomated Autofill fills in job application forms on Greenhouse,
> Lever, and Ashby using the profile you've already built at
> careerautomated.in — name, resume, experience, and screening-question
> answers.
>
> Start an autofill from your CareerAutomated dashboard. The extension
> opens the application in the background and fills it in without
> interrupting what you're doing. When it's ready, click to bring it to
> the front, review everything, solve any CAPTCHA yourself, and submit —
> the extension never clicks submit for you.
>
> Requires a free CareerAutomated account at careerautomated.in.
>
> Supported sites: Greenhouse, Lever, Ashby (more coming).

**Privacy policy URL**:
`https://careerautomated.in/legal#extension-privacy`
(live once the frontend redeploys with this session's changes)

## Permission justifications

The dashboard's "Privacy practices" tab asks you to justify each requested
permission in plain language. Use these:

- **storage**: "Stores the in-progress autofill session state locally so
  the extension knows which job application window is being filled."
- **windows**: "Opens the job application in a background browser window
  during autofill, and brings it to the foreground when the user asks to
  review it."
- **host_permissions (job-boards.greenhouse.io, boards.greenhouse.io,
  jobs.lever.co, jobs.ashbyhq.com)**: "The extension only reads and fills
  form fields on job application pages on these specific ATS platforms —
  it has no access to any other site."
- **host_permissions (careerautomated.in, api.careerautomated.in)**:
  "Communicates with the user's own CareerAutomated account to fetch
  profile data used to answer form fields."
- **externally_connectable (careerautomated.in)**: "Lets the
  CareerAutomated dashboard (a page the user is already on) start and
  check the status of a background autofill directly, instead of routing
  through a separate messaging relay."

## Screenshots

Chrome Web Store requires at least one screenshot, 1280×800 or 640×400.
None are captured yet — recommended shots once you have a moment:
1. The Jobs page with the "Open & Autofill" button visible.
2. The `BackgroundApplyButton`'s "Ready" state after a fill completes.
3. A filled Greenhouse/Lever form, showing real fields populated.

I didn't fabricate these since they need a real logged-in session and a
real job posting to be honest screenshots rather than staged ones.

## Before you submit

- [ ] Pay the one-time $5 developer registration fee if you haven't already
- [ ] Take at least 1 real screenshot (see above)
- [ ] Confirm `https://careerautomated.in/legal#extension-privacy` is live
      (deployed as part of tonight's work — verify after your next visit)
- [ ] Upload `dist/careerautomated-autofill-0.2.0.zip`
- [ ] Expect review to take anywhere from hours to ~2 weeks — this
      extension's host_permissions on external job-board domains put it on
      the more-scrutiny side, not the fast lane
