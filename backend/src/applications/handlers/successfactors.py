"""
SuccessFactors (SAP) requires a real candidate account before any
application form is reachable — confirmed live across multiple tenants
(BRITA, and the same pattern on others): browsing job postings and job
search is open, but clicking through to apply always lands on either a
"Konto anlegen" (create account) or "Anmelden" (sign in) page. There is
no guest/manual-apply bypass like Workday offers.

The good news, also confirmed live: first-time REGISTRATION has no
CAPTCHA at all, and successfully completing it auto-authenticates the
new account straight into the real application form — no separate login
step needed. Only a RETURNING login (second application to the same
tenant) is CAPTCHA-gated (a real reCAPTCHA v2 checkbox widget, not
invisible v3), which this handler cannot safely solve — it escalates to
REVIEW_REQUIRED rather than attempt it.

Once authenticated, the real form is a single scrollable page with
collapsible sections (Documents, Profile Information, Work Experience,
Education, Languages, Job-specific Questions) — native HTML fields
throughout, no custom JS widgets like Workday's comboboxes. This lets
the handler lean on BaseATSHandler's standard single-page flow for
almost everything, with only the account-flow prelude and section
expansion being SuccessFactors-specific.
"""
from src.system.logger import setup_logger
logger = setup_logger('successfactors')
import os
import re
from urllib.parse import urlparse

from src.system.state import WorkflowState
from src.applications.handlers.base_handler import BaseATSHandler
from src.applications.ats_credentials import get_or_create_credentials, has_credentials


