import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ServiceRegistry, type Job } from "../../lib/services";
import { useAuth } from "../../lib/auth";
import { API_BASE } from "../../lib/api";
import { getDisplayName } from "../../lib/displayName";
import { DsChip } from "../../components/ds/Chip";
import { DsInput } from "../../components/ds/Input";
import { DsButton } from "../../components/ds/Button";
import { JobDetailModal } from "../../components/dashboard/JobDetailModal";
import { CareerPreferencesModal } from "../../components/dashboard/CareerPreferencesModal";
import { UpgradeModal } from "../../components/dashboard/UpgradeModal";
import { CompanyLogo } from "../../components/dashboard/CompanyLogo";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardHome,
});

const LOCATIONS = ["All", "Remote", "Bangalore", "Hyderabad", "Mumbai"];
const PAGE_SIZE = 10;
const FREE_TIER_AUTO_APPLY_CAP = 5;

function timeGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Morning";
  if (h < 18) return "Afternoon";
  return "Evening";
}

function DashboardHome() {
  const { profile, session } = useAuth();
  const firstName = getDisplayName(profile?.full_name, profile?.email, "there").split(" ")[0];

  const {
    data: jobs = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["jobs", "dashboard"],
    queryFn: () => ServiceRegistry.getJobService().getJobs({ sort_by: "score", page_size: 100 }),
  });

  const { data: hasProfileData } = useQuery({
    queryKey: ["candidate-profile-completeness"],
    queryFn: async (): Promise<boolean> => {
      const res = await fetch(`${API_BASE}/candidate/profile`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (!res.ok) return false;
      const data = await res.json();
      const p = data.profile_data || {};
      const hasSkills = Object.values(p.skills || {}).some(
        (arr: any) => Array.isArray(arr) && arr.length > 0
      );
      return (p.experience || []).length > 0 || hasSkills;
    },
    enabled: !!session,
  });
  const showResumeNudge = hasProfileData === false;

  const [locationFilter, setLocationFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  // Auto-apply is frontend-only for this pass — no backend policy/queue endpoints exist yet.
  const [autoApplyOn, setAutoApplyOn] = useState(false);
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [queuedJobIds, setQueuedJobIds] = useState<string[]>([]);

  const filtered = useMemo(() => {
    return jobs.filter((job) => {
      const matchLocation =
        locationFilter === "All" ||
        (locationFilter === "Remote"
          ? (job.location || "").toLowerCase().includes("remote") ||
            (job.remote || "").toLowerCase().includes("remote")
          : (job.location || "").toLowerCase().includes(locationFilter.toLowerCase()));
      const matchQuery =
        !searchQuery ||
        (job.title || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        (job.canonical_name || "").toLowerCase().includes(searchQuery.toLowerCase());
      return matchLocation && matchQuery;
    });
  }, [jobs, locationFilter, searchQuery]);

  const topJobs = jobs.slice(0, 15);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageResults = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const handleToggleAutoApply = () => {
    if (!autoApplyOn) {
      setShowPreferencesModal(true);
      return;
    }
    setAutoApplyOn(false);
  };

  const handleSavePreferences = () => {
    // Career preferences are frontend-only for this pass — no backend policy endpoint exists yet.
    setShowPreferencesModal(false);
    setAutoApplyOn(true);
  };

  const handleQueueJob = (jobId: string) => {
    if (queuedJobIds.includes(jobId)) {
      setQueuedJobIds((ids) => ids.filter((id) => id !== jobId));
      return;
    }
    if (queuedJobIds.length >= FREE_TIER_AUTO_APPLY_CAP) {
      setShowUpgradeModal(true);
      return;
    }
    setQueuedJobIds((ids) => [...ids, jobId]);
  };

  return (
    <div>
      <div style={{ padding: "40px clamp(24px,4vw,56px) 8px" }}>
        <div
          style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-450)", marginBottom: 12 }}
        >
          {timeGreeting()}, {firstName}.
        </div>
        <h1
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: "clamp(26px,3.6vw,46px)", margin: "0 0 12px" }}
        >
          {showResumeNudge ? "Let's get you matched." : "You're all caught up."}
        </h1>
        <p style={{ fontSize: 16, color: "var(--ds-ink-500)", margin: 0, maxWidth: 480 }}>
          {showResumeNudge
            ? "Add your resume — takes about two minutes — and we'll start finding roles that actually fit you."
            : "We'll let you know when something needs you."}
        </p>
      </div>

      <div style={{ padding: "24px clamp(24px,4vw,56px)" }}>
        <div
          className="flex items-center justify-between flex-wrap gap-3"
          style={{ marginBottom: 18 }}
        >
          <div className="flex items-center gap-3.5">
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 13,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-ink-400)",
              }}
            >
              Your jobs
            </div>
            <div
              className="font-semibold"
              style={{
                fontSize: 12,
                color: "var(--ds-ink-500)",
                background: "var(--ds-surface-tint)",
                padding: "4px 10px",
                borderRadius: "var(--ds-radius-pill)",
              }}
            >
              {queuedJobIds.length}/{FREE_TIER_AUTO_APPLY_CAP} in auto-apply queue
            </div>
          </div>
          {autoApplyOn ? (
            <div className="flex items-center gap-3">
              <span
                className="font-semibold"
                style={{ fontSize: 14, color: "var(--ds-sage-text)" }}
              >
                Auto Apply on ✓
              </span>
              <DsButton variant="outline" size="md" onClick={handleToggleAutoApply}>
                Pause
              </DsButton>
            </div>
          ) : (
            <DsButton variant="primary" size="md" onClick={handleToggleAutoApply}>
              Start Auto Apply
            </DsButton>
          )}
        </div>

        {showResumeNudge && (
          <div
            className="flex items-center justify-between flex-wrap gap-4"
            style={{
              background: "var(--ds-brand-orange-tint-08)",
              border: "1px solid rgba(255,255,255,0.6)",
              borderRadius: "var(--ds-radius-xl)",
              padding: "20px 24px",
              marginBottom: 18,
            }}
          >
            <div>
              <div
                className="font-[var(--ds-font-display)] font-semibold"
                style={{ fontSize: 16, marginBottom: 4 }}
              >
                Start your journey
              </div>
              <p style={{ fontSize: 13.5, color: "var(--ds-ink-500)", margin: 0, maxWidth: 440 }}>
                These are top jobs on the platform — not personalized yet.
              </p>
            </div>
            <div className="flex gap-2.5 flex-shrink-0">
              <DsButton asChild variant="primary" size="md">
                <Link to="/dashboard/resume">Upload resume</Link>
              </DsButton>
              <DsButton asChild variant="outline" size="md">
                <Link to="/dashboard/resume">Create new resume</Link>
              </DsButton>
            </div>
          </div>
        )}

        {isLoading ? (
          <div
            style={{
              padding: "40px 0",
              textAlign: "center",
              color: "var(--ds-ink-450)",
              fontSize: 13.5,
            }}
          >
            Loading your matches…
          </div>
        ) : error ? (
          <div
            style={{
              padding: "24px 0",
              textAlign: "center",
              color: "var(--ds-ink-500)",
              fontSize: 13.5,
            }}
          >
            Couldn't load your matches right now. Try refreshing in a moment.
          </div>
        ) : topJobs.length === 0 ? (
          <div
            style={{
              background: "rgba(255,255,255,0.55)",
              border: "1px solid rgba(255,255,255,0.6)",
              borderRadius: "var(--ds-radius-xl)",
              padding: "32px 28px",
              textAlign: "center",
            }}
          >
            <div
              className="font-[var(--ds-font-display)] font-semibold"
              style={{ fontSize: 17, marginBottom: 8 }}
            >
              We're already scanning for you.
            </div>
            <p
              style={{
                fontSize: 13.5,
                color: "var(--ds-ink-500)",
                lineHeight: 1.6,
                margin: "0 0 18px",
                maxWidth: 420,
                marginInline: "auto",
              }}
            >
              CareerAutomated is watching company career pages and job boards right now. As soon as
              something matches your profile, it'll show up here — ready to review.
            </p>
          </div>
        ) : (
          <div
            className="flex gap-3.5 overflow-x-auto pb-2 no-scrollbar"
            style={{ WebkitOverflowScrolling: "touch" }}
          >
            {topJobs.map((job, i) => (
              <button
                key={job.job_id}
                type="button"
                onClick={() => setSelectedJob(job)}
                className="text-left flex-shrink-0 transition-transform hover:-translate-y-0.5 glass-card"
                style={{
                  width: 220,
                  borderRadius: "var(--ds-radius-xl)",
                  padding: 18,
                }}
              >
                <div className="flex items-center gap-2" style={{ marginBottom: 14 }}>
                  <CompanyLogo name={job.canonical_name} domain={job.company_domain} size={24} radius={6} />
                  <div
                    className="whitespace-nowrap overflow-hidden text-ellipsis"
                    style={{ fontSize: 12, fontWeight: 600, color: "var(--ds-ink-500)" }}
                  >
                    {job.canonical_name}
                  </div>
                </div>
                <div
                  className="font-[var(--ds-font-display)] font-semibold"
                  style={{ fontSize: 17, lineHeight: 1.3, marginBottom: 14, minHeight: 44 }}
                >
                  {job.title}
                </div>
                <div className="flex items-center gap-1.5" style={{ marginBottom: 10 }}>
                  <span
                    className="font-bold"
                    style={{
                      fontSize: 11,
                      color: "var(--ds-ink-600)",
                      background: "var(--ds-surface-tint)",
                      padding: "2px 7px",
                      borderRadius: "var(--ds-radius-pill)",
                    }}
                  >
                    {showResumeNudge ? "Top pick" : `${job.job_score}% match`}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--ds-ink-400)" }}>{job.location}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: "24px clamp(24px,4vw,56px) 56px" }}>
        <div
          className="uppercase font-bold"
          style={{
            fontSize: 13,
            letterSpacing: "var(--ds-tracking-wide)",
            color: "var(--ds-ink-400)",
            marginBottom: 14,
          }}
        >
          Search jobs
        </div>
        <div className="flex flex-wrap gap-2.5" style={{ marginBottom: 16 }}>
          <div style={{ flex: "1 1 240px" }}>
            <DsInput
              placeholder="Search role or company…"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(0);
              }}
            />
          </div>
          {LOCATIONS.map((l) => (
            <DsChip
              key={l}
              label={l}
              active={locationFilter === l}
              onClick={() => {
                setLocationFilter(l);
                setPage(0);
              }}
            />
          ))}
        </div>

        {filtered.length === 0 ? (
          <div
            className="flex items-center justify-center text-center"
            style={{ padding: "40px 24px" }}
          >
            <div>
              <div
                className="font-[var(--ds-font-display)] font-semibold"
                style={{ fontSize: 15.5, marginBottom: 6 }}
              >
                No matches in this location yet.
              </div>
              <p
                style={{
                  fontSize: 13,
                  color: "var(--ds-ink-500)",
                  margin: "0 0 12px",
                  maxWidth: 320,
                }}
              >
                Try a broader location, or check back soon — new roles are added continuously.
              </p>
              <button
                type="button"
                onClick={() => setLocationFilter("All")}
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--ds-accent-primary)",
                  cursor: "pointer",
                }}
              >
                Show all locations
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="glass-card" style={{ borderRadius: "var(--ds-radius-lg)" }}>
              {pageResults.map((job) => (
                <div
                  key={job.job_id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedJob(job)}
                  onKeyDown={(e) => e.key === "Enter" && setSelectedJob(job)}
                  className="flex items-center gap-3 cursor-pointer hover:bg-white/50"
                  style={{ padding: "13px 16px", borderBottom: "1px solid rgba(255,255,255,0.5)" }}
                >
                  <CompanyLogo name={job.canonical_name} domain={job.company_domain} size={32} radius={8} fontSize={13} />
                  <div className="flex-1 min-w-0">
                    <div
                      className="whitespace-nowrap overflow-hidden text-ellipsis"
                      style={{ fontSize: "var(--ds-text-md)", fontWeight: 600 }}
                    >
                      {job.title}
                    </div>
                    <div
                      style={{ fontSize: "var(--ds-text-base)", color: "var(--ds-text-secondary)" }}
                    >
                      {job.canonical_name} · {job.location}
                    </div>
                  </div>
                  {!showResumeNudge && (
                    <div className="text-right flex-shrink-0">
                      <div style={{ fontSize: "var(--ds-text-sm)", fontWeight: 700 }}>
                        {job.job_score}%
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex items-center justify-between" style={{ marginTop: 12 }}>
              <div style={{ fontSize: 13, color: "var(--ds-ink-450)" }}>
                Page {page + 1} of {totalPages}
              </div>
              <div className="flex gap-2.5">
                <DsButton
                  variant="outline"
                  size="md"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Previous
                </DsButton>
                <DsButton
                  variant="outline"
                  size="md"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                >
                  Next
                </DsButton>
              </div>
            </div>
          </>
        )}
      </div>

      {selectedJob && (
        <JobDetailModal
          job={selectedJob}
          queued={queuedJobIds.includes(selectedJob.job_id)}
          onToggleQueue={() => handleQueueJob(selectedJob.job_id)}
          onClose={() => setSelectedJob(null)}
          showMatch={!showResumeNudge}
        />
      )}

      {showPreferencesModal && (
        <CareerPreferencesModal
          onSave={handleSavePreferences}
          onSkip={() => setShowPreferencesModal(false)}
        />
      )}

      {showUpgradeModal && <UpgradeModal onClose={() => setShowUpgradeModal(false)} />}
    </div>
  );
}
