// Runs on careerautomated.in. Supabase's JS client stores the session under
// a localStorage key shaped like "sb-<project-ref>-auth-token" -- rather
// than hardcode the project ref (and have this break silently if it ever
// rotates), scan for any key matching that shape and pull access_token out
// of it. Lets the extension "just work" once you're logged into the
// dashboard, no manual token copy-paste step.
function findSupabaseAccessToken() {
  for (const key of Object.keys(localStorage)) {
    if (key.startsWith("sb-") && key.endsWith("-auth-token")) {
      try {
        const parsed = JSON.parse(localStorage.getItem(key));
        if (parsed?.access_token) return parsed.access_token;
      } catch (e) {
        // not JSON / not the session shape we expect -- skip it
      }
    }
  }
  return null;
}

const apiBase = location.hostname.includes("localhost")
  ? "http://localhost:8000/api/v1"
  : "https://api.careerautomated.in/api/v1";

const token = findSupabaseAccessToken();
if (token) {
  chrome.runtime.sendMessage({ type: "CAREERAUTOMATED_TOKEN", token, apiBase });
}
