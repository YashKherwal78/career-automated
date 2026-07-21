import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ArrowRight, Upload, CheckCircle2, Sparkles, LogOut, Check, ChevronRight, Edit3, Trash2, Plus, Info, FileText, ArrowLeft, ShieldCheck } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../lib/auth";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [
      { title: "Personalize your CareerAutomated workspace" },
    ],
  }),
  component: OnboardingPage,
});

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

interface ExperienceItem {
  company: string;
  role: string;
  start: string;
  end: string;
  desc: string;
}

interface ProjectItem {
  name: string;
  desc: string;
  tech: string;
}

interface EducationItem {
  school: string;
  degree: string;
  year: string;
}

interface ProfileData {
  name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
  skills: string[];
  experience: ExperienceItem[];
  projects: ProjectItem[];
  education: EducationItem[];
  certifications: string[];
  achievements: string[];
}

const INITIAL_PARSED_PROFILE: ProfileData = {
  name: "Yash Kherwal",
  email: "yash.kherwal78@gmail.com",
  phone: "+91 98765 43210",
  location: "Roorkee, India",
  linkedin: "linkedin.com/in/yashkherwal",
  github: "github.com/yashkherwal",
  portfolio: "yashkherwal.dev",
  skills: ["React", "TypeScript", "FastAPI", "PostgreSQL", "Redis", "Docker", "TailwindCSS", "System Architecture", "Python"],
  experience: [
    { 
      company: "CareerAutomated", 
      role: "Lead Product Engineer", 
      start: "May 2026", 
      end: "Present", 
      desc: "Built high-throughput job discovery pipelines & automated application tailoring engines." 
    }
  ],
  projects: [
    { 
      name: "AI Autonomous Career OS", 
      desc: "Designed intelligent subagent orchestration layers for continuous hiring discovery.", 
      tech: "Python, FastAPI, React, Supabase" 
    }
  ],
  education: [
    { school: "Indian Institute of Technology, Roorkee", degree: "B.Tech in Computer Science", year: "2023 - 2027" }
  ],
  certifications: ["AWS Certified Solutions Architect", "TensorFlow Developer"],
  achievements: ["Winner - National Hackathon 2025", "Published Paper on Autonomous Agent Orchestration"]
};

const PROCESSING_STAGES = [
  "Reading resume document...",
  "Extracting personal & contact details...",
  "Parsing work experience & projects...",
  "Identifying technical skills & certifications...",
  "Generating candidate profile..."
];

const DASHBOARD_PREP_STEPS = [
  { label: "Original resume stored", done: true },
  { label: "Structured candidate profile generated", done: true },
  { label: "Profile preferences saved", done: true },
  { label: "Filtering top 0.1% matching opportunities", done: false },
  { label: "Configuring personalized dashboard", done: false }
];