class SuccessFactorsHandler(BaseATSHandler):
    ATS_NAME = "SUCCESSFACTORS"

    def _tenant(self) -> str:
        # career5.successfactors.eu/careers?company=britagmbh -> "britagmbh"
        try:
            qs = self.page.url.split("company=")[1]
            return qs.split("&")[0]
        except Exception:
            return urlparse(self.page.url).hostname or "unknown"

    def _enter_application_flow(self):
        logger.info("SuccessFactorsHandler: Entering application flow...")
        self.page.wait_for_timeout(2000)

        for txt in ["Alle akzeptieren", "Akzeptieren", "Accept All", "Accept all cookies"]:
            btn = self.page.get_by_text(txt, exact=False).first
            if btn.count() > 0:
                try:
                    btn.click(timeout=3000)
                    break
                except Exception:
                    pass
        self.page.wait_for_timeout(1000)

        # The apply trigger's text is localized per tenant (confirmed
        # live: "Jetzt bewerben" in German, "Aplikuj teraz" in Polish,
        # "Apply now" in English) so text-matching it is fragile across
        # tenants — but every tenant shares the same CSS class
        # (".dialogApplyBtn") regardless of language. Two different
        # interaction shapes were confirmed live from that same class:
        # some tenants (BRITA) render it as a <button> that opens a
        # dropdown menu with a separate "#applyOption-top-manual" link to
        # actually click; others (mBank/Pekao) render it as a directly
        # clickable <a> that navigates straight through — no dropdown at
        # all. Handle both from the one class selector rather than
        # hardcoding either shape.
        apply_btn = None
        for _ in range(10):
            candidate = self.page.locator(".dialogApplyBtn").first
            if candidate.count() > 0 and candidate.is_visible():
                apply_btn = candidate
                break
            self.page.wait_for_timeout(1000)
        if not apply_btn:
            logger.info("SuccessFactorsHandler: Apply button never became visible.")
            return

        # The trigger click itself is sometimes a silent no-op (same
        # failure mode already fixed on Workday's Next button) — re-click
        # if neither a dropdown option nor a real navigation happened.
        manual_link = None
        for outer in range(4):
            start_url = self.page.url
            apply_btn.click(timeout=5000, force=True)
            self.page.wait_for_timeout(1500)
            for _ in range(4):
                candidate = self.page.locator('#applyOption-top-manual').first
                if candidate.count() > 0 and candidate.is_visible():
                    manual_link = candidate
                    break
                if self.page.url != start_url:
                    break
                self.page.wait_for_timeout(1000)
            if manual_link or self.page.url != start_url:
                break
            logger.info(f"SuccessFactorsHandler: Apply click had no effect on attempt {outer + 1}, retrying.")
        if manual_link:
            manual_link.click(timeout=8000, force=True)
        elif self.page.url == start_url:
            logger.info("SuccessFactorsHandler: Apply click never produced a dropdown or navigation.")
            return
        self.page.wait_for_load_state("networkidle", timeout=15000)
        self.page.wait_for_timeout(1500)

        self._handle_account_flow()

    def _handle_account_flow(self):
        tenant = self._tenant()
        email = self.profile.get_field("email")
        is_new_tenant = not has_credentials("successfactors", tenant)
        creds = get_or_create_credentials("successfactors", tenant, email)

        # The page SuccessFactors lands on right after clicking "manual
        # apply" is ALWAYS the "Anmelden" (sign-in) form by default,
        # regardless of whether this candidate has an account yet — a
        # "Richte dir ein Benutzerkonto ein" link is what actually leads
        # to registration. Deciding which path to take by looking at page
        # state alone is wrong (confirmed live: it misclassified a
        # brand-new tenant as "existing account" and went straight to a
        # login it could never complete) — the credential STORE is the
        # real source of truth for whether this is a first-time tenant.
        for _ in range(8):
            if self.page.locator("#fbclc_fName").count() > 0 or self.page.locator('input[type="password"]').count() > 0:
                break
            self.page.wait_for_timeout(1000)

        if is_new_tenant and self.page.locator("#fbclc_fName").count() == 0:
            # The "create account" link's text is localized per tenant
            # just like the apply/sign-in buttons ("Richte dir ein
            # Benutzerkonto ein" German, "Utwórz konto" Polish) — a
            # German/English-only regex silently missed the Polish
            # version and left the flow stuck on the login page,
            # eventually falling through to a login attempt for an
            # account that was never actually created. Its href always
            # contains "login_ns=register" regardless of tenant language
            # (confirmed live) — a language-independent signal.
            create_link = self.page.locator('a[href*="login_ns=register"]').first
            if create_link.count() == 0:
                create_link = self.page.get_by_text(
                    re.compile("benutzerkonto ein|create.*account|utwórz konto", re.I)
                ).first
            if create_link.count() > 0:
                create_link.scroll_into_view_if_needed()
                self.page.wait_for_timeout(500)
                for _ in range(4):
                    try:
                        create_link.click(timeout=5000)
                        self.page.wait_for_load_state("networkidle", timeout=15000)
                        self.page.wait_for_timeout(1500)
                        if self.page.locator("#fbclc_fName").count() > 0:
                            break
                    except Exception:
                        pass
                    self.page.wait_for_timeout(1500)

        if self.page.locator("#fbclc_fName").count() > 0:
            self._register_account(creds)
        else:
            self._login(creds)

    def _register_account(self, creds: dict):
        logger.info("SuccessFactorsHandler: Registering new candidate account...")
        first_name = self.profile.get_field("first_name") or ""
        last_name = self.profile.get_field("last_name") or ""
        country = self.profile.get_field("country") or ""

        self.page.fill("#fbclc_userName", creds["email"])
        self.page.fill("#fbclc_emailConf", creds["email"])
        self.page.fill("#fbclc_pwd", creds["password"])
        self.page.fill("#fbclc_pwdConf", creds["password"])
        self.page.fill("#fbclc_fName", first_name)
        self.page.fill("#fbclc_lName", last_name)

        country_select = self.page.locator("select").first
        if country_select.count() > 0 and country:
            try:
                country_select.select_option(label=country)
            except Exception:
                # Country names are localized per tenant (e.g. "India" vs
                # "Indien") — fall back to a substring match against the
                # real option list rather than failing the whole field.
                opts = country_select.locator("option").all_inner_texts()
                match = next((o for o in opts if country.lower()[:4] in o.lower()), None)
                if match:
                    country_select.select_option(label=match)

        # Most restrictive profile-visibility option (last radio, per the
        # real option text: "only recruiters for jobs I actually applied
        # to") — matches this project's standing privacy-conservative
        # default for any visibility/sharing choice with no explicit
        # candidate instruction.
        radios = self.page.locator('input[type="radio"]')
        if radios.count() > 0:
            radios.last.check(timeout=3000)

        # The privacy-terms link runs its own validation pass over the
        # rest of the form before it will even open — confirmed live:
        # with other required fields still empty it just surfaces inline
        # errors instead of opening the acceptance dialog. Everything
        # above must be filled first, which it now is.
        # Localized text again ("Lies und akzeptiere die
        # Datenschutzerklärung" German) — the element's own id
        # ("dataPrivacyId") is stable across tenant languages, confirmed
        # live, and is the reliable primary selector.
        terms_link = self.page.locator("#dataPrivacyId").first
        if terms_link.count() == 0:
            terms_link = self.page.get_by_text("Lies und akzeptiere", exact=False).first
        if terms_link.count() == 0:
            terms_link = self.page.get_by_text("privacy", exact=False).first
        if terms_link.count() > 0:
            terms_link.click(timeout=5000)
            self.page.wait_for_timeout(1500)
            # Button text is localized ("Akzeptieren" German, presumably
            # something else per tenant language) — the dialog's own
            # Accept/Decline pair is structurally stable though (Accept
            # is always the first action button, confirmed live), so
            # target it by position within the dialog rather than text.
            dialog = self.page.get_by_role("dialog").first
            accept_btn = dialog.locator("button").first
            if accept_btn.count() > 0:
                accept_btn.click(timeout=5000)
                self.page.wait_for_timeout(1000)

        # Same localization issue as the apply/sign-in/create-account
        # buttons — "Konto anlegen" is German-only wording. The
        # registration form's own submit button is structurally the last
        # button within the form containing fbclc_fName, regardless of
        # tenant language.
        submit_btn = None
        try:
            form = self.page.locator("#fbclc_fName").locator("xpath=ancestor::form").first
            if form.count() > 0:
                candidate = form.locator("button").last
                if candidate.count() > 0:
                    submit_btn = candidate
        except Exception:
            pass
        if submit_btn is None:
            submit_btn = self.page.get_by_role(
                "button", name=re.compile("konto anlegen|create account", re.I)
            ).first
        if submit_btn.count() == 0:
            logger.info("SuccessFactorsHandler: Registration submit button not found.")
            return
        submit_btn.click(timeout=8000)
        self.page.wait_for_load_state("networkidle", timeout=20000)
        self.page.wait_for_timeout(2000)
        logger.info("SuccessFactorsHandler: Registration submitted.")

    def _login(self, creds: dict):
        logger.info("SuccessFactorsHandler: Existing account found for this tenant — attempting login...")
        # A real reCAPTCHA v2 checkbox (not invisible v3) guards the LOGIN
        # form specifically — confirmed live, distinct from registration
        # which has none. This handler does not attempt to solve it; a
        # returning application to the same tenant safely escalates
        # rather than risk a stuck/incorrect automated CAPTCHA attempt.
        if self.page.locator('iframe[src*="recaptcha"]').count() > 0:
            logger.info("SuccessFactorsHandler: Login is CAPTCHA-gated — cannot proceed automatically.")
            self._captcha_blocked = True
            return

        email_input = self.page.locator('input[type="text"], input[type="email"]').first
        pw_input = self.page.locator('input[type="password"]').first
        if email_input.count() == 0 or pw_input.count() == 0:
            logger.info("SuccessFactorsHandler: Login fields not found.")
            return
        email_input.fill(creds["email"])
        pw_input.fill(creds["password"])

        # The sign-in button's text is localized per tenant just like the
        # apply trigger ("Anmelden" German, "Zaloguj się" Polish, "Sign
        # In" English) — confirmed live that a German/English-only regex
        # silently missed the Polish button and left the form filled but
        # never submitted. Target it structurally instead: the first
        # visible button inside the same <form> as the password field,
        # language-independent.
        signin_btn = None
        try:
            form = pw_input.locator("xpath=ancestor::form").first
            if form.count() > 0:
                candidate = form.locator("button").first
                if candidate.count() > 0:
                    signin_btn = candidate
        except Exception:
            pass
        if signin_btn is None:
            signin_btn = self.page.get_by_role(
                "button", name=re.compile("anmelden|sign in|zaloguj", re.I)
            ).first
        if signin_btn.count() > 0:
            signin_btn.click(timeout=8000)
            self.page.wait_for_load_state("networkidle", timeout=15000)
            self.page.wait_for_timeout(1500)
        else:
            logger.info("SuccessFactorsHandler: Sign-in button not found.")

    def _detect_and_set_iframe(self):
        self.active_context = self.page

    def _expand_all_sections(self):
        # Documents/Profile/Experience/Education/Languages/Job-specific
        # sections are collapsed by default; a "Alle Abschnitte
        # einblenden" (expand all) link does exactly what's needed in one
        # click, confirmed present on every tenant scouted.
        expand_all = self.page.get_by_text(
            re.compile("alle abschnitte einblenden|expand all", re.I)
        ).first
        if expand_all.count() > 0:
            try:
                expand_all.click(timeout=5000)
                self.page.wait_for_timeout(1000)
                return
            except Exception:
                pass
        # Fallback: click each collapsed section header individually.
        headers = self.page.locator('[class*="sectionHeader"], [role="button"]').all()
        for h in headers:
            try:
                if h.is_visible():
                    h.click(timeout=2000)
            except Exception:
                continue

    def _fill_and_verify_standard_fields(self) -> bool:
        if getattr(self, "_captcha_blocked", False):
            return False

        self._expand_all_sections()
        safe = True

        # Field IDs on this platform are stable German-labeled ids that
        # showed up consistently on registration (fbclc_*) but the
        # profile-information section uses its own distinct set —
        # matched by label text instead, since ids there are dynamically
        # generated per tenant (confirmed live: no shared prefix like
        # Workday's data-automation-id convention).
        field_map = {
            "Vorname": self.profile.get_field("first_name"),
            "Nachname": self.profile.get_field("last_name"),
            "Telefon": self.profile.get_field("phone"),
            "Straße und Hausnummer": self.profile.get_field("address"),
            "Stadt": self.profile.get_field("city"),
            "Postleitzahl": self.profile.get_field("postal_code"),
        }
        for label, value in field_map.items():
            if not value:
                continue
            input_el = self._input_for_label(label)
            if input_el is None:
                continue
            current = input_el.input_value()
            if current:
                continue
            try:
                self._human_type(input_el, value)
                self.page.wait_for_timeout(120)
                if not input_el.input_value() and label in ("Vorname", "Nachname"):
                    logger.info(f"SuccessFactorsHandler: CRITICAL - {label} failed to populate.")
                    safe = False
            except Exception as e:
                logger.info(f"SuccessFactorsHandler: Error filling {label}: {e}")

        email_input = self._input_for_label("E-Mail Adresse") or self._input_for_label("Email")
        if email_input is not None:
            self.telemetry.setdefault("filled_fields", {})["Email"] = bool(email_input.input_value())
        phone_input = self._input_for_label("Telefon")
        if phone_input is not None:
            self.telemetry.setdefault("filled_fields", {})["Phone"] = bool(phone_input.input_value())

        return safe

    def _input_for_label(self, label_text: str):
        try:
            label = self.page.locator("label", has_text=label_text).first
            if label.count() == 0:
                return None
            for_id = label.get_attribute("for")
            if for_id:
                el = self.page.locator(f"#{for_id}")
                if el.count() > 0:
                    return el.first
            # Fallback: nearest following input in the same field wrapper.
            wrapper = label.locator("xpath=..")
            el = wrapper.locator("input").first
            return el if el.count() > 0 else None
        except Exception:
            return None

    def _upload_resume(self) -> bool:
        if getattr(self, "_captcha_blocked", False):
            return False

        logger.info(f"SuccessFactorsHandler: Uploading resume {self.resume_path}...")
        if "filled_fields" not in self.telemetry:
            self.telemetry["filled_fields"] = {}
        if not os.path.exists(self.resume_path):
            logger.info("SuccessFactorsHandler: Resume file does not exist.")
            return False

        # The visible "Lebenslauf hochladen" tile has no plain <input
        # type=file> until its own upload button is clicked — a hidden
        # accessibility tooltip span shares the label text and must not
        # be mistaken for the real trigger (confirmed live: clicking it
        # does nothing). The real trigger is a "+" icon button with class
        # "addAttachments" and no text/aria-label at all — confirmed live
        # via a full button-attribute dump. Three such buttons exist
        # (Resume, Cover Letter, Additional Documents, in that DOM order)
        # — the first is Resume/CV. expect_file_chooser around its click
        # is the reliable path.
        # Right after registration submits, the redirect to the candidate
        # profile page can take a few seconds longer to fully render than
        # `networkidle` alone accounts for (confirmed live: a fixed short
        # gap between "Registration submitted" and this check found 0
        # matches, while polling for a few extra seconds reliably found
        # the same button) — poll instead of trusting one snapshot.
        resume_btn = None
        for _ in range(8):
            candidate = self.page.locator("button.addAttachments, [class*='addAttachments']").first
            if candidate.count() > 0:
                resume_btn = candidate
                break
            self.page.wait_for_timeout(1000)
        if resume_btn is None:
            logger.info("SuccessFactorsHandler: Resume upload button not found.")
            return False

        resume_btn.scroll_into_view_if_needed()
        self.page.wait_for_timeout(300)
        try:
            resume_btn.click(timeout=5000, force=True)
            self.page.wait_for_timeout(800)
            # Clicking "+" opens a source-choice dialog ("Von Gerät
            # hochladen" / upload from device vs "Aus Dropbox hochladen")
            # rather than going straight to a native file chooser — but
            # the real <input type="file"> is already layered directly on
            # top of that "device" label (aria-labelledby points to it,
            # and it intercepts the label's own click per Playwright's
            # actionability check) — confirmed live. No separate click
            # needed; set_input_files targets it directly.
            file_input = self.page.locator('input[type="file"]').first
            file_input.set_input_files(self.resume_path, timeout=8000)
            self.page.wait_for_timeout(4000)
        except Exception as e:
            logger.info(f"SuccessFactorsHandler: Resume upload failed: {e}")
            return False

        self.telemetry["resume_upload_success"] = True
        self.telemetry["filled_fields"]["Resume"] = True
        return True

    def _extract_questions(self) -> list[dict]:
        if getattr(self, "_captcha_blocked", False):
            return []

        logger.info("SuccessFactorsHandler: Extracting questions...")
        questions = []
        skip_labels = {
            "vorname", "zweiter vorname", "nachname", "e-mail adresse", "telefon",
            "link zu sozialem netzwerk", "straße und hausnummer", "adresszusatz",
            "stadt", "postleitzahl", "land", "geburtsdatum", "nationalität", "geschlecht",
        }

        labels = self.active_context.locator("label").all()
        for label in labels:
            try:
                if not label.is_visible():
                    continue
                raw_text = label.inner_text().split("\n")[0].strip()
                clean_label = raw_text.replace("*", "").strip()
                if not clean_label or clean_label.lower() in skip_labels:
                    continue

                for_id = label.get_attribute("for")
                field = self.active_context.locator(f"#{for_id}").first if for_id else None
                if field is None or field.count() == 0:
                    continue

                tag = field.evaluate("e => e.tagName").lower()
                is_required = "*" in raw_text or label.locator(".required, [class*=required]").count() > 0

                widget_type = "unknown"
                options = []
                placeholder = ""
                if tag == "select":
                    widget_type = "native_select"
                    options = [o.strip() for o in field.locator("option").all_inner_texts() if o.strip() and "auswahl" not in o.lower() and "select" not in o.lower()]
                elif tag == "textarea":
                    widget_type = "textarea"
                    placeholder = field.get_attribute("placeholder") or ""
                elif tag == "input":
                    input_type = (field.get_attribute("type") or "text").lower()
                    if input_type in ("radio", "checkbox"):
                        continue
                    if input_type == "file":
                        continue
                    widget_type = "input"
                    placeholder = field.get_attribute("placeholder") or ""

                if widget_type == "unknown":
                    continue

                questions.append({
                    "container": field, "question": clean_label, "raw_label": raw_text,
                    "is_required": is_required, "widget_type": widget_type,
                    "options": options, "placeholder": placeholder,
                })
            except Exception:
                continue

        logger.info(f"SuccessFactorsHandler: Detected {len(questions)} questions.")
        return questions

    def _get_submit_button_locator(self):
        # "Bewerben"/"Apply" is localized text again. It shares its CSS
        # class ("rcmSaveButton") with the neighboring "Speichern"/"Save"
        # button, confirmed live, but always appears second/last in DOM
        # order — a language-independent positional signal.
        by_class = self.page.locator(".rcmSaveButton").last
        if by_class.count() > 0:
            return by_class
        return self.page.get_by_role("button", name=re.compile("bewerben|apply", re.I)).first

    def execute(self) -> dict:
        result = super().execute()
        if getattr(self, "_captcha_blocked", False):
            result["status"] = WorkflowState.REVIEW_REQUIRED.name
            result.setdefault("telemetry", {})["diagnosis_json"] = (
                "SuccessFactors login is CAPTCHA-gated for this returning account; "
                "cannot proceed automatically."
            )
        return result
