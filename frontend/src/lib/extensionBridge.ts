// Talks directly to the CareerAutomated browser extension via
// chrome.runtime.sendMessage(extensionId, ...) -- allowed because the
// extension declares this site under "externally_connectable" in its
// manifest.json, so no content-script relay is needed for this flow
// (unlike the auth-token bridge, which does go through one).
//
// Every call resolves to `null` if the extension isn't installed, isn't
// reachable, or the browser doesn't support extensions at all (Safari on
// iOS, Chrome on Android) -- callers should always have a graceful
// fallback for that case, never assume the extension is present.

const EXTENSION_ID = "knhjidhnhmjdgiamklelcniaojfchanl";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const chrome: any;

function hasChromeRuntime(): boolean {
  return typeof chrome !== "undefined" && !!chrome.runtime && !!chrome.runtime.sendMessage;
}

function sendToExtension<T>(message: Record<string, unknown>): Promise<T | null> {
  return new Promise((resolve) => {
    if (!hasChromeRuntime()) {
      resolve(null);
      return;
    }
    try {
      chrome.runtime.sendMessage(EXTENSION_ID, message, (response: T) => {
        // chrome.runtime.lastError is how failed sendMessage calls report
        // errors (no extension installed, wrong ID, etc.) -- reading it is
        // required to avoid an "Unchecked runtime.lastError" console spam,
        // and its presence is exactly the "extension not there" signal.
        if (chrome.runtime.lastError) {
          resolve(null);
          return;
        }
        resolve(response ?? null);
      });
    } catch {
      resolve(null);
    }
  });
}

export async function isExtensionInstalled(): Promise<boolean> {
  const res = await sendToExtension<{ ok: boolean }>({ type: "PING" });
  return !!res?.ok;
}

export interface BackgroundApplyStatus {
  status: "none" | "filling" | "ready" | "error" | "closed";
  filled?: number;
  total?: number;
  error?: string | null;
}

export async function startBackgroundApply(jobId: string, applyUrl: string): Promise<boolean> {
  const res = await sendToExtension<{ started: boolean }>({
    type: "START_BACKGROUND_APPLY",
    jobId,
    applyUrl,
  });
  return !!res?.started;
}

export async function getBackgroundApplyStatus(jobId: string): Promise<BackgroundApplyStatus> {
  const res = await sendToExtension<BackgroundApplyStatus>({ type: "GET_APPLY_STATUS", jobId });
  return res ?? { status: "none" };
}

export async function focusApplyWindow(jobId: string): Promise<boolean> {
  const res = await sendToExtension<{ ok: boolean }>({ type: "FOCUS_APPLY_WINDOW", jobId });
  return !!res?.ok;
}

export async function cancelBackgroundApply(jobId: string): Promise<void> {
  await sendToExtension<{ ok: boolean }>({ type: "CANCEL_APPLY", jobId });
}
