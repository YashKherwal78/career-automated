import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { API_BASE } from "../../lib/api";
import { ServiceRegistry } from "../../lib/services";
import { UpgradeModal } from "../../components/dashboard/UpgradeModal";

const searchSchema = z.object({
  jobId: z.string().optional(),
});

export const Route = createFileRoute("/dashboard/cover-letter")({
  validateSearch: searchSchema,
  component: CoverLetterPage,
});

const LOADING_LINES = [
  "Reading the role…",
  "Finding the strongest angle from your background…",
  "Writing it in your voice, not a template's…",
  "Cutting anything that sounds like filler…",
];

type GenPhase = "idle" | "generating" | "done" | "error" | "paywalled";

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

interface GeneratedCoverLetter {
  id: string;
  job_id: string;
  company_name: string;
  job_title: string;
  cover_letter_text: string;
  word_count: number | null;
  created_at: string;
}

function useGeneratedCoverLetters() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["generated-cover-letters"],
    queryFn: async (): Promise<GeneratedCoverLetter[]> => {
      const res = await fetch(`${API_BASE}/applications/cover-letters`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (!res.ok) throw new Error("Failed to load generated cover letters");
      const data = await res.json();
      return data.items || [];
    },
    enabled: !!session,
  });
}

function useBaseResume() {
  const { session } = useAuth();
  return useQuery({
    queryKey: ["base-resume"],
    meta: { persist: true },
    queryFn: async (): Promise<{ exists: boolean }> => {
      const res = await fetch(`${API_BASE}/candidate/base-resume`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (res.status === 404) return { exists: false };
      if (!res.ok) throw new Error("Failed to load base resume");
      return { exists: true };
    },
    enabled: !!session,
  });
}

function CoverLetterPage() {
  const { jobId } = Route.useSearch();
  const { user, session } = useAuth();
  const [genPhase, setGenPhase] = useState<GenPhase>("idle");
  const [lineIndex, setLineIndex] = useState(0);
  const [letterText, setLetterText] = useState<string | null>(null);
  const [letterTex, setLetterTex] = useState<string | null>(null);
  const [wordCount, setWordCount] = useState(0);
  const [pdfState, setPdfState] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [copied, setCopied] = useState(false);
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
  const { data: generatedLetters = [] } = useGeneratedCoverLetters();
  const [expandedGeneratedId, setExpandedGeneratedId] = useState<string | null>(null);

  useEffect(() => {
    if (genPhase !== "generating") return;
    const t = setInterval(() => setLineIndex((i) => (i + 1) % LOADING_LINES.length), 1100);
    return () => clearInterval(t);
  }, [genPhase]);

  const canGenerate = !!jobId || jobDescription.trim().length > 0;

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

  const generateCoverLetter = async () => {
    if (!user || !canGenerate) return;
    setGenPhase("generating");
    setLineIndex(0);
    setErrorMessage("");
    try {
      const response = await fetch(`${API_BASE}/resume/cover-letter`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify(
          jobId
            ? { candidate_id: user.id, job_id: jobId, company_name: companyName || undefined, role_title: roleTitle || undefined }
            : {
                candidate_id: user.id,
                job_description: jobDescription,
                company_name: companyName || undefined,
                role_title: roleTitle || undefined,
              },
        ),
      });
      if (response.status === 402) {
        setGenPhase("paywalled");
        return;
      }
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Generation failed");
      }
      const data = await response.json();
      setLetterText(data.cover_letter_text);
      setLetterTex(data.cover_letter_tex || null);
      setWordCount(data.word_count);
      setGenPhase("done");
    } catch (err) {
      console.error(err);
      setErrorMessage(err instanceof Error ? err.message : "That didn't go through.");
      setGenPhase("error");
    }
  };

  const copyToClipboard = async () => {
    if (!letterText) return;
    try {
      await navigator.clipboard.writeText(letterText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Clipboard write failed:", err);
    }
  };

  const downloadAsText = () => {
    if (!letterText) return;
    const blob = new Blob([letterText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cover_letter_${jobId || "custom"}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAsTex = () => {
    if (!letterTex) return;
    const blob = new Blob([letterTex], { type: "application/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cover_letter_${jobId || "custom"}.tex`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAsPdf = async () => {
    if (!letterTex) return;
    setPdfState("loading");
    try {
      const response = await fetch(`${API_BASE}/resume/cover-letter/pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ cover_letter_tex: letterTex }),
      });
      if (!response.ok) {
        // PDF compilation failing must never take away the text/LaTeX
        // outputs that already succeeded -- surface a clear error here,
        // don't touch genPhase (letter stays fully usable via copy/.txt/.tex).
        setPdfState("error");
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Cover Letter.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setPdfState("idle");
    } catch (err) {
      console.error("Cover letter PDF download failed:", err);
      setPdfState("error");
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

  const inputStyle: React.CSSProperties = {
    width: "100%",
    boxSizing: "border-box",
    padding: "11px 14px",
    borderRadius: "var(--ds-radius-md)",
    border: "1px solid var(--ds-border-medium)",
    fontSize: 13.5,
    fontFamily: "var(--ds-font-body)",
    background: "var(--ds-surface-card)",
    color: "var(--ds-text-primary)",
  };

  if (genPhase === "paywalled") {
    return <UpgradeModal onClose={() => setGenPhase("idle")} />;
  }

  return (
    <div
      className="flex flex-col items-center"
      style={{ minHeight: "100vh", padding: "clamp(32px,5vw,72px)", gap: 24 }}
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
          Cover Letter
        </div>
        <h1
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: "clamp(26px,3vw,34px)", margin: "0 0 20px" }}
        >
          A short, specific letter — not a form one.
        </h1>

        {!baseResumeLoading && !baseResume?.exists && (
          <div
            className="flex items-center justify-between"
            style={{
              background: "rgba(180,57,44,0.06)",
              border: "1px solid rgba(180,57,44,0.2)",
              borderRadius: "var(--ds-radius-lg)",
              padding: "14px 18px",
              marginBottom: 14,
              fontSize: 13,
              color: "var(--ds-ink-600)",
            }}
          >
            <span>Cover letters draw on your base resume — build one first.</span>
            <Link
              to="/dashboard/resume"
              style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-accent-primary)", flexShrink: 0, marginLeft: 12 }}
            >
              Build it →
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
              Written against this role's stored requirements.
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "rgba(255,255,255,0.55)",
              border: "1px solid rgba(255,255,255,0.6)",
              borderRadius: "var(--ds-radius-xl)",
              padding: 22,
              marginBottom: 14,
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
            <div className="flex flex-col sm:flex-row" style={{ gap: 8, marginBottom: 10 }}>
              <input
                type="text"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && extractFromLink()}
                placeholder="Paste a job link (LinkedIn, Greenhouse, Lever, Ashby…)"
                className="flex-1 bg-transparent outline-none w-full sm:w-auto"
                style={{
                  fontSize: 13.5,
                  color: "var(--ds-text-primary)",
                  border: "1px solid var(--ds-border-default)",
                  borderRadius: "var(--ds-radius-md)",
                  padding: "10px 12px",
                  boxSizing: "border-box",
                  minWidth: 0,
                }}
              />
              <button
                type="button"
                onClick={extractFromLink}
                disabled={extracting || !linkedinUrl.trim()}
                className="flex-shrink-0 w-full sm:w-auto"
                style={{
                  padding: "10px 16px",
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
              placeholder="Paste the job description here."
              rows={5}
              className="w-full bg-transparent outline-none resize-none"
              style={{
                fontSize: 13.5,
                lineHeight: 1.6,
                color: "var(--ds-text-primary)",
                border: "1px solid var(--ds-border-default)",
                borderRadius: "var(--ds-radius-md)",
                padding: 12,
                boxSizing: "border-box",
                marginBottom: 10,
              }}
            />
            <div className="flex gap-2.5">
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Company (optional)"
                style={inputStyle}
              />
              <input
                type="text"
                value={roleTitle}
                onChange={(e) => setRoleTitle(e.target.value)}
                placeholder="Role title (optional)"
                style={inputStyle}
              />
            </div>
          </div>
        )}

        {genPhase === "idle" && (
          <button
            type="button"
            onClick={generateCoverLetter}
            disabled={!canGenerate || !baseResume?.exists}
            className="transition-transform active:scale-[0.98]"
            style={{
              ...baseBtnStyle,
              background:
                canGenerate && baseResume?.exists ? "var(--ds-accent-primary)" : "var(--ds-cream-300)",
              color: canGenerate && baseResume?.exists ? "var(--ds-text-on-brand)" : "var(--ds-ink-400)",
              boxShadow:
                canGenerate && baseResume?.exists ? "0 10px 22px -8px rgba(226,116,72,0.45)" : "none",
              cursor: canGenerate && baseResume?.exists ? "pointer" : "default",
            }}
          >
            Write my cover letter
          </button>
        )}
        {genPhase === "generating" && (
          <div
            className="flex items-center justify-center gap-2.5"
            style={{ ...baseBtnStyle, background: "var(--ds-accent-primary)", color: "var(--ds-text-on-brand)" }}
          >
            <Spinner />
            {LOADING_LINES[lineIndex]}
          </div>
        )}
        {genPhase === "done" && letterText && (
          <>
            <div
              style={{
                background: "rgba(255,255,255,0.65)",
                border: "1px solid var(--ds-border-medium)",
                borderRadius: "var(--ds-radius-lg)",
                padding: 18,
                marginBottom: 14,
                fontSize: 13.5,
                lineHeight: 1.7,
                color: "var(--ds-text-primary)",
                whiteSpace: "pre-wrap",
                maxHeight: 360,
                overflowY: "auto",
              }}
            >
              {letterText}
            </div>
            <div style={{ fontSize: 11.5, color: "var(--ds-ink-400)", marginBottom: 12, textAlign: "right" }}>
              {wordCount} words
            </div>

            {/* Primary: PDF -- the actual submission-ready document. */}
            <button
              type="button"
              onClick={downloadAsPdf}
              disabled={!letterTex || pdfState === "loading"}
              className="transition-transform active:scale-[0.98]"
              style={{
                ...baseBtnStyle,
                width: "100%",
                marginBottom: 10,
                background: letterTex ? "var(--ds-accent-primary)" : "var(--ds-cream-300)",
                color: letterTex ? "var(--ds-text-on-brand)" : "var(--ds-ink-400)",
                cursor: letterTex && pdfState !== "loading" ? "pointer" : "default",
              }}
            >
              {pdfState === "loading" ? "Compiling PDF…" : "↓ Download Cover Letter PDF"}
            </button>
            {pdfState === "error" && (
              <div style={{ fontSize: 12, color: "#B4392C", marginBottom: 10, textAlign: "center" }}>
                PDF compilation failed — the text and LaTeX below still work. Try again, or use those instead.
              </div>
            )}

            {/* Secondary: LaTeX source, and copy. */}
            <div className="flex gap-2.5">
              <button
                type="button"
                onClick={copyToClipboard}
                className="flex-1 transition-transform active:scale-[0.98]"
                style={{
                  ...baseBtnStyle,
                  background: "transparent",
                  border: "1px solid var(--ds-border-medium)",
                  color: "var(--ds-ink-700)",
                }}
              >
                {copied ? "Copied ✓" : "Copy text"}
              </button>
              <button
                type="button"
                onClick={downloadAsTex}
                disabled={!letterTex}
                className="flex-1 transition-transform active:scale-[0.98]"
                style={{
                  ...baseBtnStyle,
                  background: "transparent",
                  border: "1px solid var(--ds-border-medium)",
                  color: letterTex ? "var(--ds-ink-700)" : "var(--ds-ink-400)",
                  cursor: letterTex ? "pointer" : "default",
                }}
              >
                Download .tex
              </button>
              <button
                type="button"
                onClick={downloadAsText}
                className="flex-1 transition-transform active:scale-[0.98]"
                style={{ ...baseBtnStyle, background: "var(--ds-ink-900)", color: "#FFFDFA" }}
              >
                ↓ .txt
              </button>
            </div>
            <button
              type="button"
              onClick={() => setGenPhase("idle")}
              style={{
                display: "block",
                margin: "14px auto 0",
                background: "none",
                border: "none",
                fontSize: 12.5,
                color: "var(--ds-ink-450)",
                cursor: "pointer",
              }}
            >
              Write another
            </button>
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
            <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-800)", marginBottom: 4 }}>
              That didn't go through.
            </div>
            <div style={{ fontSize: 13, color: "var(--ds-ink-500)", marginBottom: 12 }}>
              Nothing was lost. Let's try that again.
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

      {generatedLetters.length > 0 && (
        <div style={{ width: "100%", maxWidth: 640 }}>
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 12,
              letterSpacing: "var(--ds-tracking-wide)",
              color: "var(--ds-ink-400)",
              marginBottom: 10,
            }}
          >
            Generated for your applications ({generatedLetters.length})
          </div>
          <div className="flex flex-col" style={{ gap: 10 }}>
            {generatedLetters.map((letter) => {
              const isExpanded = expandedGeneratedId === letter.id;
              return (
                <div
                  key={letter.id}
                  style={{
                    background: "rgba(255,255,255,0.55)",
                    border: "1px solid rgba(255,255,255,0.6)",
                    borderRadius: "var(--ds-radius-lg)",
                    padding: "14px 16px",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setExpandedGeneratedId(isExpanded ? null : letter.id)}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div style={{ fontSize: 13.5, fontWeight: 600 }}>
                        {letter.job_title}
                        <span style={{ color: "var(--ds-ink-450)", fontWeight: 500 }}> · {letter.company_name}</span>
                      </div>
                      <span style={{ fontSize: 11.5, color: "var(--ds-ink-400)", flexShrink: 0, marginLeft: 10 }}>
                        {isExpanded ? "Hide ↑" : "View →"}
                      </span>
                    </div>
                  </button>
                  {isExpanded && (
                    <div
                      style={{
                        marginTop: 12,
                        fontSize: 13,
                        lineHeight: 1.7,
                        color: "var(--ds-text-primary)",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {letter.cover_letter_text}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
