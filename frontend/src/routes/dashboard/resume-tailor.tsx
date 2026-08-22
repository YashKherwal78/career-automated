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

function useBaseResume() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["base-resume"],
    meta: { persist: true },
    queryFn: async (): Promise<{ exists: boolean; pdfAvailable: boolean }> => {
      const res = await fetch(`${API_BASE}/candidate/base-resume`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (res.status === 404) return { exists: false, pdfAvailable: false };
      if (!res.ok) throw new Error("Failed to load base resume");
      const data = await res.json();
      return { exists: true, pdfAvailable: !!data.pdf_available };
    },
    enabled: !!session,
  });
}

function ResumeTailorPage() {
  const { jobId } = Route.useSearch();
  const { user, session } = useAuth();
  const [genPhase, setGenPhase] = useState<GenPhase>("idle");
  const [lineIndex, setLineIndex] = useState(0);
  const [tailoredTex, setTailoredTex] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState("");

  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    meta: { persist: true },
    queryFn: () => ServiceRegistry.getJobService().getJob(jobId as string),
    enabled: !!jobId,
  });

  const { data: baseResume, isLoading: baseResumeLoading } = useBaseResume();

  useEffect(() => {
    if (genPhase !== "generating") return;
    const t = setInterval(() => setLineIndex((i) => (i + 1) % LOADING_LINES.length), 1100);
    return () => clearInterval(t);
  }, [genPhase]);

  const extractFromLink = async () => {
    if (!linkedinUrl.trim()) return;
    setExtracting(true);
    setExtractError("");
    try {
      const response = await fetch(`${API_BASE}/resume/extract-from-link`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ url: linkedinUrl.trim() }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Couldn't read that link");
      }
      const data = await response.json();
      setJobDescription(data.job_description);
      setCompanyName(data.company_name || "");
      setRoleTitle(data.role_title || "");
      setLinkedinUrl("");
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : "Couldn't read that link");
    } finally {
      setExtracting(false);
    }
  };

  const generateResume = async () => {
    if (!user) return;
    if (!jobId && !jobDescription.trim()) return;
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
        body: JSON.stringify(
          jobId
            ? { candidate_id: user.id, job_id: jobId }
            : {
                candidate_id: user.id,
                job_description: jobDescription,
                company_name: companyName || undefined,
                role_title: roleTitle || undefined,
              },
        ),
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

  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  const downloadResume = async () => {
    if (!tailoredTex) return;
    setDownloadingPdf(true);
    setDownloadError("");
    try {
      const response = await fetch(`${API_BASE}/resume/tailor/pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ tailored_tex: tailoredTex }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Couldn't generate the PDF");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume_tailored_${jobId || "custom"}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setDownloadError(err instanceof Error ? err.message : "Couldn't generate the PDF");
    } finally {
      setDownloadingPdf(false);
    }
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

  const canGenerate = !!jobId || jobDescription.trim().length > 0;

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
        <div
          className="flex flex-col sm:flex-row sm:items-start sm:justify-between"
          style={{ marginBottom: 20, gap: 8 }}
        >
          <h1
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: "clamp(26px,3vw,34px)", margin: 0, maxWidth: 440 }}
          >
            Hand us the job. We'll handle the fit.
          </h1>
          <Link
            to="/dashboard/cover-letter"
            search={jobId ? { jobId } : {}}
            className="flex-shrink-0"
            style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ds-accent-primary)", marginTop: 8 }}
          >
            Need a cover letter too? →
          </Link>
        </div>

        {!jobId && (
          <div
            style={{
              background: "rgba(139,123,192,0.08)",
              border: "1px solid rgba(139,123,192,0.2)",
              borderRadius: "var(--ds-radius-lg)",
              padding: "14px 18px",
              marginBottom: 14,
              fontSize: 13,
              color: "var(--ds-ink-600)",
              lineHeight: 1.5,
            }}
          >
            First time here? Paste in a job description below and watch your resume reshape around
            it — nothing saves until you download.
          </div>
        )}

        {/* Your resume card */}
        {!baseResumeLoading && (
          <div
            className="flex flex-col sm:flex-row sm:items-center"
            style={{
              background: "rgba(255,255,255,0.55)",
              border: "1px solid rgba(255,255,255,0.6)",
              borderRadius: "var(--ds-radius-xl)",
              padding: 22,
              marginBottom: 14,
              gap: 14,
            }}
          >
            <div className="flex items-center" style={{ gap: 14, minWidth: 0 }}>
              <div
                className="flex items-center justify-center flex-shrink-0"
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: "var(--ds-radius-md)",
                  background: "var(--ds-brand-orange-tint-10)",
                }}
              >
                <div
                  className="relative"
                  style={{
                    width: 14,
                    height: 16,
                    borderRadius: 2,
                    border: "2px solid var(--ds-accent-primary)",
                  }}
                />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "var(--ds-text-md)", fontWeight: 600 }}>Your resume</div>
                <div style={{ fontSize: 12.5, color: "var(--ds-ink-400)" }}>
                  {baseResume?.exists ? "Base resume ready for tailoring" : "No base resume yet"}
                </div>
              </div>
            </div>
            <Link
              to="/dashboard/resume"
              className="flex-shrink-0 pl-[52px] sm:pl-0"
              style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-accent-primary)" }}
            >
              {baseResume?.exists ? "Use a different one" : "Build your base resume →"}
            </Link>
          </div>
        )}

        {jobId ? (
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
              Tailoring against this role's stored requirements — nothing saves until you download.
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "rgba(255,255,255,0.55)",
              border: "1px solid rgba(255,255,255,0.6)",
              borderRadius: "var(--ds-radius-xl)",
              padding: 22,
              marginBottom: 26,
            }}
          >
            <label
              className="uppercase font-bold"
              style={{
                display: "block",
                fontSize: 11.5,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-ink-400)",
                marginBottom: 8,
              }}
            >
              The job you're applying to
            </label>
            <div className="flex" style={{ gap: 8, marginBottom: 10 }}>
              <input
                type="text"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && extractFromLink()}
                placeholder="Paste a LinkedIn job link instead…"
                className="flex-1 bg-transparent outline-none"
                style={{
                  fontSize: 13.5,
                  color: "var(--ds-text-primary)",
                  border: "1px solid var(--ds-border-default)",
                  borderRadius: "var(--ds-radius-md)",
                  padding: "10px 12px",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={extractFromLink}
                disabled={extracting || !linkedinUrl.trim()}
                className="flex-shrink-0"
                style={{
                  padding: "0 16px",
                  borderRadius: "var(--ds-radius-md)",
                  border: "1px solid var(--ds-border-default)",
                  background: extracting ? "var(--ds-cream-300)" : "var(--ds-ink-900)",
                  color: extracting ? "var(--ds-ink-400)" : "#FFFDFA",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: extracting || !linkedinUrl.trim() ? "default" : "pointer",
                }}
              >
                {extracting ? "Reading…" : "Extract"}
              </button>
            </div>
            {extractError && (
              <div style={{ fontSize: 12.5, color: "var(--ds-accent-danger, #C4432B)", marginBottom: 10 }}>
                {extractError}
              </div>
            )}
            <div
              className="flex items-center"
              style={{ gap: 10, margin: "4px 0 10px", fontSize: 11.5, color: "var(--ds-ink-400)" }}
            >
              <div style={{ flex: 1, height: 1, background: "var(--ds-border-default)" }} />
              or paste it yourself
              <div style={{ flex: 1, height: 1, background: "var(--ds-border-default)" }} />
            </div>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the job description here — we'll take it from there."
              rows={6}
              className="w-full bg-transparent outline-none resize-none"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: "var(--ds-text-primary)",
                border: "1px solid var(--ds-border-default)",
                borderRadius: "var(--ds-radius-md)",
                padding: 12,
                boxSizing: "border-box",
              }}
            />
            {(companyName || roleTitle) && (
              <div style={{ fontSize: 12, color: "var(--ds-ink-400)", marginTop: 8 }}>
                Detected: {roleTitle || "Role"} {companyName ? `at ${companyName}` : ""}
              </div>
            )}
          </div>
        )}

        {genPhase === "idle" && (
          <button
            type="button"
            onClick={generateResume}
            disabled={!canGenerate || !baseResume?.exists}
            className="transition-transform active:scale-[0.98]"
            style={{
              ...baseBtnStyle,
              background:
                canGenerate && baseResume?.exists
                  ? "var(--ds-accent-primary)"
                  : "var(--ds-cream-300)",
              color:
                canGenerate && baseResume?.exists ? "var(--ds-text-on-brand)" : "var(--ds-ink-400)",
              boxShadow:
                canGenerate && baseResume?.exists
                  ? "0 10px 22px -8px rgba(226,116,72,0.45)"
                  : "none",
              cursor: canGenerate && baseResume?.exists ? "pointer" : "default",
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
          <>
            <button
              type="button"
              onClick={downloadResume}
              disabled={downloadingPdf}
              className="transition-transform active:scale-[0.98]"
              style={{
                ...baseBtnStyle,
                background: "var(--ds-ink-900)",
                color: "#FFFDFA",
                opacity: downloadingPdf ? 0.7 : 1,
                cursor: downloadingPdf ? "default" : "pointer",
              }}
            >
              {downloadingPdf ? "Generating PDF…" : "↓ Download your resume"}
            </button>
            {downloadError && (
              <p
                style={{
                  fontSize: 12.5,
                  color: "var(--ds-accent-danger, #C4432B)",
                  margin: "10px 0 0",
                  textAlign: "center",
                }}
              >
                {downloadError}
              </p>
            )}
          </>
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
      </div>
    </div>
  );
}
