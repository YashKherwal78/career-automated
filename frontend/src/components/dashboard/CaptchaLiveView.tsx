import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ServiceRegistry } from "../../lib/services";
import { DsButton } from "../ds/Button";

// Mounted once at the dashboard-layout level (not per-page) so it's visible
// no matter which page you're on when a background application hits a
// CAPTCHA -- these are time-boxed (10 min server-side timeout) so it needs
// to be findable immediately, not tucked into one specific page.
export function CaptchaLiveView() {
  const queryClient = useQueryClient();
  const { data: active } = useQuery({
    queryKey: ["captcha-active"],
    queryFn: () => ServiceRegistry.getCaptchaService().getActive(),
    refetchInterval: 4000,
  });

  const sessionId = active?.active ? active.session_id : null;
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const prevUrlRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!sessionId) {
      if (pollRef.current) clearInterval(pollRef.current);
      if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current);
      setScreenshotUrl(null);
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const url = await ServiceRegistry.getCaptchaService().getScreenshot(sessionId);
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current);
        prevUrlRef.current = url;
        setScreenshotUrl(url);
      } catch (e) {
        console.error("Captcha screenshot poll failed:", e);
      }
    };
    poll();
    pollRef.current = setInterval(poll, 1000);
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [sessionId]);

  if (!active?.active || !sessionId) return null;

  const isFinalReview = active.reason === "final_review";

  const handleImageClick = async (e: React.MouseEvent<HTMLImageElement>) => {
    if (!imgRef.current || busy) return;
    const rect = imgRef.current.getBoundingClientRect();
    // Screenshot is taken at the real page's viewport size (1280x800, see
    // browser_launcher.py) but displayed scaled to fit this box -- convert
    // click position in the scaled image back to real page coordinates.
    const scaleX = 1280 / rect.width;
    const scaleY = 800 / rect.height;
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    try {
      await ServiceRegistry.getCaptchaService().click(sessionId, x, y);
    } catch (err) {
      console.error("Captcha click relay failed:", err);
    }
  };

  const finish = async (action: "resolved" | "skip") => {
    setBusy(true);
    try {
      if (action === "resolved") await ServiceRegistry.getCaptchaService().resolved(sessionId);
      else await ServiceRegistry.getCaptchaService().skip(sessionId);
      queryClient.invalidateQueries({ queryKey: ["captcha-active"] });
    } catch (e) {
      console.error(`Captcha ${action} signal failed:`, e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2000,
        background: "rgba(20,16,12,0.55)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          background: "var(--ds-surface-card, #fff)",
          borderRadius: "var(--ds-radius-xl)",
          padding: 24,
          maxWidth: 900,
          width: "100%",
          boxShadow: "0 30px 80px rgba(0,0,0,0.35)",
        }}
      >
        <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
          <div>
            <div className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: 17 }}>
              {isFinalReview ? "Ready for your final review" : "CAPTCHA needs you"}
            </div>
            <p style={{ fontSize: 13, color: "var(--ds-ink-500)", margin: "4px 0 0" }}>
              {isFinalReview
                ? "The application is fully filled in and ready to go. Take a look, and confirm to submit it."
                : "An application in progress hit a CAPTCHA — everything else is already filled in. Click on it below to solve it, then confirm."}
            </p>
          </div>
        </div>

        <div
          style={{
            position: "relative",
            width: "100%",
            aspectRatio: "1280 / 800",
            background: "#111",
            borderRadius: "var(--ds-radius-lg)",
            overflow: "hidden",
            marginBottom: 16,
          }}
        >
          {screenshotUrl ? (
            <img
              ref={imgRef}
              src={screenshotUrl}
              alt="Live application form"
              onClick={handleImageClick}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
                cursor: isFinalReview ? "default" : "crosshair",
              }}
            />
          ) : (
            <div
              className="flex items-center justify-center"
              style={{ width: "100%", height: "100%", color: "#888", fontSize: 13 }}
            >
              Loading live view…
            </div>
          )}
        </div>

        <div className="flex items-center justify-between flex-wrap gap-3">
          <p style={{ fontSize: 11.5, color: "var(--ds-ink-450)", margin: 0 }}>
            {isFinalReview
              ? "Click on the image above if you need to fix anything. Updates about once a second."
              : "Click directly on the CAPTCHA in the image above to interact with it. Updates about once a second."}
          </p>
          <div className="flex gap-2.5">
            <DsButton variant="outline" size="md" disabled={busy} onClick={() => finish("skip")}>
              {isFinalReview ? "Don't submit — send to review instead" : "Skip — send to review instead"}
            </DsButton>
            <DsButton variant="primary" size="md" disabled={busy} onClick={() => finish("resolved")}>
              {isFinalReview ? "Looks good — submit it" : "I solved it — continue"}
            </DsButton>
          </div>
        </div>
      </div>
    </div>
  );
}
