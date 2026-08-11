"""
Workday is structurally different from every other platform this project
handles: a genuine multi-page wizard (Autofill with Resume -> My
Information -> My Experience -> Application Questions -> Voluntary
Disclosures -> Review), not one scrollable form. BaseATSHandler's
execute() assumes a single page, so WorkdayHandler overrides execute()
entirely with its own step loop instead, while still reusing the shared
QuestionEngine / telemetry / screenshot / translation infrastructure so
custom questions get the exact same classification, RAG, and safety
behavior every other handler already has.

Every field on every step shares one consistent DOM convention
(data-automation-id="formField-<key>" wrapping either a plain <input>, an
accessible combobox button, or a radio <fieldset>), discovered by live
inspection against a real posting — see SESSION_LOG.md for the specifics.
Workday's own async rendering is genuinely flaky (elements intermittently
absent from a locator query moments after being visibly present), so
every lookup here goes through a retrying helper rather than a single
locator call.
"""
from src.system.logger import setup_logger
logger = setup_logger('workday')
import os
import re
from urllib.parse import urlparse

from src.system.state import WorkflowState
from src.applications.handlers.base_handler import BaseATSHandler
from src.applications.question_engine import translate_to_english
from src.applications.ats_credentials import get_or_create_credentials


class WorkdayHandler(BaseATSHandler):
    ATS_NAME = "WORKDAY"

    _MAX_STEPS = 10

    # ------------------------------------------------------------------
    # Robust element lookup — Workday's React app genuinely does not have
    # every data-automation-id element reliably queryable via a single
    # locator call the instant it's visually present (confirmed live,
    # repeatedly, against a real posting — not a guess at a hypothetical
    # race condition).
    # ------------------------------------------------------------------

    def _find(self, aid: str, retries: int = 8, wait_ms: int = 800):
        for _ in range(retries):
            els = self.page.locator(f'[data-automation-id="{aid}"]').all()
            if els:
                return els[0]
            self.page.wait_for_timeout(wait_ms)
        return None

    def _active_step_name(self) -> str:
        try:
            el = self.page.locator('[data-automation-id="progressBarActiveStep"]').first
            if el.count() > 0:
                return el.inner_text().strip()
        except Exception:
            pass
        return ""

    def _find_all_form_fields(self, retries: int = 10, wait_ms: int = 600):
        # Returning as soon as ANY fields are found (the original approach)
        # is not enough — Workday's React app mounts formFields
        # incrementally, so an early non-empty snapshot can be a genuine
        # partial render, silently missing fields (confirmed live:
        # phoneNumber intermittently absent from this snapshot, so the
        # standard-field branch never re-typed over Workday's own
        # resume-autofill value for it, which was left in a format
        # ("+91 9891148156", country-code-prefixed) that fails this
        # tenant's own phone validation). Wait for the count to stop
        # growing across two consecutive polls before trusting it.
        last_count = -1
        stable_count = 0
        els = []
        for _ in range(retries):
            els = self.page.locator('[data-automation-id^="formField-"]').all()
            if len(els) > 0 and len(els) == last_count:
                stable_count += 1
                if stable_count >= 2:
                    return els
            else:
                stable_count = 0
            last_count = len(els)
            self.page.wait_for_timeout(wait_ms)
        return els

    # ------------------------------------------------------------------
    # Abstract methods required by BaseATSHandler — implemented as real,
    # narrowly-scoped helpers called from this handler's own execute()
    # override below, not left as stubs.
    # ------------------------------------------------------------------

    def _enter_application_flow(self):
        logger.info("WorkdayHandler: Clicking Apply...")
        self.page.wait_for_timeout(2000)
        apply_btn = self.page.get_by_role("button", name="Apply", exact=True).first
        if apply_btn.count() == 0:
            apply_btn = self.page.get_by_role("link", name="Apply", exact=True).first
        apply_btn.click(timeout=8000)
        self.page.wait_for_timeout(1500)

        # Some tenants show a hard Sign In wall (email + password) before
        # the apply flow is reachable at all, rather than the guest-style
        # "Autofill with Resume" modal confirmed on the tenant this
        # handler was built against. Detect and use stored/generated
        # credentials in that case; otherwise proceed as a guest.
        signin_wall = self.page.get_by_text("Sign In", exact=False).first
        autofill_option = self.page.get_by_text("Autofill with Resume", exact=False).first
        manual_option = self.page.get_by_text("Apply Manually", exact=False).first
        for _ in range(6):
            if autofill_option.count() > 0 or manual_option.count() > 0:
                break
            self.page.wait_for_timeout(500)

        if autofill_option.count() > 0:
            autofill_option.click(timeout=8000)
        elif manual_option.count() > 0:
            manual_option.click(timeout=8000)
        else:
            logger.info("WorkdayHandler: Neither Autofill nor Apply Manually option found — attempting account sign-in/creation path.")
            self._handle_account_flow()

        self.page.wait_for_timeout(2000)

    def _handle_account_flow(self):
        """Reached only when a tenant requires an account before the
        application wizard itself — creates (or reuses) tenant-scoped
        credentials via ats_credentials.py rather than a guessable
        password pattern. Not exercised against a real login-walled
        tenant yet (the posting this was built against didn't require
        one) — this is the documented, best-effort path for when one is
        found, not something to treat as fully proven."""
        tenant = urlparse(self.page.url).hostname or "unknown"
        email = self.profile.get_field("email")
        creds = get_or_create_credentials("workday", tenant, email)

        email_input = self.page.locator('input[type="email"], input[name*="email" i]').first
        password_input = self.page.locator('input[type="password"]').first
        if email_input.count() == 0 or password_input.count() == 0:
            logger.info("WorkdayHandler: Account flow fields not found — cannot proceed automatically.")
            return

        email_input.fill(creds["email"])
        password_input.fill(creds["password"])
        confirm_input = self.page.locator('input[type="password"]').nth(1)
        if confirm_input.count() > 0:
            confirm_input.fill(creds["password"])
        submit_btn = self.page.get_by_role("button", name=re.compile("create account|sign in|continue", re.I)).first
        if submit_btn.count() > 0:
            submit_btn.click(timeout=8000)
            self.page.wait_for_timeout(2000)

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _fill_and_verify_standard_fields(self) -> bool:
        # Not used — WorkdayHandler's own execute() override processes
        # every step's fields (standard and custom together) uniformly,
        # since Workday doesn't separate them the way a single-page form
        # does. Present only to satisfy BaseATSHandler's abstract method.
        return True

    def _upload_resume(self) -> bool:
        # Handled inline in execute()'s "Autofill with Resume" step.
        return True

    def _extract_questions(self) -> list[dict]:
        return []

    def _get_submit_button_locator(self):
        return self._find("pageFooterSubmitButton") or self._find("pageFooterNextButton")

    # ------------------------------------------------------------------
    # Field-level helpers
    # ------------------------------------------------------------------

    _STANDARD_FIELD_MAP = {
        "formField-legalName--firstName": lambda self: self.profile.get_field("first_name"),
        "formField-legalName--lastName": lambda self: self.profile.get_field("last_name"),
        "formField-addressLine1": lambda self: self.profile.get_field("address"),
        "formField-city": lambda self: self.profile.get_field("city"),
        "formField-postalCode": lambda self: self.profile.get_field("postal_code"),
        "formField-emailAddress": lambda self: self.profile.get_field("email"),
        "formField-phoneNumber": lambda self: self.profile.get_field("phone"),
    }

    def _label_for(self, wrapper) -> str:
        try:
            label = wrapper.locator("label").first
            if label.count() > 0:
                return label.inner_text().split("\n")[0].replace("*", "").strip()
        except Exception:
            pass
        return ""

    # Curated, defensible leaf choices for the hierarchical "How Did You
    # Hear About Us?"-style category trees confirmed live on a real
    # tenant: EVERY top-level item there (including "Other") is a
    # category with its own submenu, not a selectable value — clicking
    # one just expands it. "Other"'s only leaf turned out to be "Migrated
    # from Prior ATS" (nonsensical for a fresh applicant), so a blind
    # "Other" fallback is actively wrong here, not just unhelpful. These
    # two categories are close to universal across employers and have
    # leaves that are true, defensible statements for how an automated
    # discovery-and-apply agent actually finds postings.
    _SOURCE_CATEGORY_FALLBACKS = [
        ("Career Websites", ["corporate", "career"]),
        ("Job Sites", ["indeed", "linkedin", "glassdoor"]),
    ]

    def _open_menu_items(self, wrapper, retries: int = 6, wait_ms: int = 300) -> list:
        """Returns the option elements belonging to the listbox the given
        wrapper's own trigger currently controls. Workday uses at least
        THREE different combobox widget implementations on this one page
        — a plain button with bare `<p data-automation-id="promptOption">`
        options (Country), a tag-style multiselect with
        `[data-automation-id="menuItem"]` options (Country Phone Code,
        How Did You Hear About Us), and a native
        `<ul role="listbox"><li role="option">` list with NEITHER
        automation-id (Degree, and likely other Education/dropdown
        fields) — confirmed live. Matching by automation-id alone means
        Degree's own click matched zero real elements while a stale
        globally-visible container from a DIFFERENT already-open widget
        (a Skills suggestion panel) got read instead. The one thing every
        variant reliably sets is `aria-controls` on the trigger itself,
        pointing at the exact listbox id currently open for THAT specific
        field — so resolve the listbox by id first, and only fall back to
        the automation-id heuristics if no aria-controls is present.
        Retries because the attribute can take a moment to appear after
        the click — and also because the trigger click itself is
        sometimes a silent no-op (confirmed live, same failure mode
        already fixed for the wizard's Next button): the Certification
        field's trigger showed IDENTICAL attributes before and after a
        click with no exception raised — the dropdown genuinely never
        opened, so no amount of waiting alone would ever find items.
        Re-clicking the trigger partway through the retry budget recovers
        from this without every caller needing its own retry logic."""
        trigger = wrapper.locator("button, input").first
        for i in range(retries):
            controls_id = trigger.get_attribute("aria-controls")
            if controls_id:
                listbox = self.page.locator(f'#{controls_id}')
                if listbox.count() > 0:
                    items = listbox.first.locator(
                        '[data-automation-id="menuItem"], [data-automation-id="promptOption"], li[role="option"]'
                    ).all()
                    items = [i for i in items if (i.get_attribute("aria-disabled") or "").lower() != "true"]
                    if items:
                        return items
            containers = self.page.locator('[data-automation-id="activeListContainer"]').all()
            visible = [c for c in containers if c.is_visible()]
            if visible:
                items = visible[-1].locator('[data-automation-id="menuItem"]').all()
                if items:
                    return items
            if i > 0 and i % 2 == 0:
                try:
                    trigger.click(timeout=3000, force=True)
                except Exception:
                    pass
            self.page.wait_for_timeout(wait_ms)
        return []

    def _option_has_submenu(self, option) -> bool:
        try:
            return option.locator("svg.wd-icon-chevron-right-small").count() > 0
        except Exception:
            return False

    def _is_combobox_committed(self, wrapper) -> bool:
        try:
            aria = wrapper.locator('[data-automation-id="promptAriaInstruction"]').inner_text()
            if "item selected" in aria.lower() and "0 items selected" not in aria.lower():
                return True
        except Exception:
            pass
        # Non-multiselect combobox (Country): the trigger button's own
        # text becomes the selected value, no promptAriaInstruction exists.
        try:
            btn = wrapper.locator("button").first
            if btn.count() > 0:
                text = btn.inner_text().strip()
                return bool(text) and text.lower() != "select one"
        except Exception:
            pass
        return False

    def _get_combobox_options(self, wrapper) -> list:
        """Opens a combobox just to read its real option labels, then
        closes it again without selecting anything. Used so generic
        dropdowns (e.g. "Degree") can be asked about with their REAL
        options — the same pattern the radio-group branch already uses
        (`wrapper.locator("label").all_inner_texts()`) — instead of the
        engine guessing at a raw profile value that may not match any of
        this tenant's exact option wording. Without this, "Degree" always
        failed to fill: the engine's answer (a free-text degree name from
        the profile) essentially never matches Workday's own exact
        picklist entry verbatim."""
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)
            wrapper.scroll_into_view_if_needed()
            trigger = wrapper.locator("button, input").first
            trigger.click(timeout=5000, force=True)
            self.page.wait_for_timeout(500)
            options = self._open_menu_items(wrapper)
            texts = [t.strip() for t in (
                (o.inner_text() for o in options if not self._option_has_submenu(o))
            ) if t.strip()]
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)
            return texts
        except Exception as e:
            logger.info(f"WorkdayHandler: Reading combobox options failed: {e}")
            return []

    def _select_option_in_open_list(self, wrapper, answer: str) -> bool:
        """Selects a LEAF option (no submenu chevron) from whatever
        listbox is currently open. Returns False without side effects if
        only category (submenu) items match — clicking a category doesn't
        commit a value, it only expands it, and treating that click as a
        successful fill was the root cause of an earlier bug: the field
        looked filled by a naive text-match immediately afterward, then
        silently reverted to empty once Workday itself discarded the
        never-actually-committed state on blur."""
        options = self._open_menu_items(wrapper)
        for opt in options:
            try:
                text = opt.inner_text().strip()
            except Exception:
                continue
            if answer.lower() not in text.lower():
                continue
            if self._option_has_submenu(opt):
                continue
            opt.click(timeout=3000, force=True)
            self.page.wait_for_timeout(400)
            return True
        return False

    def _drill_into_category(self, wrapper, category_name: str) -> bool:
        options = self._open_menu_items(wrapper)
        for opt in options:
            try:
                text = opt.inner_text().strip()
            except Exception:
                continue
            if text.lower() == category_name.lower() and self._option_has_submenu(opt):
                opt.click(timeout=3000, force=True)
                self.page.wait_for_timeout(600)
                return True
        return False

    def _pick_safe_leaf_in_open_category(self, wrapper, keyword_priority: list) -> bool:
        options = self._open_menu_items(wrapper)
        leaves = []
        for opt in options:
            try:
                text = opt.inner_text().strip()
            except Exception:
                continue
            if text and not self._option_has_submenu(opt):
                leaves.append((text, opt))
        for keyword in keyword_priority:
            for text, opt in leaves:
                if keyword.lower() in text.lower():
                    opt.click(timeout=3000, force=True)
                    self.page.wait_for_timeout(400)
                    return True
        return False

    def _fill_combobox(self, wrapper, answer: str, is_source_style: bool = False) -> bool:
        try:
            # A previous combobox interaction elsewhere on the page can
            # leave its own dropdown open, which then intercepts the
            # click on THIS field's trigger ("<li> ... subtree intercepts
            # pointer events", confirmed live). Force-close anything
            # already open before starting a fresh interaction.
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)
            wrapper.scroll_into_view_if_needed()

            trigger = wrapper.locator("button, input").first
            trigger.click(timeout=5000, force=True)
            self.page.wait_for_timeout(500)
            # Not every Workday combobox actually filters on typed text —
            # confirmed live: "How Did You Hear About Us?" shows its full,
            # unfiltered option list regardless of typing. Typing first is
            # harmless where it DOES filter (Country) and a no-op where it
            # doesn't, so it's kept as a best-effort narrowing step.
            self.page.keyboard.type(answer, delay=100)
            self.page.wait_for_timeout(700)

            if self._select_option_in_open_list(wrapper, answer):
                if self._is_combobox_committed(wrapper):
                    return True

            if is_source_style:
                # Every top-level item was a category, none matched the
                # answer as a leaf — drill into the most defensible
                # generic category rather than clicking a category node
                # and treating that as success.
                for category, keywords in self._SOURCE_CATEGORY_FALLBACKS:
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(200)
                    trigger.click(timeout=5000, force=True)
                    self.page.wait_for_timeout(500)
                    if not self._drill_into_category(wrapper, category):
                        continue
                    if self._pick_safe_leaf_in_open_category(wrapper, keywords):
                        if self._is_combobox_committed(wrapper):
                            return True

            self.page.keyboard.press("Escape")
            return False
        except Exception as e:
            logger.info(f"WorkdayHandler: Combobox fill failed: {e}")
            return False

    def _fill_radio_group(self, wrapper, answer: str) -> bool:
        try:
            labels = wrapper.locator("label").all()
            target = answer.strip().lower()
            for lbl in labels:
                text = lbl.inner_text().strip().lower()
                if text == target or (target in ("yes", "no") and text == target):
                    radio_input = lbl.locator('input[type="radio"]').first
                    if radio_input.count() == 0:
                        for_id = lbl.get_attribute("for")
                        if for_id:
                            radio_input = wrapper.locator(f'#{for_id}').first
                    # A single click() isn't reliably reflected in
                    # is_checked() immediately on this React-controlled
                    # widget — confirmed live: the click fired without
                    # error, but the review step still showed the field
                    # as empty. Verify and retry a couple of times rather
                    # than trusting one click, same pattern already used
                    # for every other React-controlled checkbox/radio in
                    # this codebase (_click_and_verify_checked).
                    for _ in range(3):
                        lbl.click(timeout=3000, force=True)
                        self.page.wait_for_timeout(300)
                        try:
                            if radio_input.count() > 0 and radio_input.is_checked():
                                return True
                        except Exception:
                            pass
                    return False
            return False
        except Exception as e:
            logger.info(f"WorkdayHandler: Radio group fill failed: {e}")
            return False

    def _ask(self, question: str, field_type: str, options: list = None, required: bool = True) -> str:
        translated = translate_to_english(question, self.engine.llm_client)
        dom_meta = {"css_selector": "", "input_tag": field_type, "visible": True, "disabled": False, "current_value": "", "widget_type": field_type}
        answer = self.engine.answer(question=translated, field_type=field_type, options=options or [], label_text=translated, required=required, dom_meta=dom_meta)
        # Matches every other handler's pattern (base_handler.py's
        # _process_custom_fields): a low-confidence answer is treated as
        # unanswerable, not typed in as-is. Without this check, an
        # optional field the profile has no real data for (e.g. "Local
        # Given Name(s)") got a nonsense LLM non-answer ("I do not have a
        # local given name(s) as I am an automated application
        # assistant.") typed directly into the field instead of being
        # left blank.
        conf = dom_meta.get("confidence", 100)
        if answer in ("NORMALIZATION_FAILED", "REVIEW_REQUIRED") or conf < 70:
            return ""
        return answer

    def _process_current_step(self, telemetry: dict) -> bool:
        """Fills every formField on the current wizard page — standard
        identity fields directly from the profile, everything else
        through the shared QuestionEngine. Returns False if any REQUIRED
        field couldn't be confidently answered (never guesses)."""
        safe = True
        wrappers = self._find_all_form_fields()
        logger.info(f"WorkdayHandler: Processing {len(wrappers)} fields on current step.")
        combobox_fills = []  # [(wrapper, aid, answer_used), ...] for the verify-and-reassert pass below

        # Multiselect-style comboboxes (tag-chip widgets like "How Did You
        # Hear About Us?"/"Country Phone Code") are the ones observed
        # reverting after a LATER field's own interaction — processing
        # them last, immediately before Next, gives nothing left in this
        # step a chance to disturb them afterward. Plain fields keep their
        # original DOM order relative to each other.
        def _is_multiselect_wrapper(w):
            try:
                return w.locator('[data-automation-id="multiSelectContainer"], [data-automation-id="multiselectInputContainer"]').count() > 0
            except Exception:
                return False
        wrappers = sorted(wrappers, key=_is_multiselect_wrapper)

        for wrapper in wrappers:
            try:
                aid = wrapper.get_attribute("data-automation-id") or ""

                # Date fields (work experience/education From-To, spinbutton
                # month+year pairs) are pre-populated by Workday's own
                # "Autofill with Resume" parsing and are already correct —
                # confirmed live via each field's own "current value is
                # X/Y" helper text and populated spinbutton values. Routing
                # a bare label like "From" through the generic question
                # engine produced a nonsense free-text answer ("I am
                # applying for the Retail Sales Representative position.")
                # that got typed into the month spinbutton, wiping out the
                # correct autofilled value and producing Workday's own
                # "Invalid Date" validation error. Never touch these —
                # leave Workday's autofill as the source of truth.
                if wrapper.locator('[data-automation-id="dateInputWrapper"]').count() > 0:
                    continue

                is_required = wrapper.locator('abbr').count() > 0
                # Two visually different combobox implementations share
                # this platform: a plain button[aria-haspopup=listbox]
                # (Country) and a tag-style "multiselect" widget whose
                # trigger is an <input> wrapped in a
                # multiSelectContainer/multiselectInputContainer
                # (Country Phone Code, How Did You Hear About Us). The
                # multiselect's inner input previously satisfied the
                # plain-text-field check below and got free-text typed
                # into it via the question engine — which doesn't create
                # a real selected value in a combobox, just stray loose
                # text — so both must be detected as "combobox" up front,
                # before the plain-input branch ever sees them.
                is_multiselect = wrapper.locator('[data-automation-id="multiSelectContainer"], [data-automation-id="multiselectInputContainer"]').count() > 0
                has_button = wrapper.locator('button[aria-haspopup="listbox"]').count() > 0 or is_multiselect
                has_radio = wrapper.locator('input[type="radio"]').count() > 0
                has_checkbox = wrapper.locator('input[type="checkbox"]').count() > 0
                has_input = (not has_button) and (not has_radio) and (not has_checkbox) and \
                    wrapper.locator("input:not([type=checkbox]):not([type=radio])").count() > 0

                # Standard identity fields — filled directly, not via the
                # question engine, matching every other handler's pattern.
                if aid in self._STANDARD_FIELD_MAP and has_input:
                    value = self._STANDARD_FIELD_MAP[aid](self)
                    if not value:
                        continue
                    inp = wrapper.locator("input").first
                    self._human_type(inp, value)
                    self.page.wait_for_timeout(120)
                    if not inp.input_value():
                        logger.info(f"WorkdayHandler: CRITICAL - {aid} failed to populate.")
                        if is_required:
                            safe = False
                    elif aid == "formField-emailAddress":
                        telemetry.setdefault("filled_fields", {})["Email"] = True
                    elif aid == "formField-phoneNumber":
                        telemetry.setdefault("filled_fields", {})["Phone"] = True
                    continue

                if aid in ("formField-country", "formField-countryPhoneCode") and has_button:
                    # countryPhoneCode is left at whatever this tenant's
                    # default is (often United States) otherwise, which
                    # produced a "phone number format" validation error
                    # since a 10-digit Indian number doesn't match the
                    # expected US pattern.
                    current = wrapper.locator("button, input").first.inner_text() if wrapper.locator("button").count() > 0 else ""
                    country = self.profile.get_field("country") or "India"
                    if country not in (current or ""):
                        if self._fill_combobox(wrapper, country):
                            combobox_fills.append((wrapper, aid, country))
                    continue

                label = self._label_for(wrapper)
                if not label:
                    continue

                # Everything else — tenant custom questions, "How did you
                # hear about us", previous-worker boolean, etc. — routed
                # through the same QuestionEngine every other platform
                # uses, so it gets the same classification, RAG grounding,
                # and no-guessing-on-required-fields safety behavior.
                if has_button:
                    # Some comboboxes (e.g. "Phone Device Type") already
                    # come pre-set to a sensible default ("Mobile") —
                    # don't touch an already-populated field. Asking the
                    # question engine for one anyway produced a nonsense
                    # answer (the raw phone NUMBER, "9891148156", for a
                    # question about device TYPE) and then overwrote a
                    # value that was already correct.
                    current_text = wrapper.locator("button, input").first.inner_text() if wrapper.locator("button").count() > 0 else wrapper.locator("input").first.input_value()
                    if current_text and current_text.strip() and "select" not in current_text.strip().lower():
                        continue

                    is_source_style = aid == "formField-source"
                    real_options = self._get_combobox_options(wrapper)
                    answer = self._ask(label, field_type="dropdown", options=real_options, required=is_required)
                    used_answer = answer or ("Career Websites" if is_source_style else "")
                    if not used_answer:
                        if is_required:
                            safe = False
                        continue
                    filled = self._fill_combobox(wrapper, used_answer, is_source_style=is_source_style)
                    if not filled and is_source_style:
                        # The engine's answer (e.g. the shared SOURCE
                        # default, "LinkedIn") doesn't exist verbatim in
                        # every tenant's own option wording, and on this
                        # platform "How Did You Hear About Us?" is often a
                        # two-level category tree where every top-level
                        # item (including a literal "Other") is a category
                        # requiring a further leaf click, not a directly
                        # selectable value — confirmed live. _fill_combobox
                        # already tries the curated category fallbacks
                        # above; this second attempt just forces that path
                        # even when the first attempt's typed answer
                        # accidentally matched a category label as a false
                        # "leaf".
                        filled = self._fill_combobox(wrapper, "Career Websites", is_source_style=True)
                    if filled:
                        combobox_fills.append((wrapper, label, used_answer))
                    if not filled and is_required:
                        safe = False
                elif has_radio:
                    opt_labels = [l.strip() for l in wrapper.locator("label").all_inner_texts() if l.strip() and l.strip() != label]
                    answer = self._ask(label, field_type="dropdown", options=opt_labels, required=is_required)
                    if answer:
                        fill_ok = self._fill_radio_group(wrapper, answer)
                        if not fill_ok and is_required:
                            safe = False
                    elif is_required:
                        safe = False
                elif has_checkbox:
                    # Optional acknowledgement-style checkboxes (e.g. SMS
                    # opt-in) — never required on this platform in what
                    # was scouted; leave unchecked rather than guess.
                    continue
                elif has_input:
                    # Optional free-text fields are only asked when they're
                    # a real, well-grounded fact (name/contact-style, which
                    # the STANDARD_FIELD_MAP branch above already handles
                    # directly) — anything left over here that's optional
                    # is usually a field the profile has no honest answer
                    # for at all (e.g. Workday's "Local Given Name(s)",
                    # a non-Latin-script name accommodation this candidate
                    # doesn't need). Asking the LLM anyway produced a
                    # polite non-answer ("I do not have a local given
                    # name(s)...") typed directly into the field — worse
                    # than just leaving it blank. Only required fields go
                    # through the full question pipeline; optional ones
                    # are left untouched, same "don't guess" principle
                    # every other handler already follows for optional
                    # fields with no clear source of truth.
                    if not is_required:
                        continue
                    answer = self._ask(label, field_type="text", required=is_required)
                    if answer:
                        inp = wrapper.locator("input").first
                        self._human_type(inp, answer)
                    else:
                        safe = False
            except Exception as e:
                logger.info(f"WorkdayHandler: Error processing field: {e}")
                safe = False

        # Verify-and-reassert pass: confirmed live that a combobox filled
        # earlier in this same loop (e.g. "How Did You Hear About Us?")
        # can silently reset back to empty by the time later fields in
        # the SAME step finish processing — most likely a React re-render
        # triggered by a later field's own change clobbering an earlier
        # field's committed value. A single successful fill is therefore
        # not trustworthy on its own; re-check every combobox this pass
        # touched right before deciding the step is done, and retry once
        # if it reverted. NOTE: a second full retry pass was tried and
        # made things WORSE (confirmed live) — reasserting one multiselect
        # can disturb another, and repeating the cycle just traded which
        # field ended up broken rather than converging. One pass only —
        # and in REVERSE fill order, so whichever field was filled FIRST
        # (and is therefore most exposed to being disturbed by every
        # later field's own interaction) gets reasserted LAST, i.e.
        # closest to the actual Next click with nothing left to disturb
        # it afterward.
        for wrapper, aid_or_label, used_answer in reversed(combobox_fills):
            try:
                if not self._is_combobox_committed(wrapper):
                    logger.info(f"WorkdayHandler: '{aid_or_label}' reverted after being filled — re-asserting {used_answer!r}.")
                    if not self._fill_combobox(wrapper, used_answer, is_source_style=(aid_or_label == "How Did You Hear About Us?")):
                        safe = False
            except Exception as e:
                logger.info(f"WorkdayHandler: Verify-and-reassert failed for '{aid_or_label}': {e}")

        return safe

    # ------------------------------------------------------------------
    # Main wizard loop
    # ------------------------------------------------------------------

    def execute(self) -> dict:
        telemetry = {
            "question_count": 0, "llm_question_count": 0, "profile_question_count": 0,
            "filled_fields": {"Resume": False, "Email": False, "Phone": False, "LinkedIn": False,
                               "Questions": False, "Attachments": False},
        }
        self.telemetry = telemetry

        try:
            self._enter_application_flow()
            self._capture_screenshot("01_apply_flow_entered.png")

            # "Autofill with Resume" step: upload, then Next.
            file_input = self._find("file-upload-input-ref")
            if file_input:
                if not os.path.exists(self.resume_path):
                    return {"status": WorkflowState.REVIEW_REQUIRED.name, "telemetry": telemetry, "audit_log": self.engine.audit_log}
                file_input.set_input_files(self.resume_path, timeout=8000)
                self.page.wait_for_timeout(3000)
                telemetry["resume_upload_success"] = True
                telemetry["filled_fields"]["Resume"] = True
                next_btn = self._find("pageFooterNextButton")
                if next_btn:
                    next_btn.click(timeout=8000)
                    self.page.wait_for_timeout(3000)

            safe_to_submit = True
            for step_num in range(self._MAX_STEPS):
                self.page.wait_for_timeout(1500)
                self._capture_screenshot(f"step_{step_num}.png")

                # Reached Review/final step — no more formFields to fill,
                # a submit button appears instead of Next.
                submit_btn = self._find("pageFooterSubmitButton", retries=2, wait_ms=300)
                if submit_btn:
                    logger.info("WorkdayHandler: Reached Review step.")
                    break

                current_step_name = self._active_step_name()
                logger.info(f"WorkdayHandler: On step '{current_step_name}'.")

                if not self._process_current_step(telemetry):
                    safe_to_submit = False

                # Workday doesn't navigate away on Next if a required
                # field is still missing/invalid — it just re-renders the
                # SAME step with validation errors surfaced. But confirmed
                # live: even with every field genuinely valid (zero
                # aria-invalid, no "Errors Found" banner, no console
                # errors), the FIRST click on Next is sometimes a silent
                # no-op — the page doesn't navigate and shows no error at
                # all — and only a SECOND click actually advances. Retry a
                # couple of times before concluding a field is really
                # invalid, rather than escalating on what's actually just
                # a swallowed first click.
                new_step_name = current_step_name
                for attempt in range(3):
                    next_btn = self.page.locator('[data-automation-id="pageFooterNextButton"]').first
                    if next_btn.count() == 0:
                        logger.info("WorkdayHandler: No Next button found — stopping wizard walk.")
                        new_step_name = None
                        break
                    next_btn.scroll_into_view_if_needed()
                    self.page.wait_for_timeout(200)
                    next_btn.click(timeout=8000)
                    self.page.wait_for_timeout(2500)
                    new_step_name = self._active_step_name()
                    if new_step_name != current_step_name:
                        break

                if new_step_name is None:
                    break
                if new_step_name == current_step_name:
                    logger.info(f"WorkdayHandler: Step name unchanged after {attempt + 1} Next attempts ('{new_step_name}') — a required field is likely still invalid. Escalating.")
                    safe_to_submit = False
                    break
            else:
                logger.info(f"WorkdayHandler: Exceeded {self._MAX_STEPS} steps without reaching Review.")
                safe_to_submit = False

            self._capture_screenshot("final_review.png")

            if not safe_to_submit:
                return {"status": WorkflowState.REVIEW_REQUIRED.name, "telemetry": telemetry, "audit_log": self.engine.audit_log}

            if self.test_mode:
                logger.info("WorkdayHandler: TEST MODE ACTIVE. Skipping final submit.")
                return {"status": WorkflowState.COMPLETED.name, "telemetry": telemetry, "audit_log": self.engine.audit_log}

            submit_btn = self._find("pageFooterSubmitButton")
            if not submit_btn:
                return {"status": WorkflowState.REVIEW_REQUIRED.name, "telemetry": telemetry, "audit_log": self.engine.audit_log}
            submit_btn.click(timeout=8000)
            self.page.wait_for_timeout(3000)
            telemetry["really_submitted"] = True
            return {"status": WorkflowState.COMPLETED.name, "telemetry": telemetry, "audit_log": self.engine.audit_log}

        except Exception as e:
            logger.info(f"WorkdayHandler Execution Error: {e}")
            return {"status": WorkflowState.FAILED.name, "error": str(e), "telemetry": telemetry, "audit_log": self.engine.audit_log}
