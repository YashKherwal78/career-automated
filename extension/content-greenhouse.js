// Runs in the user's own real Chrome on a real Greenhouse application page.
// Deliberately does NOT auto-submit or touch CAPTCHA widgets -- it fills
// what it can determine and leaves Submit (and any CAPTCHA) to the human at
// the keyboard, since that's the entire point of running here instead of on
// a server: this browser's fingerprint, IP, and presence are genuinely the
// user's, so a CAPTCHA is just something they solve inline like normal.
//
// v1 scope: text/textarea/native-<select> fields + resume upload. Radio and
// checkbox groups are skipped for now (harder to reliably label-match) --
// left for the user to fill by hand, same as before this extension existed.

(function () {
  const API_BASE = location.hostname === "boards.greenhouse.io" || location.hostname === "job-boards.greenhouse.io"
    ? "https://api.careerautomated.in/api/v1"
    : "https://api.careerautomated.in/api/v1";

  function setNativeValue(el, value) {
    const proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function getLabel(el) {
    if (el.id) {
      const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (label?.innerText?.trim()) return label.innerText.trim();
    }
    const closest = el.closest("label");
    if (closest?.innerText?.trim()) return closest.innerText.trim();
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
    // Greenhouse wraps most fields in a container with the question text
    // in a sibling/ancestor element -- walk up a few levels looking for it.
    let node = el.closest(".field, [class*='field']");
    if (node) {
      const labelNode = node.querySelector("label, .application-label, legend");
      if (labelNode?.innerText?.trim()) return labelNode.innerText.trim();
    }
    return el.placeholder || "";
  }

  function collectFields() {
    const form = document.querySelector("form") || document.body;
    const els = Array.from(form.querySelectorAll("input, textarea, select"));
    const fields = [];
    for (const el of els) {
      if (el.disabled || el.type === "hidden" || el.type === "submit" || el.type === "button") continue;
      if (el.type === "file") continue; // resume handled separately
      if (el.type === "checkbox" || el.type === "radio") continue; // v1 scope
      const label = getLabel(el);
      if (!label) continue;

      let field_type = "text";
      let options = null;
      if (el.tagName === "TEXTAREA") field_type = "textarea";
      if (el.tagName === "SELECT") {
        field_type = "dropdown";
        options = Array.from(el.options).map((o) => o.text.trim()).filter(Boolean);
      }
      fields.push({ el, label, field_type, options, placeholder: el.placeholder || "" });
    }
    return fields;
  }

  function fillSelect(el, answer) {
    const target = answer.trim().toLowerCase();
    let best = null;
    for (const opt of el.options) {
      const text = opt.text.trim().toLowerCase();
      if (text === target) {
        best = opt;
        break;
      }
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
    // "Job Application for <Title> at <Company>" is Greenhouse's usual
    // <title>; falls back to the page's visible heading if that ever
    // changes, since document.title is convention, not a contract.
    const titleText = document.title || "";
    const m = titleText.match(/Job Application for (.+?) at (.+)/i);
    if (m) return { jobTitle: m[1].trim(), company: m[2].trim() };
    const h1 = document.querySelector("h1")?.innerText?.trim() || "";
    return { jobTitle: h1, company: "" };
  }

  async function attachResume(jobTitle, token) {
    const fileInput = document.querySelector(
      "input[type=file][name*=resume], input[type=file][id*=resume], input[type=file]"
    );
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
      // Tells background.js "this background-apply window is ready" --
      // only meaningful when this run was launched by
      // startBackgroundApply() (minimized window), but harmless to send
      // otherwise since there's no session for background.js to update.
      chrome.runtime.sendMessage({ type: "AUTOFILL_STATUS", filled, total: fields.length }).catch(() => {});
    } catch (e) {
      console.error("CareerAutomated autofill error:", e);
      button.textContent = "Autofill failed — see console";
      chrome.runtime.sendMessage({ type: "AUTOFILL_STATUS", filled: 0, total: fields.length, error: String(e) }).catch(() => {});
    } finally {
      button.disabled = false;
    }
  }

  function injectButton() {
    if (document.getElementById("careerautomated-autofill-btn")) return;
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
  // Fires once (autoTriggered guard) since the MutationObserver below can
  // otherwise re-run it every time the SPA re-renders the form.
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
  // Greenhouse's form (React-rendered) can mount after this script first
  // runs -- same race the resume-upload wait already accounts for -- so
  // keep checking as the DOM changes instead of only trying once at load.
  const observer = new MutationObserver(() => {
    injectButton();
    checkAutoTrigger();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
