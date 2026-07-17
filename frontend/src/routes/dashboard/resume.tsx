import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton } from "../../components/dashboard/CommonComponents";
import { FileText, Upload, CheckCircle2, History, Plus } from "lucide-react";

export const Route = createFileRoute("/dashboard/resume")({
  component: ResumePage,
});

function ResumePage() {
  const { resumeService } = useDashboard();
  
  const [loading, setLoading] = useState(true);
  const [resumeInfo, setResumeInfo] = useState<{
    score: number;
    skills: string[];
    projectsCount: number;
    history: { date: string; score: number; changes: string }[];
  } | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const info = await resumeService.getResumeInfo();
        setResumeInfo(info);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [resumeService]);

  if (loading || !resumeInfo) {
    return (
      <div className="p-8">
        <LoadingSkeleton type="cards" count={3} />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Resume Optimizer</h1>
        <p className="mt-1 text-xs text-ink-soft">
          Manage your master profile and generate tailored resumes matching roles.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Profile Card & Score */}
        <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-6">
          <div className="text-center space-y-3">
            <h3 className="font-display text-lg font-semibold text-ink">Master Resume Score</h3>
            <div className="relative inline-flex items-center justify-center">
              {/* Outer dial */}
              <div className="h-32 w-32 rounded-full border-4 border-slate-200 flex items-center justify-center">
                <span className="text-4xl font-bold text-[color:var(--peach-deep)]">{resumeInfo.score}%</span>
              </div>
            </div>
            <p className="text-xs text-ink-soft">Strong match across 84 engineering roles</p>
          </div>

          {/* Upload widget */}
          <div className="border border-dashed border-white/60 bg-white/30 rounded-2xl p-6 text-center space-y-2 hover:bg-white/50 transition-colors">
            <Upload className="h-6 w-6 text-ink-soft mx-auto" />
            <span className="block text-xs font-semibold text-ink">Upload New PDF</span>
            <span className="text-[10px] text-ink-soft">Max size 5MB</span>
            <button className="btn-peach px-3 py-1.5 text-xs rounded-xl mt-2 w-full">Choose File</button>
          </div>
        </div>

        {/* Master resume parsed info */}
        <div className="md:col-span-2 space-y-8">
          
          {/* Skills & Projects */}
          <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
            <h3 className="font-display text-lg font-semibold text-ink">Parsed Profile Info</h3>
            <div className="space-y-4 text-xs">
              <div>
                <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider">Skills Directory</span>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {resumeInfo.skills.map((skill) => (
                    <span key={skill} className="inline-flex items-center gap-1 rounded-lg bg-white/60 border border-slate-200 px-2.5 py-1 text-xs text-ink">
                      {skill}
                    </span>
                  ))}
                  <button className="inline-flex items-center gap-1 rounded-lg border border-dashed border-slate-300 px-2 py-0.5 text-xs text-ink-soft hover:bg-white transition-colors">
                    <Plus className="h-3.5 w-3.5" /> Add Skill
                  </button>
                </div>
              </div>
              <div className="border-t border-white/20 pt-4">
                <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">Academic Summary</span>
                <p className="mt-1 text-ink leading-relaxed">
                  B.Tech Engineering Candidate, Indian Institute of Technology Roorkee (IITR). Expected graduation 2026.
                </p>
              </div>
            </div>
          </div>

          {/* Tailor Generation History */}
          <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <History className="h-4.5 w-4.5 text-ink" />
              <h3 className="font-display text-lg font-semibold text-ink">Optimization History</h3>
            </div>
            <div className="space-y-3">
              {resumeInfo.history.map((hist, idx) => (
                <div key={idx} className="flex items-center justify-between border-b border-white/10 pb-2 text-xs">
                  <div className="space-y-0.5">
                    <p className="font-semibold text-ink">{hist.changes}</p>
                    <span className="text-[10px] text-ink-soft">{hist.date}</span>
                  </div>
                  <span className="font-bold text-[color:var(--peach-deep)]">{hist.score}%</span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
