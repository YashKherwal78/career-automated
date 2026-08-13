import { createFileRoute, Link, Outlet, useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton } from "../../components/dashboard/CommonComponents";
import { CompanyLogo } from "../../components/dashboard/CompanyLogo";
import { Search, MapPin, ArrowUpDown } from "lucide-react";
import { Job } from "../../lib/services";

export const Route = createFileRoute("/dashboard/jobs")({
  validateSearch: (search: Record<string, unknown>) => ({
    select: (search.select as string) || undefined,
  }),
  component: JobsPage,
});

// Providers sourced from external job boards rather than a company's own
// ATS -- used only to label a row "External", not to split the list (the
// dashboard shows one unified feed, not separate tabs).
const JOB_BOARD_PROVIDERS = new Set(["linkedin", "google_jobs", "wellfound", "indeed"]);

function JobsPage() {
  const { jobService } = useDashboard();
  const searchParams = useSearch({ from: "/dashboard/jobs" });
  const navigate = useNavigate();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [remoteFilter, setRemoteFilter] = useState("");
  const [sortField, setSortField] = useState<"intent_score" | "posted_at">("posted_at");
  const [applyMode, setApplyMode] = useState<"automatic" | "assisted">("automatic");

  useEffect(() => {
    jobService
      .getAutoApplyPolicy()
      .then((p) => setApplyMode(p.apply_mode))
      .catch(() => {});
  }, [jobService]);

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
    } catch (e) {
      console.error(e);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadData(true);
  }, [search, roleFilter, locationFilter, remoteFilter, sortField]);

  // Live Auto-Refresh (poll every 30s)
  useEffect(() => {
    const interval = setInterval(() => {
      loadData(false);
    }, 30000);
    return () => clearInterval(interval);
  }, [search, roleFilter, locationFilter, remoteFilter, sortField]);

  // Navigate to job detail if selected via search params
  useEffect(() => {
    if (searchParams.select) {
      navigate({ to: `/dashboard/jobs/${searchParams.select}`, replace: true });
    }
  }, [searchParams.select, navigate]);

  return (
    <div className="p-8 space-y-6 relative min-h-screen">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Jobs</h1>
      </div>

      {/* Filters Bar */}
      <div className="glass-card rounded-2xl p-4 border border-white/50 bg-white/40 shadow-sm flex flex-wrap items-center gap-4 text-xs">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-3.5 w-3.5 text-ink-soft" />
          </span>
          <input
            type="text"
            placeholder="Search title or company..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:border-[color:var(--peach-deep)] transition-colors"
          />
        </div>

        {/* Role */}
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3 py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none text-ink-soft focus:border-[color:var(--peach-deep)] cursor-pointer"
        >
          {ROLE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        {/* Location */}
        <div className="relative">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MapPin className="h-3.5 w-3.5 text-ink-soft" />
          </span>
          <input
            type="text"
            placeholder="Location — India, Remote, US…"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            className="pl-9 pr-4 py-1.5 w-52 rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:border-[color:var(--peach-deep)] transition-colors"
          />
        </div>

        {/* Remote */}
        <select
          value={remoteFilter}
          onChange={(e) => setRemoteFilter(e.target.value)}
          className="px-3 py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none text-ink-soft focus:border-[color:var(--peach-deep)] cursor-pointer"
        >
          <option value="">Remote Type</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="onsite">Onsite</option>
        </select>

        {/* Sort */}
        <button
          onClick={() => setSortField(sortField === "intent_score" ? "posted_at" : "intent_score")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-white/60 bg-white/50 text-ink-soft hover:bg-white/80 transition-colors"
        >
          <ArrowUpDown className="h-3.5 w-3.5" />
          <span>Sort: {sortField === "intent_score" ? "Intent Match" : "Date Posted"}</span>
        </button>
      </div>

      {/* Jobs Table */}
      {loading ? (
        <LoadingSkeleton type="table" count={10} />
      ) : jobs.length === 0 ? (
        <div className="text-center py-12 glass-card rounded-3xl p-6 border border-white/50 bg-white/40">
          <p className="text-xs text-ink-soft">No jobs matched your filter criteria.</p>
        </div>
      ) : (
        <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/20 text-ink-soft">
                  <th className="pb-3 font-medium">Company</th>
                  <th className="pb-3 font-medium">Position</th>
                  <th className="pb-3 font-medium">Location</th>
                  <th className="pb-3 font-medium">Salary Range</th>
                  <th className="pb-3 font-medium">Remote</th>
                  <th className="pb-3 font-medium">Resume Match</th>
                  <th className="pb-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id} className="border-b border-white/10 hover:bg-white/30 transition-colors">
                    <td className="py-4 font-semibold text-ink">
                      <div className="flex items-center gap-2.5">
                        <CompanyLogo name={job.canonical_name} domain={job.company_domain} size={24} radius={6} fontSize={10.5} />
                        <span>{job.canonical_name}</span>
                        {JOB_BOARD_PROVIDERS.has((job.provider || "").toLowerCase()) && (
                          <span className="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-100">EXTERNAL</span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 text-ink-soft font-medium">{job.title}</td>
                    <td className="py-4 text-ink-soft">{job.location || "Remote"}</td>
                    <td className="py-4 text-ink-soft">
                      {job.salary_min && job.salary_max
                        ? `₹${(job.salary_min/100000).toFixed(1)}L - ₹${(job.salary_max/100000).toFixed(1)}L`
                        : "Competitive"}
                    </td>
                    <td className="py-4 text-ink-soft capitalize">{job.remote || "Onsite"}</td>
                    <td className="py-4 font-semibold text-[color:var(--peach-deep)]">
                      {job.intent_score != null
                        ? `${Math.round(job.intent_score * 100)}%`
                        : job.job_score
                        ? `${job.job_score}%`
                        : "—"}
                      <span className="ml-1 text-[9px] text-ink-soft font-normal">intent</span>
                    </td>
                    <td className="py-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {applyMode === "assisted" && job.apply_url && (
                          <a
                            href={`${job.apply_url}?_careerautomated_autofill=1`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 text-xs rounded-xl border border-[color:var(--peach-deep)] text-[color:var(--peach-deep)] font-medium whitespace-nowrap"
                          >
                            Open & Autofill
                          </a>
                        )}
                        <Link to={`/dashboard/jobs/${job.job_id}`} className="btn-peach px-3 py-1.5 text-xs rounded-xl">
                          View Details
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Slide-out details drawer injected via Outlet */}
      <Outlet />
    </div>
  );
}
