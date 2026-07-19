import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Sparkles, FileText, Upload, CheckCircle2, Cpu } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const Route = createFileRoute("/dashboard/resume-tailor")({
  component: ResumeTailorPage,
});

const TRUST_MESSAGES = [
  "Built around Google's XYZ framework.",
  "Optimized for ATS systems.",
  "Every bullet rewritten for measurable impact.",
  "Designed for humans. Optimized for ATS.",
  "Keywords added naturally. No keyword stuffing.",
  "Every resume receives an AI quality review."
];

function ResumeTailorPage() {
  const [selectedResume, setSelectedResume] = useState<string>("master_software_resume.pdf");
  const [jobDescription, setJobDescription] = useState<string>("");
  const [rotatingIndex, setRotatingIndex] = useState(0);
  const [isTailoring, setIsTailoring] = useState(false);
  const [tailoredReady, setTailoredReady] = useState(false);

  // Rotating trust message interval
  useEffect(() => {
    const interval = setInterval(() => {
      setRotatingIndex((prev) => (prev + 1) % TRUST_MESSAGES.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTailor = () => {
    if (!selectedResume || !jobDescription) return;
    setIsTailoring(true);
    setTimeout(() => {
      setIsTailoring(false);
      setTailoredReady(true);
    }, 3000);
  };

  return (
    <div className="max-w-5xl mx-auto px-8 py-12 space-y-12">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
          Resume Tailor
        </h1>
        <p className="text-sm text-ink-soft">
          Align your resume perfectly to any target opportunity.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Left Card: Select Resume */}
        <div className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm flex flex-col justify-between space-y-6">
          <div className="space-y-6">
            <h3 className="font-display text-lg font-semibold text-ink flex items-center gap-2">
              <FileText className="h-5 w-5 text-[color:var(--peach-deep)]" /> 1. Select Master Resume
            </h3>

            {/* Existing Resumes */}
            <div className="space-y-3">
              {[
                { name: "master_software_resume.pdf", type: "Full profile", date: "Uploaded 2 days ago" },
                { name: "frontend_developer_cv.pdf", type: "Custom tailored", date: "Uploaded 1 week ago" }
              ].map((res) => (
                <div
                  key={res.name}
                  onClick={() => setSelectedResume(res.name)}
                  className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                    selectedResume === res.name 
                      ? "border-[color:var(--peach-deep)] bg-white/60 shadow-sm" 
                      : "border-white/60 bg-white/20 hover:bg-white/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-ink">{res.name}</span>
                    <span className="text-[10px] uppercase font-bold text-ink-soft">{res.type}</span>
                  </div>
                  <span className="block text-[10px] text-ink-soft mt-1">{res.date}</span>
                </div>
              ))}
            </div>

            {/* Quick Upload option */}
            <div className="border border-dashed border-white/60 bg-white/20 rounded-2xl p-6 text-center space-y-2 hover:bg-white/30 transition-colors">
              <Upload className="h-5 w-5 text-ink-soft mx-auto" />
              <span className="block text-xs font-semibold text-ink">Or upload another file</span>
              <span className="text-[10px] text-ink-soft">PDF or DOCX max 5MB</span>
            </div>
          </div>
        </div>

        {/* Right Card: Job Description */}
        <div className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm flex flex-col justify-between space-y-6">
          <div className="space-y-4 flex-1 flex flex-col">
            <h3 className="font-display text-lg font-semibold text-ink flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[color:var(--peach-deep)]" /> 2. Paste Job Description
            </h3>

            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the complete Job Description here..."
              className="w-full flex-1 min-h-[160px] rounded-2xl border border-white/80 bg-white/30 p-4 text-xs text-ink placeholder:text-slate-400 focus:outline-none focus:border-[color:var(--peach-deep)] focus:bg-white/50 transition-all resize-none"
            />
          </div>

          <div className="space-y-4">
            <button
              onClick={handleTailor}
              disabled={!selectedResume || !jobDescription || isTailoring}
              className="btn-dark w-full py-3 text-xs rounded-xl flex items-center justify-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTailoring ? (
                <>
                  <Cpu className="h-3.5 w-3.5 animate-spin" /> Tailoring Resume...
                </>
              ) : tailoredReady ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> Tailored Copy Ready
                </>
              ) : (
                "Tailor Resume"
              )}
            </button>

            {/* Rotating Trust Messages */}
            <div className="h-4 overflow-hidden text-center">
              <AnimatePresence mode="wait">
                <motion.span
                  key={rotatingIndex}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.3 }}
                  className="text-[10px] text-ink-soft font-medium block"
                >
                  {TRUST_MESSAGES[rotatingIndex]}
                </motion.span>
              </AnimatePresence>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
