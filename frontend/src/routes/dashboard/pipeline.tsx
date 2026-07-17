import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton, StatusBadge } from "../../components/dashboard/CommonComponents";
import { 
  ArrowRight, 
  Layers, 
  Settings, 
  Activity, 
  Terminal,
  RefreshCw,
  Play
} from "lucide-react";

export const Route = createFileRoute("/dashboard/pipeline")({
  component: PipelinePage,
});

function PipelinePage() {
  const { pipeline, loading, refresh } = useDashboard();
  const [activeStage, setActiveStage] = useState<string>("discovery");

  if (loading) {
    return (
      <div className="p-8">
        <LoadingSkeleton type="stats" />
        <LoadingSkeleton type="table" count={5} />
      </div>
    );
  }

  const stages = [
    { id: "companies", label: "Companies Registry", count: pipeline?.companies || 6482, detail: "Total target names in identities list" },
    { id: "discovery", label: "Discovery Queue", count: "Active", detail: "Probing domains and search fallbacks" },
    { id: "endpoints", label: "Career Endpoints", count: pipeline?.endpoints || 1867, detail: "Discovered raw career board URLs" },
    { id: "verified", label: "Verified ATS Board", count: pipeline?.verified || 1108, detail: "Successfully inspected Greenhouse/Lever/etc" },
    { id: "crawlers", label: "Job Crawlers", count: "Running", detail: "Active board syncing and scraping daemons" },
    { id: "jobs", label: "Jobs Database", count: pipeline?.jobs || 145332, detail: "Total normalized listings stored" }
  ];

  // Stage detail mapping
  const renderStageDetail = () => {
    switch (activeStage) {
      case "companies":
        return (
          <div className="space-y-3">
            <h4 className="font-semibold text-ink">Target Directory Details</h4>
            <p className="text-xs text-ink-soft">
              This is the source table containing raw legal names and target domains. New companies are ingested dynamically via search heuristics or CSV import providers.
            </p>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Manual Seed Importer</span>
                <span className="block text-sm font-semibold text-ink mt-1">1,892 Companies</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">YC Batch Crawler</span>
                <span className="block text-sm font-semibold text-ink mt-1">4,590 Companies</span>
              </div>
            </div>
          </div>
        );
      case "discovery":
        return (
          <div className="space-y-3">
            <h4 className="font-semibold text-ink">Discovery Worker Health</h4>
            <div className="grid grid-cols-2 gap-4 text-xs md:grid-cols-4">
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">State</span>
                <span className="block text-sm font-semibold text-emerald-600 mt-1">Running</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Success Rate</span>
                <span className="block text-sm font-semibold text-ink mt-1">96.4%</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Discovery Latency</span>
                <span className="block text-sm font-semibold text-ink mt-1">420 ms</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Retry Queue</span>
                <span className="block text-sm font-semibold text-ink mt-1">2 Pending</span>
              </div>
            </div>
          </div>
        );
      case "endpoints":
        return (
          <div className="space-y-3">
            <h4 className="font-semibold text-ink">Raw Career Boards List</h4>
            <p className="text-xs text-ink-soft">
              Temporary landing repository holding candidate URL listings harvested from crawl scripts. Endpoints wait here for parsing, normalization, and verification checks.
            </p>
          </div>
        );
      case "verified":
        return (
          <div className="space-y-3">
            <h4 className="font-semibold text-ink">Verification Worker Health</h4>
            <div className="grid grid-cols-2 gap-4 text-xs md:grid-cols-4">
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">State</span>
                <span className="block text-sm font-semibold text-emerald-600 mt-1">Running</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Verification Rate</span>
                <span className="block text-sm font-semibold text-ink mt-1">84%</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Average Inspect Time</span>
                <span className="block text-sm font-semibold text-ink mt-1">1.2s</span>
              </div>
              <div className="border border-white/20 p-3 rounded-xl bg-white/20">
                <span className="text-ink-soft">Failures (24h)</span>
                <span className="block text-sm font-semibold text-red-500 mt-1">3 Endpoints</span>
              </div>
            </div>
          </div>
        );
      case "crawlers":
        return (
          <div className="space-y-3">
            <h4 className="font-semibold text-ink">Scraper Crawler Clusters</h4>
            <p className="text-xs text-ink-soft">
              Active crawling nodes syncing verified Greenhouse, Lever, Ashby, and Workday APIs page-by-page.
            </p>
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div className="p-2 border border-white/10 rounded-lg bg-white/10">
                <span className="text-ink-soft block">Greenhouse</span>
                <span className="text-xs font-semibold text-emerald-600">Active (598)</span>
              </div>
              <div className="p-2 border border-white/10 rounded-lg bg-white/10">
                <span className="text-ink-soft block">Ashby</span>
                <span className="text-xs font-semibold text-emerald-600">Active (115)</span>
              </div>
              <div className="p-2 border border-white/10 rounded-lg bg-white/10">
                <span className="text-ink-soft block">Lever</span>
                <span className="text-xs font-semibold text-emerald-600">Active (289)</span>
              </div>
              <div className="p-2 border border-white/10 rounded-lg bg-white/10">
                <span className="text-ink-soft block">Workday</span>
                <span className="text-xs font-semibold text-amber-500">Wait Delay</span>
              </div>
            </div>
          </div>
        );
      case "jobs":
        return (
          <div className="space-y-3">
            <h4 className="font-semibold text-ink">Unified Job Database</h4>
            <p className="text-xs text-ink-soft">
              Unified schema directory storing normalized postings. Job match scoring is dynamically computed here against master resumes.
            </p>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Pipeline Flow Engine</h1>
          <p className="mt-1 text-xs text-ink-soft">
            Direct visualizer mapping raw target companies into verified job listings.
          </p>
        </div>
        <button onClick={refresh} className="flex items-center gap-1.5 btn-peach text-xs px-3 py-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh Pipeline
        </button>
      </div>

      {/* Visual Flow chart (Clickable) */}
      <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm overflow-x-auto">
        <div className="flex items-center justify-between min-w-[800px] gap-2">
          {stages.map((st, idx) => {
            const active = activeStage === st.id;
            return (
              <div key={st.id} className="flex items-center flex-1">
                {/* Stage Box */}
                <button
                  onClick={() => setActiveStage(st.id)}
                  className={`flex-1 text-left p-4 rounded-2xl border transition-all duration-300 ${
                    active
                      ? "border-transparent bg-[color:var(--peach-soft)] shadow-md scale-105"
                      : "border-white/50 bg-white/50 hover:bg-white/80"
                  }`}
                >
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">{st.label}</span>
                  <span className="mt-2 block text-xl font-bold text-ink">{st.count}</span>
                  <span className="mt-1 text-[10px] text-ink-soft line-clamp-1 leading-snug">{st.detail}</span>
                </button>

                {/* Arrow */}
                {idx < stages.length - 1 && (
                  <div className="px-3">
                    <ArrowRight className="h-4 w-4 text-ink-soft" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Stage Detail panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm min-h-[250px]">
          {renderStageDetail()}
        </div>

        {/* Live worker logs */}
        <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm flex flex-col justify-between">
          <div className="flex items-center gap-2 mb-3">
            <Terminal className="h-4.5 w-4.5 text-ink-soft" />
            <h3 className="font-semibold text-xs text-ink uppercase tracking-wider">Live worker logs</h3>
          </div>
          <div className="flex-1 bg-slate-900 text-slate-300 font-mono text-[10px] p-4 rounded-2xl overflow-y-auto space-y-1.5 h-44 border border-slate-800">
            <p className="text-emerald-400">✓ Ingesting Stripe metadata...</p>
            <p className="text-emerald-400">✓ Verifying Ashby patterns...</p>
            <p className="text-emerald-400">✓ Crawling Nvidia workday postings...</p>
            <p className="text-slate-400">[04:54:12] - Workday Sync complete: 208 jobs updated</p>
            <p className="text-amber-400">⚠ Rate limit hit: delaying workday fetch 3.0s</p>
          </div>
        </div>
      </div>
    </div>
  );
}
