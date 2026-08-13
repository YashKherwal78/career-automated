import { useEffect, useRef, useState } from "react";
import {
  startBackgroundApply,
  getBackgroundApplyStatus,
  focusApplyWindow,
  type BackgroundApplyStatus,
} from "../../lib/extensionBridge";

// Renders as a plain "open in a new tab" link when the extension isn't
// installed (unchanged behavior -- the pre-extension fallback) -- when it
// is, this drives the minimized-window flow: fills the application out of
// sight, then swaps to a "Review & Submit" action that brings the real
// browser window (not a screenshot) to the front for the user's own
// CAPTCHA-solving and final click.
export function BackgroundApplyButton({
  jobId,
  applyUrl,
  hasExtension,
}: {
  jobId: string;
  applyUrl: string;
  hasExtension: boolean;
}) {
  const [status, setStatus] = useState<BackgroundApplyStatus["status"]>("none");
  const [filled, setFilled] = useState<{ filled?: number; total?: number }>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const poll = (id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const s = await getBackgroundApplyStatus(id);
      setStatus(s.status);
      setFilled({ filled: s.filled, total: s.total });
      if (s.status === "ready" || s.status === "error" || s.status === "closed") {
        if (pollRef.current) clearInterval(pollRef.current);
      }
    }, 1500);
  };

  const handleStart = async () => {
    setStatus("filling");
    const started = await startBackgroundApply(jobId, applyUrl);
    if (!started) {
      setStatus("error");
      return;
    }
    poll(jobId);
  };

  const handleReview = async () => {
    await focusApplyWindow(jobId);
  };

  const baseStyle: React.CSSProperties = {
    padding: "6px 12px",
    fontSize: 12,
    borderRadius: "var(--ds-radius-md, 10px)",
    whiteSpace: "nowrap",
    cursor: "pointer",
    border: "1px solid var(--peach-deep, #E27448)",
    color: "var(--peach-deep, #E27448)",
    background: "transparent",
    fontWeight: 500,
  };

  if (!hasExtension) {
    return (
      <a
        href={`${applyUrl}?_careerautomated_autofill=1`}
        target="_blank"
        rel="noopener noreferrer"
        className="px-3 py-1.5 text-xs rounded-xl border border-[color:var(--peach-deep)] text-[color:var(--peach-deep)] font-medium whitespace-nowrap"
      >
        Open & Autofill
      </a>
    );
  }

  if (status === "none" || status === "closed") {
    return (
      <button type="button" onClick={handleStart} style={baseStyle}>
        {status === "closed" ? "Retry — Open & Autofill" : "Open & Autofill"}
      </button>
    );
  }

  if (status === "filling") {
    return (
      <button type="button" disabled style={{ ...baseStyle, opacity: 0.7, cursor: "default" }}>
        Filling in background…
      </button>
    );
  }

  if (status === "error") {
    return (
      <button type="button" onClick={handleStart} style={{ ...baseStyle, borderColor: "#B4392C", color: "#B4392C" }}>
        Failed — retry
      </button>
    );
  }

  // ready
  return (
    <button
      type="button"
      onClick={handleReview}
      style={{ ...baseStyle, background: "var(--peach-deep, #E27448)", color: "#fff" }}
      title={filled.total ? `Filled ${filled.filled ?? 0}/${filled.total} fields` : undefined}
    >
      Review & Submit
    </button>
  );
}
