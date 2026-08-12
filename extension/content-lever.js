// Runs on a real Lever application page in the user's own browser. Same
// design as content-greenhouse.js: fill what we can, never touch submit or
// a CAPTCHA widget (Lever's anti-bot here is hCaptcha, not reCAPTCHA), leave
// the human to review and finish.
//
// v1 scope: text/textarea/native-<select> fields + resume upload — same
// scope limit as the Greenhouse script, for the same reason (radio/checkbox
// groups need more careful label-matching than justified for a first pass).
// DOM structure mirrors backend/src/applications/handlers/lever.py's own
// extractor (.application-question / .application-label / native <select>)
// since that's already proven against real Lever forms.

(function () {
  const API_BASE = "https://api.careerautomated.in/api/v1";

  function setNativeValue(el, value) {
    const proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  const SKIP_LABELS = new Set(["full name", "name", "email", "phone", "resume/cv", "resume", "cv", "current location", "location"]);

  function collectFields() {
    const containers = Array.from(document.querySelectorAll(".application-question"));
    const fields = [];
    for (const container of containers) {
      if (container.offsetParent === null) continue; // not visible
      const labelEl = container.querySelector(".application-label .text, .application-label");
      if (!labelEl) continue;
      const rawLabel = (labelEl.innerText.split("\n")[0] || "").trim();
      const label = rawLabel.replace("✱", "").trim();
      if (!label || SKIP_LABELS.has(label.toLowerCase())) continue;

      const select = container.querySelector("select");
      const textarea = container.querySelector("textarea");
      const textInput = container.querySelector(
        'input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="file"])',
      );

      let el, field_type, options = null, placeholder = "";
      if (select) {
        el = select;
        field_type = "dropdown";
        options = Array.from(select.options).map((o) => o.text.trim()).filter((t) => t && !t.toLowerCase().includes("select"));
      } else if (textarea) {
        el = textarea;
        field_type = "textarea";
        placeholder = textarea.placeholder || "";
      } else if (textInput) {
        el = textInput;
        field_type = "text";
        placeholder = textInput.placeholder || "";
      } else {
        continue; // radio/checkbox group -- v1 scope skip
      }
      fields.push({ el, label, field_type, options, placeholder });
    }
    return fields;
  }

  function fillSelect(el, answer) {
    const target = answer.trim().toLowerCase();
    let best = null;
    for (const opt of el.options) {
      const text = opt.text.trim().toLowerCase();
      if (text === target) { best = opt; break; }
      if (!best && text.includes(target)) best = opt;
    }
    if (best) {
      el.value = best.value;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }
    return false;
  }

  async function getToken() {
    const { apiToken } = await chrome.storage.local.get(["apiToken"]);
    return apiToken || null;
  }

  function jobTitleAndCompany() {
    // Lever job pages: <title> is usually "<Company> - <Title>" and the
    // posting header has a distinct company/title split -- fall back to
    // document.title parsing since that's stable across tenants.
    const h2 = document.querySelector(".posting-headline h2")?.innerText?.trim() || "";
    const company = document.querySelector(".main-header-logo img")?.getAttribute("alt")?.trim() || "";
    if (h2) return { jobTitle: h2, company };
    const titleText = document.title || "";
    const parts = titleText.split(" - ");
    return { jobTitle: parts[parts.length - 1] || titleText, company: parts[0] || "" };
  }

  async function attachResume(jobTitle, token) {
    const fileInput = document.querySelector('input[type="file"][name="resume"], #resume-upload-input, input[type="file"]');
    if (!fileInput) return "no file input found on this page";
    const res = await fetch(`${API_BASE}/applications/resume-for-job?job_title=${encodeURIComponent(jobTitle)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return `resume fetch failed (${res.status})`;
    const blob = await res.blob();
    const file = new File([blob], "resume.pdf", { type: "application/pdf" });
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    return null;
  }

  async function autofill(button) {
    const token = await getToken();
    if (!token) {
      alert("CareerAutomated: not connected. Open careerautomated.in, log in, then retry.");
      return;
    }
    button.textContent = "Autofilling…";
    button.disabled = true;

    const { jobTitle, company } = jobTitleAndCompany();
    const fields = collectFields();

    try {
      const resumeError = await attachResume(jobTitle, token);
      if (resumeError) console.warn("CareerAutomated: resume not attached —", resumeError);

      const res = await fetch(`${API_BASE}/applications/autofill`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          job_title: jobTitle,
          company_name: company,
          questions: fields.map((f) => ({
            question: f.label,
            field_type: f.field_type,
            placeholder: f.placeholder,
            options: f.options,
            label_text: f.label,
            required: false,
          })),
        }),
      });
      if (!res.ok) throw new Error(`autofill request failed (${res.status})`);
      const { answers } = await res.json();

      let filled = 0;
      fields.forEach((f, i) => {
        const answer = answers[i];
        if (!answer) return;
        if (f.el.tagName === "SELECT") {
          if (fillSelect(f.el, answer)) filled++;
        } else {
          setNativeValue(f.el, answer);
          filled++;
        }
      });

      button.textContent = `Filled ${filled}/${fields.length} — review & submit`;
    } catch (e) {
      console.error("CareerAutomated autofill error:", e);
      button.textContent = "Autofill failed — see console";
    } finally {
      button.disabled = false;
    }
  }

  function injectButton() {
    if (document.getElementById("careerautomated-autofill-btn")) return;
    if (!document.querySelector(".application-question")) return; // not on the form yet
    const button = document.createElement("button");
    button.id = "careerautomated-autofill-btn";
    button.textContent = "Autofill (CareerAutomated)";
    button.style.cssText =
      "position:fixed;bottom:20px;right:20px;z-index:999999;padding:10px 16px;" +
      "background:#111;color:#fff;border:none;border-radius:8px;font-size:13px;" +
      "font-family:-apple-system,system-ui,sans-serif;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);";
    button.addEventListener("click", () => autofill(button));
    document.body.appendChild(button);
  }

  // Lets the dashboard's "Open & Autofill" link (for a REVIEW_REQUIRED
  // application) skip the extra manual click -- open the real job page
  // with ?_careerautomated_autofill=1 and this fires the same autofill()
  // the button does, automatically, the moment the form actually exists.
  let autoTriggered = false;
  function checkAutoTrigger() {
    if (autoTriggered) return;
    if (new URLSearchParams(location.search).get("_careerautomated_autofill") !== "1") return;
    const btn = document.getElementById("careerautomated-autofill-btn");
    if (!btn || btn.disabled) return;
    autoTriggered = true;
    autofill(btn);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectButton);
  } else {
    injectButton();
  }
  checkAutoTrigger();
  // Lever's apply form can appear after a client-side navigation (job page
  // -> "Apply for this job" click) without a full page load, so the initial
  // injectButton() call may run before .application-question exists yet.
  const observer = new MutationObserver(() => {
    injectButton();
    checkAutoTrigger();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
