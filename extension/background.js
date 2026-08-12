// Relays the auth token found by bridge-auth.js (running on
// careerautomated.in) into chrome.storage.local, where content-greenhouse.js
// and popup.js both read it from. A service worker (not the content script
// itself) owns storage writes so token updates are visible immediately to
// every tab, not just the one that found it.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "CAREERAUTOMATED_TOKEN" && message.token) {
    chrome.storage.local.set({ apiToken: message.token, apiBase: message.apiBase || null });
    sendResponse({ ok: true });
  }
  return true;
});
