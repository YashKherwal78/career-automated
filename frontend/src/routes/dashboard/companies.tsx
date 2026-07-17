import { createFileRoute } from "@tanstack/react-router";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton, StatusBadge } from "../../components/dashboard/CommonComponents";
import { Building2, Activity, ShieldCheck, Heart } from "lucide-react";

export const Route = createFileRoute("/dashboard/companies")({
  component: CompaniesPage,
});

function CompaniesPage() {
  const { companies, loading } = useDashboard();

  if (loading) {
    return (
      <div className="p-8">
        <LoadingSkeleton type="table" count={10} />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Company Registry Health</h1>
        <p className="mt-1 text-xs text-ink-soft">
          Active tracking of corporate endpoints and pipeline health metrics.
        </p>
      </div>

      {/* Grid overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-600">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">1,108</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Active Endpoints</p>
          </div>
        </div>
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-blue-50 p-2.5 text-blue-600">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">98.4%</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Scraper Uptime</p>
          </div>
        </div>
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-[color:var(--peach-soft)] p-2.5 text-[color:var(--peach-deep)]">
            <Heart className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">Healthy</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Registry State</p>
          </div>
        </div>
      </div>

      {/* Companies Table */}
      <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/20 text-ink-soft">
                <th className="pb-3 font-medium">Company</th>
                <th className="pb-3 font-medium">ATS Board</th>
                <th className="pb-3 font-medium">Verified Status</th>
                <th className="pb-3 font-medium">Last Crawl</th>
                <th className="pb-3 font-medium">Jobs Found</th>
                <th className="pb-3 font-medium">Endpoint Health</th>
              </tr>
            </thead>
            <tbody>
              {companies.map((comp) => {
                const isHealthy = comp.crawl_status !== "FAILED";
                return (
                  <tr key={comp.company_id} className="border-b border-white/10 hover:bg-white/30 transition-colors">
                    <td className="py-4">
                      <div className="flex items-center gap-2">
                        <div className="h-6 w-6 rounded bg-white/80 border border-slate-200 flex items-center justify-center font-semibold text-xs text-ink-soft">
                          {comp.company_name.charAt(0)}
                        </div>
                        <span className="font-semibold text-ink">{comp.company_name}</span>
                      </div>
                    </td>
                    <td className="py-4 uppercase text-ink-soft">{comp.ats_type || "Unknown"}</td>
                    <td className="py-4">
                      <StatusBadge status={comp.status} />
                    </td>
                    <td className="py-4 text-ink-soft">
                      {comp.last_checked ? new Date(comp.last_checked).toLocaleDateString() : "Pending"}
                    </td>
                    <td className="py-4 text-ink font-medium">{comp.job_count ?? 0}</td>
                    <td className="py-4">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${isHealthy ? 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20' : 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/10'}`}>
                        {isHealthy ? "Healthy" : "Critical"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
