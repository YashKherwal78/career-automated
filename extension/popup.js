const statusEl = document.getElementById("status");

function render({ apiToken }) {
  if (apiToken) {
    statusEl.textContent = "Connected ✓";
    statusEl.className = "connected";
  } else {
    statusEl.textContent = "Not connected — open careerautomated.in and log in";
    statusEl.className = "disconnected";
  }
}

chrome.storage.local.get(["apiToken"], render);

document.getElementById("saveToken").addEventListener("click", () => {
  const token = document.getElementById("tokenInput").value.trim();
  if (!token) return;
  chrome.storage.local.set({ apiToken: token }, () => render({ apiToken: token }));
});
