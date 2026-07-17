import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton } from "../../components/dashboard/CommonComponents";
import { X, CheckCircle2, AlertCircle, FileText, Send, ExternalLink } from "lucide-react";
import { Job } from "../../lib/services";

export const Route = createFileRoute("/dashboard/jobs/$jobId")({
  component: JobDetailsRoute,
});

function JobDetailsRoute() {
  const { jobId } = Route.useParams();
  const { jobService } = useDashboard();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // Mock score breakdown if not provided
  const scoreBreakdown = job?.score_breakdown && Array.isArray(job.score_breakdown) && job.score_breakdown.length > 0
    ? job.score_breakdown
    : [
        { keyword: "React", matched: true },
        { keyword: "TypeScript", matched: true },
        { keyword: "FastAPI", matched: true },
        { keyword: "Python", matched: true },
        { keyword: "Docker", matched: false },
        { keyword: "Kubernetes", matched: false }
      ];

  const matchedSkills = scoreBreakdown.filter(s => typeof s === 'object' && s !== null && 'matched' in s && s.matched);
  const missingSkills = scoreBreakdown.filter(s => typeof s === 'object' && s !== null && 'matched' in s && !s.matched);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30 backdrop-blur-xs">
      {/* Click outside backdrop to close */}
      <div className="absolute inset-0" onClick={handleClose} />

      {/* Drawer Container (Slides from right on desktop, fills screen on mobile) */}
      <div className="relative w-full max-w-lg bg-white/95 min-h-screen shadow-2xl border-l border-white/50 flex flex-col p-6 overflow-y-auto animate-in slide-in-from-right duration-300">
        
        {/* Close button */}
        <button onClick={handleClose} className="absolute top-6 right-6 p-1.5 rounded-lg hover:bg-slate-100 transition-colors text-ink-soft hover:text-ink">
          <X className="h-4.5 w-4.5" />
        </button>

        {loading ? (
          <div className="mt-8 space-y-6">
            <LoadingSkeleton type="cards" count={1} />
            <LoadingSkeleton type="table" count={4} />
          </div>
        ) : error || !job ? (
          <div className="mt-12 text-center space-y-4">
            <AlertCircle className="h-10 w-10 text-red-500 mx-auto" />
            <p className="text-xs text-ink-soft">{error || "Job details not found."}</p>
            <button onClick={handleClose} className="btn-peach text-xs">Back to Jobs</button>
          </div>
        ) : (
          <div className="mt-6 flex-1 flex flex-col gap-6">
            
            {/* Header info */}
            <div>
              <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">{job.canonical_name}</span>
              <h2 className="mt-1 font-display text-2xl font-bold tracking-tight text-ink">{job.title}</h2>
              <p className="mt-2 text-xs text-ink-soft flex items-center gap-4">
                <span>{job.location}</span>
                <span>•</span>
                <span>{job.remote}</span>
                <span>•</span>
                <span className="uppercase">{job.provider} Board</span>
              </p>
            </div>

            {/* Score Match explanation */}
            <div className="glass-card rounded-2xl p-5 border border-white bg-slate-50/50 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-ink">Resume Match Analysis</span>
                <span className="text-lg font-bold text-[color:var(--peach-deep)]">{job.job_score}%</span>
              </div>
              <div className="space-y-3">
                {/* Matching */}
                <div>
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-ink-soft">Matching Skills</h4>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {matchedSkills.map((s, idx) => {
                      const name = typeof s === 'string' ? s : (s as any).keyword;
                      return (
                        <span key={idx} className="inline-flex items-center gap-1 rounded-lg bg-emerald-50 border border-emerald-100 px-2 py-0.5 text-xs text-emerald-700">
                          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                          {name}
                        </span>
                      );
                    })}
                  </div>
                </div>

                {/* Missing */}
                <div>
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider text-ink-soft">Gaps Detected</h4>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {missingSkills.map((s, idx) => {
                      const name = typeof s === 'string' ? s : (s as any).keyword;
                      return (
                        <span key={idx} className="inline-flex items-center gap-1 rounded-lg bg-rose-50 border border-rose-100 px-2 py-0.5 text-xs text-rose-700">
                          <X className="h-3 w-3 text-rose-600" />
                          {name}
                        </span>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="grid grid-cols-2 gap-3 border-b border-slate-100 pb-6">
              <button disabled className="btn-ghost-ink w-full flex items-center justify-center gap-2 cursor-not-allowed opacity-60 text-xs py-2">
                <FileText className="h-4 w-4" />
                Tailor Resume
              </button>
              <button disabled className="btn-ghost-ink w-full flex items-center justify-center gap-2 cursor-not-allowed opacity-60 text-xs py-2">
                <Send className="h-4 w-4" />
                Queue Application
              </button>
              <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="btn-peach w-full col-span-2 flex items-center justify-center gap-2 text-xs py-2">
                <span>Apply on {job.provider}</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>

            {/* Description */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-ink">Job Description</h3>
              <div className="text-xs leading-relaxed text-ink-soft space-y-4 pr-2 max-h-96 overflow-y-auto">
                <p>{job.description || "No full job description available. Use the Apply Link to check details directly on the career page."}</p>
                <p><strong>Responsibilities:</strong></p>
                <ul className="list-disc pl-4 space-y-1">
                  <li>Build high-performance interfaces and backend system architectures.</li>
                  <li>Partner with cross-functional product and infrastructure engineering teams.</li>
                  <li>Ensure high coverage reliability across search services and databases.</li>
                </ul>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
