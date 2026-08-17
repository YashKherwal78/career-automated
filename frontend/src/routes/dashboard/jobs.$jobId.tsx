import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { JobDetailModal } from "../../components/dashboard/JobDetailModal";
import { AlertCircle } from "lucide-react";
import { Job } from "../../lib/services";

export const Route = createFileRoute("/dashboard/jobs/$jobId")({
  component: JobDetailsRoute,
});

type ApplyStatus = {
  state: "applying" | "applied" | "review_required" | "failed";
  message?: string;
};

function JobDetailsRoute() {
  const { jobId } = Route.useParams();
  const { jobService } = useDashboard();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queued, setQueued] = useState(false);
  const [applyStatus, setApplyStatus] = useState<ApplyStatus | undefined>(undefined);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await jobService.getJob(jobId);
        setJob(data);
      } catch (e) {
        setError("Failed to load job details.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [jobId, jobService]);

  const handleClose = () => {
    navigate({ to: "/dashboard/jobs", replace: true });
  };

  // Same "add to auto-apply queue" flow as the Dashboard home page's
  // JobDetailModal usage (index.tsx's handleQueueJob) -- this route
  // previously had its own separate drawer with permanently-disabled
  // Tailor/Queue buttons and no cover-letter action at all, out of sync
  // with the working version used from the Dashboard.
  const handleToggleQueue = async () => {
    if (queued || !job) return;
    setQueued(true);
    setApplyStatus({ state: "applying" });
    try {
      const result = await jobService.applyToJob(job.job_id);
      if (result.really_submitted) {
        setApplyStatus({ state: "applied" });
      } else if (result.status === "REVIEW_REQUIRED") {
        setApplyStatus({
          state: "review_required",
          message: result.failure_reason || "Needs your review before it can be submitted.",
        });
      } else {
        setApplyStatus({ state: "failed", message: result.failure_reason || "Couldn't complete this application." });
      }
    } catch (e) {
      setApplyStatus({ state: "failed", message: "Something went wrong — try again." });
    }
  };

  if (loading || error || !job) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-xs">
        {loading ? (
          <div className="glass-card rounded-2xl p-8 bg-white/95">
            <p className="text-xs text-ink-soft">Loading job details…</p>
          </div>
        ) : (
          <div className="glass-card rounded-2xl p-8 bg-white/95 text-center space-y-4">
            <AlertCircle className="h-10 w-10 text-red-500 mx-auto" />
            <p className="text-xs text-ink-soft">{error || "Job details not found."}</p>
            <button onClick={handleClose} className="btn-peach text-xs">Back to Jobs</button>
          </div>
        )}
      </div>
    );
  }

  return (
    <JobDetailModal
      job={job}
      queued={queued}
      applyStatus={applyStatus}
      onToggleQueue={handleToggleQueue}
      onClose={handleClose}
    />
  );
}