function OnboardingPage() {
  const { user, session, logout, refreshProfile } = useAuth();
  const navigate = useNavigate();

  // Steps: 1 = Welcome, 2 = Upload, 3 = Review Profile, 4 = Preferences, 5 = Preparing Dashboard
  const [step, setStep] = useState(1);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  // Parsing indicator state
  const [isParsing, setIsParsing] = useState(false);
  const [parsingIndex, setParsingIndex] = useState(0);

  // Candidate Structured Profile (Source of Truth)
  const [profile, setProfile] = useState<ProfileData>(INITIAL_PARSED_PROFILE);

  // Preferences (Only what materially improves matching)
  const [prefLocation, setPrefLocation] = useState<string>("Remote");
  const [prefJobType, setPrefJobType] = useState<string>("Full-time");
  const [remotePreference, setRemotePreference] = useState<string>("Remote Only");

  // Editing state for Step 4
  const [newSkill, setNewSkill] = useState("");
  const [isEditingContact, setIsEditingContact] = useState(false);

  // Step 6 preparation checklist
  const [prepSteps, setPrepSteps] = useState(DASHBOARD_PREP_STEPS);

  useEffect(() => {
    if (!user) {
      navigate({ to: "/signup" });
    }
  }, [user, navigate]);

  // Parsing step animation sequence
  useEffect(() => {
    if (!isParsing) return;
    const interval = setInterval(() => {
      setParsingIndex((prev) => {
        if (prev < PROCESSING_STAGES.length - 1) {
          return prev + 1;
        } else {
          setIsParsing(false);
          setStep(3); // Proceed to Step 4 (Profile Review)
          return 0;
        }
      });
    }, 1600);
    return () => clearInterval(interval);
  }, [isParsing]);

  // Preparation sequence animation before navigating to dashboard
  useEffect(() => {
    if (step !== 5) return;

    const t1 = setTimeout(() => {
      setPrepSteps((prev) => prev.map((s, i) => (i === 3 ? { ...s, done: true } : s)));
    }, 1400);

    const t2 = setTimeout(() => {
      setPrepSteps((prev) => prev.map((s, i) => (i === 4 ? { ...s, done: true } : s)));
    }, 2800);

    const t3 = setTimeout(async () => {
      try {
        if (session?.access_token) {
          await fetch(`${API_BASE}/users/onboarding`, {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              full_name: profile.name,
              education: profile.education,
              experience: profile.experience,
              skills: profile.skills.map((s) => ({ skill_name: s, proficiency: "Expert" })),
              career_goals: `Targeting ${prefJobType} roles (${remotePreference}) in ${prefLocation}.`,
              onboarding_complete: true,
            }),
          });
        }
      } catch (err) {
        console.error("Failed to save onboarding metadata:", err);
      }
      await refreshProfile();
      navigate({ to: "/dashboard" });
    }, 4000);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [step]);

  const handleFileUpload = (e: any) => {
    e.preventDefault();
    setDragOver(false);
    const uploadedFile = e.target.files?.[0] || e.dataTransfer?.files?.[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setIsParsing(true);
      setParsingIndex(0);
    }
  };

  const handleAddSkill = () => {
    if (newSkill.trim() && !profile.skills.includes(newSkill.trim())) {
      setProfile({ ...profile, skills: [...profile.skills, newSkill.trim()] });
      setNewSkill("");
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setProfile({ ...profile, skills: profile.skills.filter((s) => s !== skillToRemove) });
  };

  return (
    <div className="min-h-screen bg-[color:var(--background)] flex flex-col justify-between p-6 md:p-12 font-sans selection:bg-[color:var(--peach-soft)]">
      
      {/* Top Bar Header */}
      <div className="max-w-xl mx-auto w-full flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded-md peach-gradient flex items-center justify-center font-display text-white text-xs font-bold">
            CA
          </div>
          <span className="font-display text-sm font-semibold text-ink">CareerAutomated</span>
        </div>

        <div className="flex items-center gap-4 text-xs text-ink-soft">
          {step > 1 && step < 5 && (
            <button
              onClick={() => setStep((prev) => prev - 1)}
              className="hover:text-ink flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
          )}
          <button onClick={logout} className="hover:text-ink flex items-center gap-1 transition-colors">
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>
      </div>

      {/* Main Experience Container */}
      <div className="max-w-xl mx-auto w-full my-auto py-6">
        <AnimatePresence mode="wait">
          
          {/* STEP 1: WELCOME */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="glass-card rounded-3xl p-8 md:p-10 text-center space-y-6"
            >
              <div className="space-y-3">
                <h1 className="font-display text-3xl md:text-4xl font-semibold tracking-tight text-ink leading-tight">
                  Welcome to CareerAutomated.
                </h1>
                <p className="text-sm text-ink-soft max-w-md mx-auto leading-relaxed">
                  We personalize your entire search using your resume. No long forms. Takes under 2 minutes.
                </p>
              </div>

              <div className="pt-4">
                <button
                  onClick={() => setStep(2)}
                  className="btn-dark w-full py-3.5 text-xs font-medium rounded-2xl flex items-center justify-center gap-2 group shadow-sm hover:shadow transition-all"
                >
                  Upload Resume to Get Started
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>

              <div className="flex items-center justify-center gap-1.5 text-[11px] text-ink-soft">
                <ShieldCheck className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" />
                <span>Your privacy is protected. We never share your data without consent.</span>
              </div>
            </motion.div>
          )}

          {/* STEP 2: RESUME UPLOAD & PARSING */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="glass-card rounded-3xl p-8 md:p-10 space-y-6"
            >
              <div className="text-center space-y-2">
                <h2 className="font-display text-2xl md:text-3xl font-semibold text-ink">
                  Upload Your Resume
                </h2>
                <p className="text-xs text-ink-soft max-w-sm mx-auto">
                  Your resume helps us surface high-fit opportunities and automatically tailor your applications.
                </p>
              </div>

              {isParsing ? (
                /* Stage-based processing loader */
                <div className="border hairline bg-white/60 rounded-2xl p-10 text-center space-y-5">
                  <div className="relative h-10 w-10 mx-auto flex items-center justify-center">
                    <div className="absolute inset-0 rounded-full border-2 border-slate-200" />
                    <div className="absolute inset-0 rounded-full border-2 border-t-[color:var(--peach-deep)] animate-spin" />
                  </div>
                  
                  <div className="space-y-1">
                    <AnimatePresence mode="wait">
                      <motion.div
                        key={parsingIndex}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -6 }}
                        transition={{ duration: 0.25 }}
                        className="text-xs font-semibold text-ink"
                      >
                        {PROCESSING_STAGES[parsingIndex]}
                      </motion.div>
                    </AnimatePresence>
                    <span className="text-[10px] text-ink-soft">Building your structured candidate profile...</span>
                  </div>
                </div>
              ) : (
                /* Drag & Drop canvas */
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileUpload}
                  className={`border-2 border-dashed rounded-2xl p-10 text-center space-y-4 transition-all ${
                    dragOver 
                      ? "border-[color:var(--peach-deep)] bg-[color:var(--peach-soft)]/40 scale-[1.01]" 
                      : "border-slate-300/80 bg-white/40 hover:bg-white/60 hover:border-slate-400"
                  }`}
                >
                  <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white/80 border hairline text-[color:var(--peach-deep)] mx-auto shadow-xs">
                    <Upload className="h-6 w-6" />
                  </div>

                  <div className="space-y-1">
                    <span className="block text-xs font-semibold text-ink">
                      Drag & drop your resume here, or browse
                    </span>
                    <span className="block text-[10px] text-ink-soft">
                      Supports PDF or DOCX format (up to 10MB)
                    </span>
                  </div>

                  <label className="btn-dark inline-flex px-5 py-2.5 text-xs font-medium rounded-xl cursor-pointer">
                    Select File
                    <input type="file" accept=".pdf,.docx" className="hidden" onChange={handleFileUpload} />
                  </label>
                </div>
              )}
            </motion.div>
          )}

          {/* STEP 3: PROFILE REVIEW */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="glass-card rounded-3xl p-8 md:p-10 space-y-6"
            >
              <div className="flex items-center justify-between border-b hairline pb-4">
                <div className="space-y-0.5">
                  <h2 className="font-display text-xl font-semibold text-ink">
                    Review Your Profile
                  </h2>
                  <p className="text-[11px] text-ink-soft">
                    Verify the extracted details below. Quick edits ensure 100% accurate matching.
                  </p>
                </div>
                <button
                  onClick={() => setIsEditingContact(!isEditingContact)}
                  className="text-xs text-[color:var(--peach-deep)] font-medium hover:underline flex items-center gap-1"
                >
                  <Edit3 className="h-3.5 w-3.5" /> {isEditingContact ? "Done" : "Edit Details"}
                </button>
              </div>

              <div className="max-h-[340px] overflow-y-auto pr-1 space-y-5 text-xs scrollbar-thin">
                {/* Personal Information */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Personal Information
                  </span>
                  
                  {isEditingContact ? (
                    <div className="grid grid-cols-2 gap-2 bg-white/60 p-3 rounded-2xl border hairline">
                      <input
                        type="text"
                        value={profile.name}
                        onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                        className="px-3 py-1.5 rounded-xl bg-white border hairline text-xs outline-none"
                        placeholder="Full Name"
                      />
                      <input
                        type="text"
                        value={profile.location}
                        onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                        className="px-3 py-1.5 rounded-xl bg-white border hairline text-xs outline-none"
                        placeholder="Location"
                      />
                    </div>
                  ) : (
                    <div className="flex items-center justify-between bg-white/50 p-3 rounded-2xl border hairline text-ink font-medium">
                      <div>
                        <div className="font-semibold">{profile.name}</div>
                        <div className="text-[10px] text-ink-soft">{profile.email} • {profile.location}</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Skills Section */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Extracted Skills ({profile.skills.length})
                  </span>
                  
                  <div className="flex flex-wrap gap-1.5">
                    {profile.skills.map((skill) => (
                      <span
                        key={skill}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border hairline text-[11px] font-medium text-ink shadow-2xs group"
                      >
                        {skill}
                        <button
                          onClick={() => handleRemoveSkill(skill)}
                          className="text-ink-soft hover:text-red-500 opacity-60 group-hover:opacity-100 transition-opacity"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      value={newSkill}
                      onChange={(e) => setNewSkill(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddSkill()}
                      placeholder="Add another skill (e.g. Next.js)..."
                      className="px-3 py-1.5 rounded-xl bg-white border hairline text-xs outline-none flex-1"
                    />
                    <button
                      onClick={handleAddSkill}
                      className="btn-ghost-ink px-3 py-1.5 text-xs rounded-xl flex items-center gap-1"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add
                    </button>
                  </div>
                </div>

                {/* Experience */}
                <div className="space-y-2 border-t hairline pt-3">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Work Experience
                  </span>
                  {profile.experience.map((exp, idx) => (
                    <div key={idx} className="p-3.5 bg-white/50 border hairline rounded-2xl space-y-1">
                      <div className="flex items-center justify-between font-semibold text-ink">
                        <span>{exp.role}</span>
                        <span className="text-[10px] text-ink-soft font-normal">{exp.start} — {exp.end}</span>
                      </div>
                      <div className="text-[11px] text-ink font-medium">{exp.company}</div>
                      <p className="text-[11px] text-ink-soft leading-relaxed">{exp.desc}</p>
                    </div>
                  ))}
                </div>

                {/* Education */}
                <div className="space-y-2 border-t hairline pt-3">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Education
                  </span>
                  {profile.education.map((edu, idx) => (
                    <div key={idx} className="p-3 bg-white/50 border hairline rounded-2xl flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-ink">{edu.school}</div>
                        <div className="text-[10px] text-ink-soft">{edu.degree}</div>
                      </div>
                      <span className="text-[10px] text-ink-soft font-medium">{edu.year}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setStep(4)}
                className="btn-dark w-full py-3.5 text-xs font-medium rounded-2xl flex items-center justify-center gap-1.5"
              >
                Profile Looks Great <ChevronRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}

          {/* STEP 4: CAREER PREFERENCES */}
          {step === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="glass-card rounded-3xl p-8 md:p-10 space-y-6"
            >
              <div className="text-center space-y-1.5">
                <h2 className="font-display text-2xl font-semibold text-ink">
                  Career Preferences
                </h2>
                <p className="text-xs text-ink-soft max-w-sm mx-auto">
                  Only set parameters that refine your match quality. We won't re-ask what's on your resume.
                </p>
              </div>

              <div className="space-y-5 text-xs">
                {/* Location Choice */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Preferred Location
                  </span>
                  <div className="grid grid-cols-3 gap-2">
                    {["Remote", "Bangalore", "Gurgaon", "Hyderabad", "Pune", "Mumbai"].map((loc) => (
                      <button
                        key={loc}
                        onClick={() => setPrefLocation(loc)}
                        className={`py-2.5 px-3 rounded-xl border text-[11px] font-medium transition-all ${
                          prefLocation === loc
                            ? "border-[color:var(--peach-deep)] bg-white text-ink shadow-xs"
                            : "border-slate-200/80 bg-white/30 text-ink-soft hover:text-ink"
                        }`}
                      >
                        {loc}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Job Type Choice */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Employment Type
                  </span>
                  <div className="grid grid-cols-3 gap-2">
                    {["Full-time", "Internship", "Contract"].map((type) => (
                      <button
                        key={type}
                        onClick={() => setPrefJobType(type)}
                        className={`py-2.5 px-3 rounded-xl border text-[11px] font-medium transition-all ${
                          prefJobType === type
                            ? "border-[color:var(--peach-deep)] bg-white text-ink shadow-xs"
                            : "border-slate-200/80 bg-white/30 text-ink-soft hover:text-ink"
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Remote Preference */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Remote Setup Preference
                  </span>
                  <div className="grid grid-cols-3 gap-2">
                    {["Remote Only", "Hybrid Flexible", "Onsite Accepted"].map((setup) => (
                      <button
                        key={setup}
                        onClick={() => setRemotePreference(setup)}
                        className={`py-2.5 px-3 rounded-xl border text-[11px] font-medium transition-all ${
                          remotePreference === setup
                            ? "border-[color:var(--peach-deep)] bg-white text-ink shadow-xs"
                            : "border-slate-200/80 bg-white/30 text-ink-soft hover:text-ink"
                        }`}
                      >
                        {setup}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setStep(5)}
                className="btn-dark w-full py-3.5 text-xs font-medium rounded-2xl flex items-center justify-center gap-1.5 shadow-sm"
              >
                Generate Matching Workspace
              </button>
            </motion.div>
          )}

          {/* STEP 5: PREPARING DASHBOARD */}
          {step === 5 && (
            <motion.div
              key="step5"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="glass-card rounded-3xl p-8 md:p-10 space-y-6"
            >
              <div className="space-y-1.5 border-b hairline pb-4">
                <h2 className="font-display text-xl font-semibold text-ink">
                  Preparing Your Personalized Workspace...
                </h2>
                <p className="text-[11px] text-ink-soft">
                  Our pipeline is analyzing your candidate profile against all active portal listings.
                </p>
              </div>

              {/* Progress items */}
              <div className="space-y-4">
                {prepSteps.map((s, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs font-medium">
                    <span className={s.done ? "text-ink font-semibold" : "text-ink-soft"}>{s.label}</span>
                    {s.done ? (
                      <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-slate-300 border-t-[color:var(--peach-deep)] animate-spin" />
                    )}
                  </div>
                ))}
              </div>

              {/* Confidence summary badge */}
              <div className="bg-white/60 border border-[color:var(--peach-soft)] rounded-2xl p-4 space-y-2 text-[11px] text-ink-soft">
                <div className="font-bold text-ink uppercase tracking-wider flex items-center gap-1.5 text-[10px]">
                  <Sparkles className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" /> Your AI Profile is Ready
                </div>
                <div className="grid grid-cols-2 gap-y-1 gap-x-4 pl-4 text-ink-soft">
                  <div>• {profile.skills.length} skills extracted</div>
                  <div>• {profile.experience.length} experiences indexed</div>
                  <div>• {profile.education.length} degrees verified</div>
                  <div>• 1 location preference set</div>
                  <div className="col-span-2 text-[color:var(--peach-deep)] font-semibold mt-1">
                    • Filtering top 0.1% matching opportunities
                  </div>
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="text-center text-[11px] text-ink-soft max-w-xl mx-auto w-full">
        CareerAutomated • High-agency AI career operating system
      </div>

    </div>
  );
}
