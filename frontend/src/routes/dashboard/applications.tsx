import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { CheckCircle2, Circle, Clock, XCircle, Trophy, Sparkles } from "lucide-react";

export const Route = createFileRoute("/dashboard/applications")({
  component: ApplicationsPage,
});

// Mock Application Pipeline states
const APPLICATIONS = [
  {
    id: 1,
    company: "Stripe",
    role: "Product Engineer",
    stage: "Interview", // Applied, Assessment, Interview, Offer, Rejected
    date: "Applied 4 days ago",
    timeline: [
      { name: "Applied", status: "completed", date: "July 15" },
      { name: "Assessment", status: "completed", date: "July 17" },
      { name: "Interview", status: "current", date: "Scheduled July 22" },
      { name: "Offer", status: "upcoming", date: "" }
    ]
  },
  {
    id: 2,
    company: "Linear",
    role: "Frontend Engineer",
    stage: "Applied",
    date: "Applied today",
    timeline: [
      { name: "Applied", status: "current", date: "July 19" },
      { name: "Assessment", status: "upcoming", date: "" },
      { name: "Interview", status: "upcoming", date: "" },
      { name: "Offer", status: "upcoming", date: "" }
    ]
  },
  {
    id: 3,
    company: "Notion",
    role: "Full-stack Developer",
    stage: "Assessment",
    date: "Applied 1 week ago",
    timeline: [
      { name: "Applied", status: "completed", date: "July 12" },
      { name: "Assessment", status: "current", date: "Due July 20" },
      { name: "Interview", status: "upcoming", date: "" },
      { name: "Offer", status: "upcoming", date: "" }
    ]
  },
  {
    id: 4,
    company: "Ramp",
    role: "Software Engineer",
    stage: "Rejected",
    date: "Applied 2 weeks ago",
    timeline: [
      { name: "Applied", status: "completed", date: "July 5" },
      { name: "Assessment", status: "completed", date: "July 7" },
      { name: "Interview", status: "failed", date: "Rejected July 12" }
    ]
  }
];

function ApplicationsPage() {
  const [activeTab, setActiveTab] = useState<"all" | "active" | "archived">("all");

  const getStageIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case "current":
        return <Clock className="h-4 w-4 text-[color:var(--peach-deep)] animate-pulse" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Circle className="h-4 w-4 text-slate-300" />;
    }
  };

  const getStageBadge = (stage: string) => {
    switch (stage) {
      case "Offer":
        return "bg-emerald-50 text-emerald-600 border-emerald-100";
      case "Rejected":
        return "bg-red-50 text-red-500 border-red-100";
      case "Interview":
        return "bg-[color:var(--peach-soft)] text-[color:var(--peach-deep)] border-peach-100";
      default:
        return "bg-slate-50 text-ink-soft border-slate-100";
    }
  };

  const filteredApps = APPLICATIONS.filter(app => {
    if (activeTab === "active") return app.stage !== "Rejected" && app.stage !== "Offer";
    if (activeTab === "archived") return app.stage === "Rejected" || app.stage === "Offer";
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto px-8 py-12 space-y-12">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/20 pb-6">
        <div className="space-y-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
            Applications
          </h1>
          <p className="text-sm text-ink-soft">
            Track and monitor the pipeline of your matching opportunities.
          </p>
        </div>

        <div className="flex rounded-xl bg-white/40 border border-white/60 p-0.5 text-xs">
          {(["all", "active", "archived"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg font-medium transition-colors uppercase tracking-wider text-[10px] ${
                activeTab === tab ? "bg-white text-ink shadow-sm" : "text-ink-soft hover:text-ink"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline listing */}
      <div className="space-y-6">
        {filteredApps.length === 0 ? (
          <div className="py-16 text-center border border-dashed border-white/60 bg-white/20 rounded-3xl">
            <span className="text-xs text-ink-soft">No applications in this category.</span>
          </div>
        ) : (
          filteredApps.map((app) => (
            <div
              key={app.id}
              className="glass-card rounded-3xl p-6 border border-white/60 bg-white/40 shadow-sm space-y-6 hover:shadow-md transition-shadow"
            >
              {/* Top Details */}
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider">
                    {app.company}
                  </span>
                  <h3 className="font-display text-lg font-semibold text-ink leading-tight">
                    {app.role}
                  </h3>
                  <span className="text-[10px] text-ink-soft block">{app.date}</span>
                </div>

                <span className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold border ${getStageBadge(app.stage)}`}>
                  {app.stage}
                </span>
              </div>

              {/* Stage Progress Timeline */}
              <div className="border-t border-white/20 pt-6">
                <div className="grid grid-cols-4 gap-4 relative">
                  {app.timeline.map((step, idx) => (
                    <div key={step.name} className="flex flex-col items-center text-center space-y-2 relative">
                      {/* Connection Line */}
                      {idx < app.timeline.length - 1 && (
                        <div className="absolute left-[calc(50%+16px)] top-[7px] right-[-50%] h-[2px] bg-slate-200" />
                      )}
                      
                      {getStageIcon(step.status)}
                      
                      <div className="space-y-0.5">
                        <span className={`text-[10px] font-bold uppercase tracking-wider block ${
                          step.status === "current" ? "text-ink" : "text-ink-soft"
                        }`}>
                          {step.name}
                        </span>
                        {step.date && (
                          <span className="text-[9px] text-ink-soft block">{step.date}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          ))
        )}
      </div>
    </div>
  );
}
