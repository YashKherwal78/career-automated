import { createFileRoute, Link, Outlet, useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { CompanyLogo } from "../../components/dashboard/CompanyLogo";
import { BackgroundApplyButton } from "../../components/dashboard/BackgroundApplyButton";
import { JobDetailContent, type ApplyStatus } from "../../components/dashboard/JobDetailModal";
import { DsDropzone } from "../../components/ds/Dropzone";
import { DsModal, DsModalCloseButton } from "../../components/ds/Modal";
import { isExtensionInstalled } from "../../lib/extensionBridge";
import { Trie } from "../../lib/trie";
import { Search, MapPin, ArrowUpDown, UploadCloud } from "lucide-react";
import { Job, JobScreenshotUploadResult } from "../../lib/services";

export const Route = createFileRoute("/dashboard/jobs")({
  validateSearch: (search: Record<string, unknown>) => ({
    select: (search.select as string) || undefined,
  }),
  component: JobsPage,
});

// Providers sourced from external job boards rather than a company's own
// ATS -- used only to label a row "External".
const JOB_BOARD_PROVIDERS = new Set(["linkedin", "google_jobs", "wellfound", "indeed"]);

function formatExperience(min?: number | null, max?: number | null): string {
  if (min == null && max == null) return "Not specified";
  if (min != null && max != null && max !== min) return `${min}–${max} yrs`;
  if (min != null) return `${min}+ yrs`;
  return `Up to ${max} yrs`;
}

function formatSalaryShort(job: Job): string {
  if (job.salary_min && job.salary_max) {
    return `₹${(job.salary_min / 100000).toFixed(1)}L - ₹${(job.salary_max / 100000).toFixed(1)}L`;
  }
  return "Competitive";
}

function matchPercent(job: Job): number | null {
  if (job.intent_score != null) return Math.round(job.intent_score * 100);
  if (job.job_score) return job.job_score;
  return null;
}

function matchTone(pct: number) {
  if (pct >= 85) return { bg: "rgba(107,143,94,0.16)", fg: "#4E6E42" };
  if (pct >= 70) return { bg: "rgba(217,164,65,0.18)", fg: "#8A6414" };
  return { bg: "var(--ds-cream-300)", fg: "var(--ds-ink-500)" };
}

// The shared app LoadingSkeleton renders bg-white/80 bars, which read as
// nearly invisible against this page's light cream background -- if a
// request ever hangs, that looks identical to "nothing rendered at all".
// This page uses its own clearly-tinted skeleton instead, specifically so
// "still loading" is never confusable with "broken/blank" again.
function JobsListSkeleton() {
  return (
    <div className="glass-card rounded-3xl border border-white/50 bg-white/40 shadow-sm p-4 space-y-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 animate-pulse">
          <div style={{ width: 30, height: 30, borderRadius: 8, background: "var(--ds-cream-300)" }} />
          <div className="flex-1 space-y-1.5">
            <div style={{ height: 10, width: "40%", borderRadius: 4, background: "var(--ds-cream-300)" }} />
            <div style={{ height: 8, width: "60%", borderRadius: 4, background: "var(--ds-cream-300)" }} />
          </div>
          <div style={{ width: 44, height: 20, borderRadius: 999, background: "var(--ds-cream-300)" }} />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------
// Upload Job — screenshot a job post, we extract company/role/apply link.
// Extraction-only. Its own modal, opened from a header button -- reads
// and writes only local `uploads` state, never touches the jobs
// list/selection state below.
// ---------------------------------------------------------------------
type UploadEntry = { id: string; fileName: string; state: "processing" | "done" | "error"; result?: JobScreenshotUploadResult };

function UploadJobModal({ onClose }: { onClose: () => void }) {
  const { jobService } = useDashboard();
  const [uploads, setUploads] = useState<UploadEntry[]>([]);

  const handleFile = async (file: File) => {
    const id = `${Date.now()}-${file.name}`;
    setUploads((prev) => [{ id, fileName: file.name, state: "processing" as const }, ...prev].slice(0, 6));
    try {
      const result = await jobService.uploadJobScreenshot(file);
      setUploads((prev) =>
        prev.map((u) => (u.id === id ? { ...u, state: result.success ? "done" : "error", result } : u)),
      );
    } catch (e) {
      setUploads((prev) =>
        prev.map((u) =>
          u.id === id
            ? { ...u, state: "error", result: { success: false, message: e instanceof Error ? e.message : "Upload failed." } }
            : u,
        ),
      );
    }
  };

  return (
    <DsModal onClose={onClose} maxWidth={520}>
      <div className="p-5 md:p-6 space-y-4" style={{ position: "relative" }}>
        <DsModalCloseButton onClose={onClose} />
        <div className="flex items-start gap-3 md:gap-4" style={{ paddingRight: 28 }}>
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{ width: 40, height: 40, borderRadius: "var(--ds-radius-lg)", background: "var(--ds-brand-orange-tint-08)", color: "var(--ds-brand-orange-text)" }}
          >
            <UploadCloud size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <div
              className="uppercase font-bold"
              style={{ fontSize: 11, letterSpacing: 0.6, color: "var(--ds-brand-orange-text)", marginBottom: 3 }}
            >
              Upload job
            </div>
            <h2 className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: 16, marginBottom: 3 }}>
              Saw a role on LinkedIn? Screenshot it.
            </h2>
            <p style={{ margin: 0, fontSize: 13, color: "var(--ds-ink-500)" }}>
              Drop a screenshot of any job post — we'll pull out the company, role, and how to apply, and
              add it here so you can review it like any other match.
            </p>
          </div>
        </div>

        {uploads.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {uploads.map((u) => (
              <span
                key={u.id}
                className="inline-flex items-center gap-1.5"
                style={{
                  fontSize: 11.5, color: "var(--ds-ink-600)", background: "var(--ds-cream-100)",
                  border: "1px solid var(--ds-border-hairline)", borderRadius: "var(--ds-radius-pill)",
                  padding: "5px 10px 5px 6px", maxWidth: "100%",
                }}
              >
                <span
                  style={{
                    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                    background: u.state === "processing" ? "var(--ds-amber-500)" : u.state === "done" ? "#6B8F5E" : "#C24E22",
                  }}
                />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {u.state === "processing" && `${u.fileName} · extracting…`}
                  {u.state === "done" && u.result?.success && `${u.result.company} — ${u.result.role} · extracted ✓`}
                  {u.state === "error" && (u.result?.message || "Couldn't read this screenshot")}
                </span>
              </span>
            ))}
          </div>
        )}

        <DsDropzone
          label="Drop a job screenshot"
          hint="or click to browse"
          filetypes={["PNG", "JPG", "WEBP"]}
          accept=".png,.jpg,.jpeg,.webp"
          onFile={handleFile}
        />
      </div>
    </DsModal>
  );
}

