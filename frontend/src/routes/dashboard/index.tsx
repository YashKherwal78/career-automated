import { createFileRoute, Link } from "@tanstack/react-router";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { StatCard, LoadingSkeleton, StatusBadge } from "../../components/dashboard/CommonComponents";
import { 
  Briefcase, 
  Building2, 
  GitFork, 
  Award, 
  TrendingUp, 
  Send,
  Zap,
  CheckCircle,
  AlertTriangle,
  Play
} from "lucide-react";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardHome,
});

function DashboardHome() {
  const { recentJobs, overview, pipeline, loading } = useDashboard();

  if (loading) {
    return (
      <div className="p-8 space-y-8">
        <LoadingSkeleton type="stats" />
        <LoadingSkeleton type="table" count={5} />
      </div>
    );
  }

  // Activity Feed mock data
  const activities = [
    { type: "success", message: "Nvidia discovered 14 new jobs", time: "2 hrs ago" },
    { type: "success", message: "Stripe endpoint verified", time: "4 hrs ago" },
    { type: "info", message: "Netflix crawl completed", time: "6 hrs ago" },
    { type: "warning", message: "Adobe crawl failed (timeout)", time: "Yesterday" }
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Welcome Banner */}
      <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm">
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink">Good Morning, Yash</h1>
        <p className="mt-2 text-sm text-ink-soft">
          Here is your overnight pipeline operation report:
        </p>
        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-6 text-center border-t border-white/20 pt-4">
          <div>
            <span className="block text-xl font-semibold text-ink">{overview?.jobs || 0}</span>
            <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Jobs Crawled</span>
          </div>
          <div>
            <span className="block text-xl font-semibold text-ink">{overview?.verified || 0}</span>
            <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Verified ATS</span>
          </div>
          <div>
            <span className="block text-xl font-semibold text-ink">{overview?.companies || 0}</span>
            <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Companies</span>
          </div>
          <div>
            <span className="block text-xl font-semibold text-red-500">{overview?.failed_workers || 0}</span>
            <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Failed Workers</span>
          </div>
          <div>
            <span className="block text-xl font-semibold text-emerald-500">{overview?.active_workers || 0}</span>
            <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Active Workers</span>
          </div>
          <div>
            <span className="block text-xl font-semibold text-[color:var(--peach-deep)]">{overview?.crawl_queue || 0}</span>
            <span className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Crawl Queue</span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Jobs Available"
          value={overview?.jobs || 0}
          detail="Active indexed matchings"
          icon={Briefcase}
        />
        <StatCard
          title="Companies Tracked"
          value={overview?.companies || 0}
          detail="Startups & Corporates"
          icon={Building2}
        />
        <StatCard
          title="Verified ATS Endpoints"
          value={overview?.verified || 0}
          detail="Greenhouse, Lever, etc."
          icon={GitFork}
        />
        <StatCard
          title="Active Workers"
          value={overview?.active_workers || 0}
          detail="Discovery & crawl daemons"
          icon={Send}
        />
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Recent Jobs Table */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-ink">Recent Highly Matching Jobs</h2>
            <Link to="/dashboard/jobs" className="text-xs font-semibold text-[color:var(--peach-deep)] hover:underline">
              View all jobs
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/20 text-ink-soft">
                  <th className="pb-3 font-medium">Company</th>
                  <th className="pb-3 font-medium">Position</th>
                  <th className="pb-3 font-medium">Location</th>
                  <th className="pb-3 font-medium">ATS</th>
                  <th className="pb-3 font-medium">Match</th>
                  <th className="pb-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {recentJobs.slice(0, 5).map((job) => (
                  <tr key={job.job_id} className="border-b border-white/10 hover:bg-white/30 transition-colors">
                    <td className="py-3 font-semibold text-ink">{job.canonical_name}</td>
                    <td className="py-3 text-ink-soft">{job.title}</td>
                    <td className="py-3 text-ink-soft">{job.location}</td>
                    <td className="py-3 uppercase text-ink-soft">{job.provider}</td>
                    <td className="py-3 font-semibold text-[color:var(--peach-deep)]">{job.job_score}%</td>
                    <td className="py-3 text-right">
                      <Link to="/dashboard/jobs" search={{ select: job.job_id }} className="btn-peach px-2 py-1 text-[10px] rounded-lg">
                        Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Status Panels */}
        <div className="space-y-6">
          {/* Worker Health */}
          <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
            <h2 className="font-display text-lg font-semibold text-ink">Worker Health Monitor</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-xs font-medium text-ink-soft">Discovery Worker</span>
                <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
                  Running
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-xs font-medium text-ink-soft">Endpoint Worker</span>
                <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
                  Running
                </span>
              </div>
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-xs font-medium text-ink-soft">Crawler Worker</span>
                <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
                  Running
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-ink-soft">Scheduler</span>
                <span className="text-xs font-semibold text-ink-soft">Idle</span>
              </div>
            </div>
          </div>

          {/* Activity Feed */}
          <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
            <h2 className="font-display text-lg font-semibold text-ink">Activity Feed</h2>
            <div className="space-y-4">
              {activities.map((act, idx) => (
                <div key={idx} className="flex items-start gap-2.5 text-xs">
                  {act.type === "success" && <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5" />}
                  {act.type === "warning" && <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />}
                  {act.type === "info" && <Zap className="h-4 w-4 text-blue-500 mt-0.5" />}
                  <div className="space-y-0.5">
                    <p className="font-medium text-ink">{act.message}</p>
                    <span className="text-[10px] text-ink-soft">{act.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
