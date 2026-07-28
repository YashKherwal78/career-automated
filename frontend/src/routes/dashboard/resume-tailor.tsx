import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { API_BASE } from "../../lib/api";
import { ServiceRegistry } from "../../lib/services";

const searchSchema = z.object({
  jobId: z.string().optional(),
});

export const Route = createFileRoute("/dashboard/resume-tailor")({
  validateSearch: searchSchema,
  component: ResumeTailorPage,
});

const LOADING_LINES = [
  "Reading through what makes you a fit…",
  "Pulling out your strongest, most relevant work…",
  "Rewriting your resume around this role…",
  "Making sure it reads clearly to a real person…",
  "Sharpening the details that matter most…",
];

type GenPhase = "idle" | "generating" | "done" | "error";

function Spinner() {
  return (
    <div
      className="animate-spin rounded-full flex-shrink-0"
      style={{
        width: 16,
        height: 16,
        border: "2px solid rgba(255,255,255,0.4)",
        borderTopColor: "#fff",
      }}
    />
  );
}

function ResumeTailorPage() {
  const { jobId } = Route.useSearch();
  const { user, session } = useAuth();
  const [genPhase, setGenPhase] = useState<GenPhase>("idle");
  const [lineIndex, setLineIndex] = useState(0);
  const [tailoredTex, setTailoredTex] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => ServiceRegistry.getJobService().getJob(jobId as string),
    enabled: !!jobId,
  });

  useEffect(() => {
    if (genPhase !== "generating") return;
    const t = setInterval(() => setLineIndex((i) => (i + 1) % LOADING_LINES.length), 1100);
    return () => clearInterval(t);
  }, [genPhase]);

  const generateResume = async () => {
    if (!jobId || !user) return;
    setGenPhase("generating");
    setLineIndex(0);
    setErrorMessage("");
    try {
      const response = await fetch(`${API_BASE}/resume/tailor`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ candidate_id: user.id, job_id: jobId }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Tailoring failed");
      }
      const data = await response.json();
      setTailoredTex(data.tailored_tex);
      setGenPhase("done");
    } catch (err) {
      console.error(err);
      setErrorMessage(err instanceof Error ? err.message : "That didn't go through.");
      setGenPhase("error");
    }
  };

  const downloadResume = () => {
    if (!tailoredTex) return;
    const blob = new Blob([tailoredTex], { type: "text/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `resume_tailored_${jobId}.tex`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const baseBtnStyle: React.CSSProperties = {
    display: "block",
    width: "100%",
    boxSizing: "border-box",
    textAlign: "center",
    padding: 15,
    border: "none",
    borderRadius: "var(--ds-radius-md)",
    fontSize: 15,
    fontWeight: 700,
    fontFamily: "var(--ds-font-body)",
    cursor: "pointer",
  };

  return (
    <div
      className="flex items-center justify-center"
      style={{ minHeight: "100vh", padding: "clamp(32px,5vw,72px)" }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 640,
          background: "rgba(255,255,255,0.4)",
          backdropFilter: "blur(20px) saturate(160%)",
          border: "1px solid rgba(255,255,255,0.55)",
          borderRadius: "var(--ds-radius-2xl)",
          boxShadow: "var(--ds-shadow-card)",
          padding: "clamp(28px,4vw,40px)",
        }}
      >
        <div
          className="uppercase font-bold"
          style={{
            fontSize: 13,
            letterSpacing: "var(--ds-tracking-wide)",
            color: "var(--ds-brand-orange-text)",
            marginBottom: 12,
          }}
        >
          Tailoring
        </div>
        <h1
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: "clamp(26px,3vw,34px)", margin: "0 0 20px" }}
        >
          Hand us the job. We'll handle the fit.
        </h1>

        {!jobId ? (
          <div
            style={{
              background: "rgba(139,123,192,0.08)",
              border: "1px solid rgba(139,123,192,0.2)",
              borderRadius: "var(--ds-radius-lg)",
              padding: "14px 18px",
              fontSize: 13.5,
              color: "var(--ds-ink-600)",
              lineHeight: 1.6,
            }}
          >
            Pick a role from your{" "}
            <Link to="/dashboard" style={{ fontWeight: 600 }}>
              dashboard
            </Link>{" "}
            and choose "Tailor for this role" — we'll tailor your resume against that job's real
            requirements.
          </div>
        ) : (
          <>
            <div
              style={{
                background: "rgba(255,255,255,0.55)",
                border: "1px solid rgba(255,255,255,0.6)",
                borderRadius: "var(--ds-radius-xl)",
                padding: 22,
                marginBottom: 14,
              }}
            >
              <div style={{ fontSize: "var(--ds-text-md)", fontWeight: 600, marginBottom: 4 }}>
                {job ? `${job.title} at ${job.canonical_name}` : "Loading role…"}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ds-ink-400)" }}>
                Tailoring against this role's stored requirements — nothing saves until you
                download.
              </div>
            </div>

            {genPhase === "idle" && (
              <button
                type="button"
                onClick={generateResume}
                className="transition-transform active:scale-[0.98]"
                style={{
                  ...baseBtnStyle,
                  background: "var(--ds-accent-primary)",
                  color: "var(--ds-text-on-brand)",
                  boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
                }}
              >
                Tailor my resume
              </button>
            )}
            {genPhase === "generating" && (
              <div
                className="flex items-center justify-center gap-2.5"
                style={{
                  ...baseBtnStyle,
                  background: "var(--ds-accent-primary)",
                  color: "var(--ds-text-on-brand)",
                }}
              >
                <Spinner />
                {LOADING_LINES[lineIndex]}
              </div>
            )}
            {genPhase === "done" && (
              <button
                type="button"
                onClick={downloadResume}
                className="transition-transform active:scale-[0.98]"
                style={{ ...baseBtnStyle, background: "var(--ds-ink-900)", color: "#FFFDFA" }}
              >
                ↓ Download your resume
              </button>
            )}
            {genPhase === "error" && (
              <div
                style={{
                  background: "rgba(180,57,44,0.06)",
                  border: "1px solid rgba(180,57,44,0.2)",
                  borderRadius: "var(--ds-radius-lg)",
                  padding: "16px 18px",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: "var(--ds-ink-800)",
                    marginBottom: 4,
                  }}
                >
                  That didn't go through.
                </div>
                <div style={{ fontSize: 13, color: "var(--ds-ink-500)", marginBottom: 12 }}>
                  Your work is safe — nothing was lost. Let's try that again.
                  {errorMessage ? ` (${errorMessage})` : ""}
                </div>
                <button
                  type="button"
                  onClick={() => setGenPhase("idle")}
                  style={{
                    padding: "10px 20px",
                    borderRadius: "var(--ds-radius-md)",
                    border: "1px solid var(--ds-border-medium)",
                    background: "transparent",
                    color: "var(--ds-ink-700)",
                    fontSize: 13.5,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Try again
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
