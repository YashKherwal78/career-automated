import { createFileRoute } from "@tanstack/react-router";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton, StatusBadge } from "../../components/dashboard/CommonComponents";
import { ShieldAlert, Server, DollarSign, Database, ListCollapse, Terminal } from "lucide-react";

export const Route = createFileRoute("/dashboard/admin")({
  component: AdminConsolePage,
});

function AdminConsolePage() {
  const { companies, loading } = useDashboard();

  if (loading) {
    return (
      <div className="p-8">
        <LoadingSkeleton type="stats" />
        <LoadingSkeleton type="table" count={5} />
      </div>
    );
  }

  // Admin Logs mock data
  const logs = [
    { source: "EXA_SEARCH", text: "Query 'Stripe careers' verified in 430ms", cost: "$0.02" },
    { source: "CRAWLER", text: "Successfully parsed 208 Nvidia workday postings", cost: "$0.00" },
    { source: "VERIFIER", text: "Verified Lever endpoint for Netflix: 404 response", cost: "$0.00" }
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink flex items-center gap-2">
          <ShieldAlert className="h-6 w-6 text-red-500" />
          Operator Console (Admin)
        </h1>
        <p className="mt-1 text-xs text-ink-soft">
          Monitor crawler daemons, track API consumption costs, and explore the raw registry state.
        </p>
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-slate-900 p-2.5 text-slate-300">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">5 Running</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Crawler Workers</p>
          </div>
        </div>
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-slate-900 p-2.5 text-slate-300">
            <DollarSign className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">$2.40</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">API Cost (Today)</p>
          </div>
        </div>
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-slate-900 p-2.5 text-slate-300">
            <Database className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">1,867</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Raw Endpoints</p>
          </div>
        </div>
        <div className="glass-card rounded-2xl p-5 border border-white/50 bg-white/40 shadow-sm flex items-center gap-4">
          <div className="rounded-xl bg-slate-900 p-2.5 text-slate-300">
            <ListCollapse className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-ink">1</h3>
            <p className="text-[10px] uppercase font-semibold text-ink-soft tracking-wider">Active Failure</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Registry Explorer */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
          <h3 className="font-display text-lg font-semibold text-ink">ATS Registry Explorer</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/20 text-ink-soft">
                  <th className="pb-3 font-medium">Company ID</th>
                  <th className="pb-3 font-medium">ATS Board Endpoint</th>
                  <th className="pb-3 font-medium">Crawler Status</th>
                  <th className="pb-3 font-medium">Job Count</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((comp) => (
                  <tr key={comp.company_id} className="border-b border-white/10 hover:bg-white/30 transition-colors">
                    <td className="py-3 font-semibold text-ink">{comp.company_id}</td>
                    <td className="py-3 font-mono text-[10px] text-ink-soft truncate max-w-xs">{comp.website}</td>
                    <td className="py-3 uppercase text-ink-soft">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${comp.crawl_status === 'SUCCESS' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                        {comp.crawl_status || "IDLE"}
                      </span>
                    </td>
                    <td className="py-3 text-ink font-semibold">{comp.job_count ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Workers costs & operational log console */}
        <div className="space-y-6">
          <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
            <h3 className="font-display text-lg font-semibold text-ink flex items-center gap-2">
              <Terminal className="h-4.5 w-4.5" />
              API Operation Log
            </h3>
            <div className="space-y-4">
              {logs.map((log, idx) => (
                <div key={idx} className="flex justify-between items-start gap-4 text-xs border-b border-white/10 pb-2">
                  <div>
                    <span className="text-[9px] uppercase font-bold text-slate-500 tracking-wider block">{log.source}</span>
                    <p className="mt-0.5 text-ink-soft leading-snug">{log.text}</p>
                  </div>
                  <span className="font-mono text-emerald-600 font-semibold">{log.cost}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
