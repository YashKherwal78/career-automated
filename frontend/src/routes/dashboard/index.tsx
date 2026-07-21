import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { MapPin, Briefcase, Sparkles, Filter, ChevronRight, Loader2, Search, SlidersHorizontal } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ServiceRegistry, Job } from "../../lib/services";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardHome,
});

export function DashboardHome() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [locationFilter, setLocationFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");

  // Fetch jobs
  useEffect(() => {
    async function loadJobs() {
      try {
        setIsLoading(true);
        const jobService = ServiceRegistry.getJobService();
        const data = await jobService.getJobs();
        setJobs(data || []);
      } catch (err: any) {
        console.error("Failed to fetch jobs:", err);
        setError("Unable to load live opportunity matches.");
      } finally {
        setIsLoading(false);
      }
    }
    loadJobs();
  }, []);

  // Match filtering
  const filterJobs = (jobList: Job[]) => {
    return jobList.filter((job) => {
      const matchQuery =
        !searchQuery ||
        (job.title || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        (job.canonical_name || "").toLowerCase().includes(searchQuery.toLowerCase());

      const matchLoc =
        locationFilter === "All" ||
        (locationFilter === "Remote" && (job.location || "").toLowerCase().includes("remote")) ||
        (locationFilter === "Onsite/Hybrid" && !(job.location || "").toLowerCase().includes("remote"));

      const matchType =
        typeFilter === "All" ||
        (typeFilter === "Full-time" && (job.remote || "").toLowerCase().includes("full")) ||
        (typeFilter === "Hybrid" && (job.remote || "").toLowerCase().includes("hybrid"));

      return matchQuery && matchLoc && matchType;
    });
  };

  const activeJobs = filterJobs(jobs);
  // Top 5 match cards
  const topMatches = activeJobs.slice(0, 5);
  // Remaining matches
  const secondaryMatches = activeJobs.slice(5);

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-10 py-10 space-y-10">
      
      {/* 1. Header Philosophy Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b hairline pb-6">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[color:var(--peach-soft)] text-[color:var(--peach-deep)] text-[11px] font-semibold">
            <Sparkles className="h-3 w-3" /> Pre-Filtered Intelligence
          </div>
          <h1 className="font-display text-3xl md:text-4xl font-semibold tracking-tight text-ink">
            Top Matches
          </h1>
          <p className="text-xs text-ink-soft max-w-md">
            Your AI candidate profile searched all live listing portals and filtered out non-matching opportunities.
          </p>
        </div>

        {/* Quick Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ink-soft" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search role or company..."
            className="w-full pl-9 pr-4 py-2 bg-white/60 border hairline rounded-xl text-xs text-ink placeholder:text-ink-soft focus:outline-none focus:border-[color:var(--peach-deep)] transition-colors"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="min-h-[360px] flex flex-col items-center justify-center space-y-3">
          <Loader2 className="h-7 w-7 text-[color:var(--peach-deep)] animate-spin" />
          <span className="text-xs text-ink-soft font-medium">Fetching top matched opportunities...</span>
        </div>
      ) : error ? (
        <div className="min-h-[220px] flex flex-col items-center justify-center text-center space-y-3 border border-red-100 bg-red-50/50 rounded-3xl p-6">
          <span className="text-xs text-red-500 font-semibold">{error}</span>
          <button
            onClick={() => window.location.reload()}
            className="btn-dark px-5 py-2 text-xs rounded-xl"
          >
            Retry Loading
          </button>
        </div>
      ) : (
        <>
          {/* 2. Top Matches Horizontal Grid */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs uppercase font-bold tracking-widest text-ink-soft flex items-center gap-1.5">
                Top Recommendation Suite ({topMatches.length})
              </h2>
              <span className="text-[10px] text-ink-soft">Highest fit score first</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topMatches.length === 0 ? (
                <div className="col-span-full py-12 text-center glass-card rounded-3xl">
                  <span className="text-xs text-ink-soft">No matching opportunities found with your criteria.</span>
                </div>
              ) : (
                topMatches.map((job) => (
                  <div
                    key={job.job_id}
                    className="glass-card rounded-3xl p-6 flex flex-col justify-between hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 border hairline bg-white/40"
                  >
                    <div className="space-y-4">
                      <div className="flex items-start justify-between">
                        <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider truncate max-w-[130px]">
                          {job.canonical_name || "Company"}
                        </span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-50 text-[10px] font-bold text-emerald-600 border border-emerald-100">
                          {job.job_score || 92}% Fit
                        </span>
                      </div>

                      <h3 className="font-display text-base font-semibold leading-snug text-ink line-clamp-2">
                        {job.title}
                      </h3>
                    </div>

                    <div className="mt-6 space-y-4 pt-4 border-t hairline">
                      <div className="space-y-1.5 text-[11px] text-ink-soft">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="h-3 w-3 text-ink-soft" />
                          <span className="truncate max-w-[180px]">{job.location || "Remote / Onsite"}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Briefcase className="h-3 w-3 text-ink-soft" />
                          <span>{job.remote || "Full-time"}</span>
                        </div>
                      </div>

                      <a
                        href={job.apply_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-dark w-full py-2.5 text-xs rounded-xl flex items-center justify-center gap-1 font-medium"
                      >
                        Review & Tailor Application <ChevronRight className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 3. Refine Filter Bar */}
          <div className="flex flex-wrap items-center justify-between border-t border-b hairline py-3.5 gap-4">
            <div className="flex items-center gap-2 text-xs text-ink-soft">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span className="font-medium">Refine Preferences</span>
            </div>

            <div className="flex items-center gap-3">
              {/* Location Filter */}
              <div className="flex rounded-xl bg-white/50 border hairline p-0.5 text-[11px]">
                {["All", "Remote", "Onsite/Hybrid"].map((loc) => (
                  <button
                    key={loc}
                    onClick={() => setLocationFilter(loc)}
                    className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                      locationFilter === loc ? "bg-white text-ink shadow-xs" : "text-ink-soft hover:text-ink"
                    }`}
                  >
                    {loc}
                  </button>
                ))}
              </div>

              {/* Type Filter */}
              <div className="flex rounded-xl bg-white/50 border hairline p-0.5 text-[11px]">
                {["All", "Full-time", "Hybrid"].map((type) => (
                  <button
                    key={type}
                    onClick={() => setTypeFilter(type)}
                    className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                      typeFilter === type ? "bg-white text-ink shadow-xs" : "text-ink-soft hover:text-ink"
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 4. Secondary Pipeline List */}
          {secondaryMatches.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xs uppercase font-bold tracking-widest text-ink-soft">
                Additional Pipeline Matches ({secondaryMatches.length})
              </h2>

              <div className="glass-card rounded-3xl border hairline bg-white/40 overflow-hidden shadow-xs">
                <div className="divide-y divide-white/20">
                  {secondaryMatches.map((job) => (
                    <div
                      key={job.job_id}
                      className="flex items-center justify-between px-6 py-4 hover:bg-white/50 transition-colors group"
                    >
                      <div className="flex items-center gap-4">
                        <div className="grid h-9 w-9 place-items-center rounded-xl bg-white border hairline text-xs font-semibold text-ink">
                          {(job.canonical_name || "C").slice(0, 1)}
                        </div>

                        <div className="space-y-0.5">
                          <h4 className="text-xs font-semibold text-ink group-hover:text-[color:var(--peach-deep)] transition-colors">
                            {job.title}
                          </h4>
                          <div className="flex items-center gap-2 text-[11px] text-ink-soft">
                            <span>{job.canonical_name}</span>
                            <span>•</span>
                            <span>{job.location}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <span className="text-xs font-semibold text-emerald-600">
                          {job.job_score}% fit
                        </span>
                        <a
                          href={job.apply_url}
                          target="_blank"
                          rel="noreferrer"
                          className="btn-dark px-3.5 py-1.5 text-xs rounded-xl opacity-90 group-hover:opacity-100 transition-opacity"
                        >
                          Review
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}

    </div>
  );
}