function JobsPage() {
  const { jobService } = useDashboard();
  const searchParams = useSearch({ from: "/dashboard/jobs" });
  const navigate = useNavigate();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [titleTrie, setTitleTrie] = useState<Trie | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const [roleFilter, setRoleFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [remoteFilter, setRemoteFilter] = useState("");
  const [sortField, setSortField] = useState<"intent_score" | "posted_at">("intent_score");
  const [applyMode, setApplyMode] = useState<"automatic" | "assisted">("automatic");
  const [hasExtension, setHasExtension] = useState<boolean | undefined>(undefined);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Desktop split-view selection + per-job apply state -- local, not
  // route-driven, since the detail pane is always on screen rather than an
  // overlay a URL can point at. Mobile still navigates to
  // /dashboard/jobs/$jobId (the Outlet below renders the existing
  // full-screen modal there) -- a split pane has no room on a phone.
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [queuedMap, setQueuedMap] = useState<Record<string, boolean>>({});
  const [applyStatusMap, setApplyStatusMap] = useState<Record<string, ApplyStatus | undefined>>({});

  useEffect(() => {
    jobService
      .getAutoApplyPolicy()
      .then((p) => setApplyMode(p.apply_mode))
      .catch(() => {});
    isExtensionInstalled().then(setHasExtension);
    jobService
      .getTitleSuggestions()
      .then((titles) => setTitleTrie(Trie.fromTitles(titles)))
      .catch(() => {});
  }, [jobService]);

  useEffect(() => {
    const handle = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(handle);
  }, [searchInput]);

  useEffect(() => {
    if (!titleTrie || !searchInput.trim()) {
      setSuggestions([]);
      return;
    }
    setSuggestions(titleTrie.suggest(searchInput));
  }, [titleTrie, searchInput]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const ROLE_OPTIONS = [
    { label: "All Roles", value: "" },
    { label: "AI Engineer", value: "AI Engineer" },
    { label: "ML Engineer", value: "Machine Learning Engineer" },
    { label: "Software Engineer", value: "Software Engineer" },
    { label: "Software Developer", value: "Software Developer" },
    { label: "Data Scientist", value: "Data Scientist" },
    { label: "Associate Product Manager", value: "Associate Product Manager" },
  ];

  const loadData = async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const filters = {
        q: search || undefined,
        title: roleFilter || undefined,
        location: locationFilter || undefined,
        remote_type: remoteFilter || undefined,
        sort_by: sortField === "intent_score" ? "score" : "newest",
      };
      const data = await jobService.getJobs(filters);
      setJobs(data);
      setLoadError(null);
      setSelectedJobId((current) => {
        if (current && data.some((j) => j.job_id === current)) return current;
        return data[0]?.job_id ?? null;
      });
    } catch (e) {
      console.error(e);
      setLoadError(e instanceof Error ? e.message : "Couldn't load jobs.");
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);
  }, [search, roleFilter, locationFilter, remoteFilter, sortField]);

  useEffect(() => {
    const interval = setInterval(() => {
      loadData(false);
    }, 30000);
    return () => clearInterval(interval);
  }, [search, roleFilter, locationFilter, remoteFilter, sortField]);

  useEffect(() => {
    if (searchParams.select) {
      navigate({ to: `/dashboard/jobs/${searchParams.select}`, replace: true });
    }
  }, [searchParams.select, navigate]);

  const selectedJob = jobs.find((j) => j.job_id === selectedJobId) || null;

  const handleToggleQueue = async (job: Job) => {
    if (queuedMap[job.job_id]) return;
    setQueuedMap((m) => ({ ...m, [job.job_id]: true }));
    setApplyStatusMap((m) => ({ ...m, [job.job_id]: { state: "applying" } }));
    try {
      const result = await jobService.applyToJob(job.job_id);
      if (result.really_submitted) {
        setApplyStatusMap((m) => ({ ...m, [job.job_id]: { state: "applied" } }));
      } else if (result.status === "REVIEW_REQUIRED") {
        setApplyStatusMap((m) => ({
          ...m,
          [job.job_id]: { state: "review_required", message: result.failure_reason || "Needs your review before it can be submitted." },
        }));
      } else {
        setApplyStatusMap((m) => ({
          ...m,
          [job.job_id]: { state: "failed", message: result.failure_reason || "Couldn't complete this application." },
        }));
      }
    } catch (e) {
      setApplyStatusMap((m) => ({ ...m, [job.job_id]: { state: "failed", message: "Something went wrong — try again." } }));
    }
  };

  return (
    <div className="p-4 md:p-8 space-y-5 md:space-y-6 relative min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Jobs</h1>
        <button
          type="button"
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 font-semibold"
          style={{
            padding: "9px 16px", borderRadius: "var(--ds-radius-lg)",
            border: "1px solid var(--ds-border-medium)", background: "var(--ds-surface-card)",
            color: "var(--ds-ink-700)", fontSize: 13,
          }}
        >
          <UploadCloud size={16} style={{ color: "var(--ds-brand-orange-text)" }} />
          Upload job
        </button>
      </div>

      {showUploadModal && <UploadJobModal onClose={() => setShowUploadModal(false)} />}

      {/* Filters Bar */}
      <div className="glass-card rounded-2xl p-4 border border-white/50 bg-white/40 shadow-sm flex flex-wrap items-center gap-4 text-xs">
        <div className="relative flex-1 min-w-[200px]" ref={searchBoxRef}>
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-3.5 w-3.5 text-ink-soft" />
          </span>
          <input
            type="text"
            placeholder="Search title or company..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            className="w-full pl-9 pr-4 py-2 sm:py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:border-[color:var(--peach-deep)] transition-colors"
          />
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl bg-white border border-white/60 shadow-lg z-20 overflow-hidden">
              {suggestions.map((title) => (
                <button
                  key={title}
                  type="button"
                  onClick={() => {
                    setSearchInput(title);
                    setSearch(title);
                    setShowSuggestions(false);
                  }}
                  className="w-full text-left px-3.5 py-2 text-xs text-ink hover:bg-[color:var(--peach-light)]/30 transition-colors"
                >
                  {title}
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="flex-1 sm:flex-none min-w-[130px] sm:min-w-0 px-3 py-2 sm:py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none text-ink-soft focus:border-[color:var(--peach-deep)] cursor-pointer"
        >
          {ROLE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <div className="relative flex-1 sm:flex-none min-w-[130px] sm:min-w-0">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MapPin className="h-3.5 w-3.5 text-ink-soft" />
          </span>
          <input
            type="text"
            placeholder="Location — India, Remote, US…"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            className="pl-9 pr-4 py-2 sm:py-1.5 w-full sm:w-52 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:border-[color:var(--peach-deep)] transition-colors"
          />
        </div>

        <select
          value={remoteFilter}
          onChange={(e) => setRemoteFilter(e.target.value)}
          className="flex-1 sm:flex-none min-w-[130px] sm:min-w-0 px-3 py-2 sm:py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none text-ink-soft focus:border-[color:var(--peach-deep)] cursor-pointer"
        >
          <option value="">Remote Type</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">Onsite</option>
        </select>

        <button
          onClick={() => setSortField(sortField === "intent_score" ? "posted_at" : "intent_score")}
          className="flex-1 sm:flex-none flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 sm:py-1.5 rounded-xl border border-white/60 bg-white/50 text-ink-soft hover:bg-white/80 transition-colors"
        >
          <ArrowUpDown className="h-3.5 w-3.5" />
          <span>Sort: {sortField === "intent_score" ? "Intent Match" : "Date Posted"}</span>
        </button>
      </div>

      {loading ? (
        <JobsListSkeleton />
      ) : loadError ? (
        <div className="text-center py-12 glass-card rounded-3xl p-6 border border-white/50 bg-white/40">
          <p className="text-xs" style={{ color: "#C0392B" }}>Couldn't load jobs: {loadError}</p>
          <button
            type="button"
            onClick={() => loadData(true)}
            className="mt-3 font-semibold"
            style={{ fontSize: 12.5, color: "var(--ds-accent-primary)" }}
          >
            Try again
          </button>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-3xl p-6 border border-white/50 bg-white/40">
          <p className="text-xs text-ink-soft">No jobs matched your filter criteria.</p>
        </div>
      ) : (
        <>
          {/* Desktop/tablet: split view -- compact list on the left, full
              detail always visible on the right. No overlay, so the detail
              pane gets real width instead of a fixed-width modal. */}
          <div className="hidden md:grid gap-4" style={{ gridTemplateColumns: "340px 1fr", alignItems: "start" }}>
            <div
              className="glass-card rounded-3xl border border-white/50 bg-white/40 shadow-sm overflow-y-auto"
              style={{ maxHeight: "calc(100vh - 320px)" }}
            >
              <div
                className="uppercase font-bold"
                style={{ padding: "14px 16px 10px", fontSize: 11, letterSpacing: 0.5, color: "var(--ds-ink-400)" }}
              >
                {jobs.length} open roles
              </div>
              {jobs.map((job, i) => {
                const pct = matchPercent(job);
                const tone = pct != null ? matchTone(pct) : null;
                const isSelected = job.job_id === selectedJobId;
                return (
                  <div
                    key={job.job_id}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedJobId(job.job_id)}
                    onKeyDown={(e) => e.key === "Enter" && setSelectedJobId(job.job_id)}
                    className="cursor-pointer transition-colors"
                    style={{
                      padding: "13px 16px",
                      borderTop: i === 0 ? "none" : "1px solid var(--ds-border-hairline)",
                      background: isSelected ? "var(--ds-brand-orange-tint-08)" : "transparent",
                      borderLeft: isSelected ? "3px solid var(--ds-accent-primary)" : "3px solid transparent",
                    }}
                  >
                    <div className="flex items-center gap-2" style={{ marginBottom: 6 }}>
                      <CompanyLogo name={job.canonical_name} domain={job.company_domain} size={22} radius={6} fontSize={9.5} />
                      <span className="font-semibold truncate" style={{ fontSize: 12.5, color: "var(--ds-ink-900)", flex: 1, minWidth: 0 }}>
                        {job.canonical_name}
                      </span>
                      {pct != null && (
                        <span
                          className="font-semibold flex-shrink-0"
                          style={{ fontSize: 10.5, padding: "2px 7px", borderRadius: "var(--ds-radius-pill)", background: tone!.bg, color: tone!.fg }}
                        >
                          {pct}%
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--ds-ink-800)", marginBottom: 3 }}>{job.title}</div>
                    <div className="flex gap-1.5" style={{ fontSize: 11, color: "var(--ds-ink-450)" }}>
                      <span>{job.location || "Remote"}</span>
                      <span>·</span>
                      <span className="capitalize">{job.remote || "Onsite"}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="glass-card rounded-3xl border border-white/50 bg-white/40 shadow-sm">
              {selectedJob ? (
                <JobDetailContent
                  job={selectedJob}
                  queued={!!queuedMap[selectedJob.job_id]}
                  applyStatus={applyStatusMap[selectedJob.job_id]}
                  onToggleQueue={() => handleToggleQueue(selectedJob)}
                />
              ) : (
                <div className="p-8 text-center text-xs text-ink-soft">Select a role to see details.</div>
              )}
            </div>
          </div>

          {/* Mobile: same compact-row visual language as the desktop list.
              Tapping opens the full-screen detail route -- no room for a
              split pane on a phone. */}
          <div className="md:hidden glass-card rounded-3xl border border-white/50 bg-white/40 shadow-sm overflow-hidden">
            {jobs.map((job, i) => {
              const pct = matchPercent(job);
              const tone = pct != null ? matchTone(pct) : null;
              return (
                <div
                  key={job.job_id}
                  style={{ padding: "14px 16px", borderTop: i === 0 ? "none" : "1px solid var(--ds-border-hairline)" }}
                >
                  <div className="flex items-center gap-2.5">
                    <CompanyLogo name={job.canonical_name} domain={job.company_domain} size={30} radius={8} fontSize={12} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold truncate" style={{ fontSize: 13, color: "var(--ds-ink-900)" }}>
                          {job.canonical_name}
                        </span>
                        {JOB_BOARD_PROVIDERS.has((job.provider || "").toLowerCase()) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-100 flex-shrink-0">EXTERNAL</span>
                        )}
                      </div>
                      <div className="truncate" style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>{job.title}</div>
                    </div>
                    {pct != null && (
                      <span
                        className="font-semibold flex-shrink-0"
                        style={{ fontSize: 11, padding: "3px 9px", borderRadius: "var(--ds-radius-pill)", background: tone!.bg, color: tone!.fg }}
                      >
                        {pct}%
                      </span>
                    )}
                  </div>

                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1" style={{ fontSize: 11.5, color: "var(--ds-ink-450)" }}>
                    <span>{job.location || "Remote"}</span>
                    <span className="capitalize">{job.remote || "Onsite"}</span>
                    <span>{formatExperience(job.experience_min, job.experience_max)}</span>
                    <span>{formatSalaryShort(job)}</span>
                  </div>

                  <div className="mt-3 flex items-center gap-1.5">
                    {applyMode === "assisted" && job.apply_url && (
                      <BackgroundApplyButton
                        jobId={job.job_id}
                        applyUrl={job.apply_url}
                        hasExtension={!!hasExtension}
                      />
                    )}
                    <Link
                      to={`/dashboard/jobs/${job.job_id}`}
                      className="flex-1 text-center font-semibold"
                      style={{
                        padding: "10px 14px", borderRadius: "var(--ds-radius-lg)",
                        background: "var(--ds-accent-primary)", color: "var(--ds-text-on-brand)", fontSize: 13,
                      }}
                    >
                      View Details
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Mobile full-screen detail, injected via Outlet */}
      <Outlet />
    </div>
  );
}
