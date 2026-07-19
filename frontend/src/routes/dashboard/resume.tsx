import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { FileText, Upload, Plus, Trash2, ArrowLeft, Save, HelpCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const Route = createFileRoute("/dashboard/resume")({
  component: ResumePage,
});

interface ResumeData {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
  summary: string;
  skills: string[];
  experience: { company: string; role: string; start: string; end: string; desc: string }[];
  projects: { name: string; desc: string; tech: string }[];
  education: { school: string; degree: string; year: string }[];
  certifications: string[];
}

const INITIAL_RESUME_DATA: ResumeData = {
  name: "Yash Kherwal",
  email: "yash.kherwal78@gmail.com",
  phone: "+91 98765 43210",
  location: "Roorkee, India",
  linkedin: "linkedin.com/in/yashkherwal",
  github: "github.com/yashkherwal",
  portfolio: "yashkherwal.dev",
  summary: "High-agency product engineer studying at IIT Roorkee. Passionate about AI systems, vector search indexing, and crafting premium distraction-free interfaces.",
  skills: ["React", "TypeScript", "FastAPI", "PostgreSQL", "Redis", "Docker", "TailwindCSS"],
  experience: [
    { company: "CareerAutomated", role: "Product Engineering Lead", start: "May 2026", end: "Present", desc: "Re-architected the main scraper storage stack to route across Supabase and local Operational DB container partitions. Reduced storage overhead from 1.6 GB to under 50 MB using Cloudflare R2 migrations." }
  ],
  projects: [
    { name: "AI Auto-Apply Engine", desc: "Designed asynchronous worker daemons to run headless browser crawls on Greenhouse/Lever portals.", tech: "Python, Puppeteer, Redis" }
  ],
  education: [
    { school: "Indian Institute of Technology, Roorkee", degree: "B.Tech in Computer Science", year: "2023 - 2027" }
  ],
  certifications: ["AWS Certified Solutions Architect", "Google Cloud Associate Engineer"]
};

function ResumePage() {
  const [editorMode, setEditorMode] = useState<"onboarding" | "builder">("onboarding");
  const [resumeData, setResumeData] = useState<ResumeData>(INITIAL_RESUME_DATA);
  const [dragOver, setDragOver] = useState(false);

  // Resume builder add/remove helper utilities
  const addExperience = () => {
    setResumeData(prev => ({
      ...prev,
      experience: [...prev.experience, { company: "", role: "", start: "", end: "", desc: "" }]
    }));
  };

  const removeExperience = (index: number) => {
    setResumeData(prev => ({
      ...prev,
      experience: prev.experience.filter((_, i) => i !== index)
    }));
  };

  const addProject = () => {
    setResumeData(prev => ({
      ...prev,
      projects: [...prev.projects, { name: "", desc: "", tech: "" }]
    }));
  };

  const removeProject = (index: number) => {
    setResumeData(prev => ({
      ...prev,
      projects: prev.projects.filter((_, i) => i !== index)
    }));
  };

  const handleFileUpload = (e: any) => {
    e.preventDefault();
    setDragOver(false);
    // Mimic upload success and transition directly to the distraction-free builder editor
    setEditorMode("builder");
  };

  return (
    <div className="max-w-4xl mx-auto px-8 py-12">
      <AnimatePresence mode="wait">
        {editorMode === "onboarding" ? (
          /* 1. INITIAL SPLIT CARD STATE */
          <motion.div
            key="onboarding"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="space-y-12"
          >
            <div className="space-y-1">
              <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
                Your Resume
              </h1>
              <p className="text-sm text-ink-soft">
                Upload your document or craft a recruiter-ready version from scratch.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Left Card: Drag & Drop */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileUpload}
                className={`glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm flex flex-col justify-between items-center text-center space-y-8 min-h-[320px] transition-all duration-300 ${
                  dragOver ? "border-[color:var(--peach-deep)] bg-white/60 scale-[1.01]" : "hover:shadow-md"
                }`}
              >
                <div className="space-y-4">
                  <div className="h-12 w-12 rounded-2xl bg-[color:var(--peach-soft)] flex items-center justify-center mx-auto">
                    <Upload className="h-5 w-5 text-[color:var(--peach-deep)]" />
                  </div>
                  <h3 className="font-display text-lg font-semibold text-ink">Upload Resume</h3>
                  <p className="text-xs text-ink-soft max-w-[240px] mx-auto">
                    Drag and drop your master PDF/DOCX file here. We will parse your experience automatically.
                  </p>
                </div>
                
                <label className="btn-dark px-6 py-2.5 text-xs rounded-xl cursor-pointer">
                  Choose File
                  <input type="file" className="hidden" onChange={() => setEditorMode("builder")} />
                </label>
              </div>

              {/* Right Card: Distraction-free Builder */}
              <div className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm flex flex-col justify-between items-center text-center space-y-8 min-h-[320px] hover:shadow-md transition-all duration-300">
                <div className="space-y-4">
                  <div className="h-12 w-12 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto">
                    <FileText className="h-5 w-5 text-slate-500" />
                  </div>
                  <h3 className="font-display text-lg font-semibold text-ink">Create Resume</h3>
                  <p className="text-xs text-ink-soft max-w-[240px] mx-auto">
                    Create a recruiter-ready resume from scratch. Built using professional XYZ structures.
                  </p>
                </div>

                <button
                  onClick={() => setEditorMode("builder")}
                  className="btn-dark px-6 py-2.5 text-xs rounded-xl"
                >
                  Start Building
                </button>
              </div>
            </div>
          </motion.div>
        ) : (
          /* 2. DISTRACTION-FREE NOTION-LIKE RESUME BUILDER */
          <motion.div
            key="builder"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            className="space-y-8"
          >
            {/* Action Bar */}
            <div className="flex items-center justify-between border-b border-white/20 pb-4">
              <button
                onClick={() => setEditorMode("onboarding")}
                className="flex items-center gap-1.5 text-xs text-ink-soft hover:text-ink transition-colors"
              >
                <ArrowLeft className="h-3.5 w-3.5" /> Back to Dashboard
              </button>

              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-500 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" /> Auto-saved
                </span>
                <button
                  onClick={() => setEditorMode("onboarding")}
                  className="btn-dark px-4 py-1.5 text-xs rounded-xl flex items-center gap-1.5"
                >
                  <Save className="h-3.5 w-3.5" /> Finish Editing
                </button>
              </div>
            </div>

            {/* Notion Editor canvas */}
            <div className="space-y-12 py-4">
              
              {/* Header / Personal Details */}
              <div className="space-y-4">
                <input
                  type="text"
                  value={resumeData.name}
                  onChange={(e) => setResumeData({ ...resumeData, name: e.target.value })}
                  placeholder="Your Full Name"
                  className="w-full bg-transparent font-display text-4xl font-bold tracking-tight text-ink border-none outline-none focus:ring-0 placeholder:text-slate-300"
                />
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                  <input
                    type="email"
                    value={resumeData.email}
                    onChange={(e) => setResumeData({ ...resumeData, email: e.target.value })}
                    placeholder="email@address.com"
                    className="bg-transparent border-b border-dashed border-slate-300 focus:border-ink py-1 outline-none text-ink"
                  />
                  <input
                    type="text"
                    value={resumeData.phone}
                    onChange={(e) => setResumeData({ ...resumeData, phone: e.target.value })}
                    placeholder="Phone number"
                    className="bg-transparent border-b border-dashed border-slate-300 focus:border-ink py-1 outline-none text-ink"
                  />
                  <input
                    type="text"
                    value={resumeData.location}
                    onChange={(e) => setResumeData({ ...resumeData, location: e.target.value })}
                    placeholder="Location"
                    className="bg-transparent border-b border-dashed border-slate-300 focus:border-ink py-1 outline-none text-ink"
                  />
                  <input
                    type="text"
                    value={resumeData.portfolio}
                    onChange={(e) => setResumeData({ ...resumeData, portfolio: e.target.value })}
                    placeholder="portfolio.dev"
                    className="bg-transparent border-b border-dashed border-slate-300 focus:border-ink py-1 outline-none text-ink"
                  />
                </div>
              </div>

              {/* Professional Summary */}
              <div className="space-y-2">
                <h3 className="text-xs uppercase font-bold tracking-widest text-ink-soft">Summary</h3>
                <textarea
                  value={resumeData.summary}
                  onChange={(e) => setResumeData({ ...resumeData, summary: e.target.value })}
                  placeholder="Introduce yourself and specify your target roles..."
                  rows={2}
                  className="w-full bg-transparent text-sm leading-relaxed text-ink border-none outline-none focus:ring-0 resize-none"
                />
              </div>

              {/* Experience Block */}
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <h3 className="text-xs uppercase font-bold tracking-widest text-ink-soft">Experience</h3>
                  <button
                    onClick={addExperience}
                    className="inline-flex items-center gap-1 text-xs text-[color:var(--peach-deep)] hover:underline"
                  >
                    <Plus className="h-3 w-3" /> Add Experience
                  </button>
                </div>

                <div className="space-y-8">
                  {resumeData.experience.map((exp, idx) => (
                    <div key={idx} className="relative group space-y-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={exp.role}
                            placeholder="Role Title"
                            onChange={(e) => {
                              const expCopy = [...resumeData.experience];
                              expCopy[idx].role = e.target.value;
                              setResumeData({ ...resumeData, experience: expCopy });
                            }}
                            className="bg-transparent font-medium text-sm text-ink outline-none border-b border-transparent focus:border-slate-300"
                          />
                          <span className="text-slate-300">at</span>
                          <input
                            type="text"
                            value={exp.company}
                            placeholder="Company Name"
                            onChange={(e) => {
                              const expCopy = [...resumeData.experience];
                              expCopy[idx].company = e.target.value;
                              setResumeData({ ...resumeData, experience: expCopy });
                            }}
                            className="bg-transparent font-medium text-sm text-ink outline-none border-b border-transparent focus:border-slate-300"
                          />
                        </div>

                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={exp.start}
                            placeholder="Start date"
                            className="bg-transparent text-xs text-ink-soft text-right w-20 outline-none"
                            onChange={(e) => {
                              const expCopy = [...resumeData.experience];
                              expCopy[idx].start = e.target.value;
                              setResumeData({ ...resumeData, experience: expCopy });
                            }}
                          />
                          <span className="text-slate-300">—</span>
                          <input
                            type="text"
                            value={exp.end}
                            placeholder="End date"
                            className="bg-transparent text-xs text-ink-soft w-20 outline-none"
                            onChange={(e) => {
                              const expCopy = [...resumeData.experience];
                              expCopy[idx].end = e.target.value;
                              setResumeData({ ...resumeData, experience: expCopy });
                            }}
                          />
                          
                          <button
                            onClick={() => removeExperience(idx)}
                            className="text-red-400 opacity-0 group-hover:opacity-100 hover:text-red-600 transition-opacity ml-2"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      <textarea
                        value={exp.desc}
                        placeholder="Detail your responsibilities and XYZ achievements..."
                        rows={2}
                        onChange={(e) => {
                          const expCopy = [...resumeData.experience];
                          expCopy[idx].desc = e.target.value;
                          setResumeData({ ...resumeData, experience: expCopy });
                        }}
                        className="w-full bg-transparent text-xs leading-relaxed text-ink-soft border-none outline-none focus:ring-0 resize-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Projects Block */}
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <h3 className="text-xs uppercase font-bold tracking-widest text-ink-soft">Projects</h3>
                  <button
                    onClick={addProject}
                    className="inline-flex items-center gap-1 text-xs text-[color:var(--peach-deep)] hover:underline"
                  >
                    <Plus className="h-3 w-3" /> Add Project
                  </button>
                </div>

                <div className="space-y-6">
                  {resumeData.projects.map((proj, idx) => (
                    <div key={idx} className="relative group space-y-2">
                      <div className="flex items-center justify-between">
                        <input
                          type="text"
                          value={proj.name}
                          placeholder="Project Name"
                          onChange={(e) => {
                            const projCopy = [...resumeData.projects];
                            projCopy[idx].name = e.target.value;
                            setResumeData({ ...resumeData, projects: projCopy });
                          }}
                          className="bg-transparent font-medium text-sm text-ink outline-none border-b border-transparent focus:border-slate-300"
                        />
                        <button
                          onClick={() => removeProject(idx)}
                          className="text-red-400 opacity-0 group-hover:opacity-100 hover:text-red-600 transition-opacity"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>

                      <textarea
                        value={proj.desc}
                        placeholder="Briefly describe project functions..."
                        rows={1}
                        onChange={(e) => {
                          const projCopy = [...resumeData.projects];
                          projCopy[idx].desc = e.target.value;
                          setResumeData({ ...resumeData, projects: projCopy });
                        }}
                        className="w-full bg-transparent text-xs text-ink-soft border-none outline-none focus:ring-0 resize-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
