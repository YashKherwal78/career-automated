// Relays the auth token found by bridge-auth.js (running on
// careerautomated.in) into chrome.storage.local, where content-greenhouse.js
// and popup.js both read it from. A service worker (not the content script
// itself) owns storage writes so token updates are visible immediately to
// every tab, not just the one that found it.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "CAREERAUTOMATED_TOKEN" && message.token) {
    chrome.storage.local.set({ apiToken: message.token, apiBase: message.apiBase || null });
    sendResponse({ ok: true });
    return true;
  }

  // Sent by a per-ATS content script (content-greenhouse.js etc.) once
  // autofill() finishes running inside a background-apply window -- this
  // is how the dashboard finds out "ready for you to review" instead of
  // polling the DOM itself (it can't; the window is minimized/unfocused
  // and the dashboard is a different page entirely).
  if (message?.type === "AUTOFILL_STATUS" && sender.tab) {
    const jobId = windowIdToJobId.get(sender.tab.windowId);
    if (jobId) {
      const session = backgroundApplySessions.get(jobId);
      if (session) {
        session.status = message.error ? "error" : "ready";
        session.filled = message.filled ?? session.filled;
        session.total = message.total ?? session.total;
        session.error = message.error || null;
      }
    }
    sendResponse({ ok: true });
    return true;
  }

  return false;
});

// ── Background-apply: minimized-window autofill ────────────────────────────
// Dashboard asks the extension to open a job application in an unfocused,
// minimized window and fill it there -- out of the user's way -- then the
// dashboard shows a single "Review & Submit" action once it's done, which
// brings that same real window (not a screenshot, not a copy) to the front
// for the user to solve any CAPTCHA and click Submit themselves.
//
// jobId -> { windowId, tabId, status, filled, total, error }
const backgroundApplySessions = new Map();
// windowId -> jobId, so AUTOFILL_STATUS messages (which only carry a
// sender.tab, not a jobId) can be routed back to the right session.
const windowIdToJobId = new Map();

chrome.windows.onRemoved.addListener((windowId) => {
  const jobId = windowIdToJobId.get(windowId);
  if (!jobId) return;
  windowIdToJobId.delete(windowId);
  const session = backgroundApplySessions.get(jobId);
  if (session && session.status !== "submitted") {
    session.status = "closed";
  }
});

async function startBackgroundApply(jobId, applyUrl) {
  const existing = backgroundApplySessions.get(jobId);
  if (existing && existing.status !== "closed" && existing.status !== "error") {
    return { started: true, alreadyRunning: true };
  }

  const url = `${applyUrl}${applyUrl.includes("?") ? "&" : "?"}_careerautomated_autofill=1&_careerautomated_bg=1`;
  const win = await chrome.windows.create({
    url,
    type: "popup",
    state: "minimized",
    focused: false,
    width: 1280,
    height: 900,
  });
  const tabId = win.tabs && win.tabs[0] ? win.tabs[0].id : null;

  backgroundApplySessions.set(jobId, {
    windowId: win.id,
    tabId,
    status: "filling",
    filled: 0,
    total: 0,
    error: null,
    createdAt: Date.now(),
  });
  windowIdToJobId.set(win.id, jobId);

  return { started: true, alreadyRunning: false };
}

function getApplyStatus(jobId) {
  const session = backgroundApplySessions.get(jobId);
  if (!session) return { status: "none" };
  return {
    status: session.status,
    filled: session.filled,
    total: session.total,
    error: session.error,
  };
}

async function focusApplyWindow(jobId) {
  const session = backgroundApplySessions.get(jobId);
  if (!session) return { ok: false, error: "No session for this job" };
  try {
    await chrome.windows.update(session.windowId, { state: "normal", focused: true });
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

async function cancelBackgroundApply(jobId) {
  const session = backgroundApplySessions.get(jobId);
  if (!session) return { ok: true };
  try {
    await chrome.windows.remove(session.windowId);
  } catch (e) {
    // Window may already be closed -- fine either way.
  }
  windowIdToJobId.delete(session.windowId);
  backgroundApplySessions.delete(jobId);
  return { ok: true };
}

// Only careerautomated.in / localhost:5173 can reach this (see manifest.json
// externally_connectable) -- the regular dashboard page talks to the
// extension directly, no content-script relay needed for this flow.
chrome.runtime.onMessageExternal.addListener((message, _sender, sendResponse) => {
  (async () => {
    switch (message?.type) {
      case "PING":
        sendResponse({ ok: true, version: chrome.runtime.getManifest().version });
        break;
      case "START_BACKGROUND_APPLY":
        sendResponse(await startBackgroundApply(message.jobId, message.applyUrl));
        break;
      case "GET_APPLY_STATUS":
        sendResponse(getApplyStatus(message.jobId));
        break;
      case "FOCUS_APPLY_WINDOW":
        sendResponse(await focusApplyWindow(message.jobId));
        break;
      case "CANCEL_APPLY":
        sendResponse(await cancelBackgroundApply(message.jobId));
        break;
      default:
        sendResponse({ ok: false, error: "Unknown message type" });
    }
  })();
  return true; // keep the message channel open for the async response
});
