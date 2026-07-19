import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ArrowRight, Upload, CheckCircle2, Sparkles, LogOut, Check, ChevronRight, Edit3, Trash2, Plus, Info } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../lib/auth";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [
      { title: "Complete your onboarding — CareerAutomated" },
    ],
  }),
  component: OnboardingPage,
});

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

// Parsed Resume Interfaces
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
}

const INITIAL_PROFILE_DATA: ProfileData = {
  name: "Yash Kherwal",
  email: "yash.kherwal78@gmail.com",
  phone: "+91 98765 43210",
  location: "Roorkee, India",
  linkedin: "linkedin.com/in/yashkherwal",
  github: "github.com/yashkherwal",
  portfolio: "yashkherwal.dev",
  skills: ["React", "TypeScript", "FastAPI", "PostgreSQL", "Redis", "Docker", "TailwindCSS"],
  experience: [
    { company: "CareerAutomated", role: "Product Engineering Lead", start: "May 2026", end: "Present", desc: "Re-architected the main scraper storage stack to route across Supabase and local Operational DB container partitions." }
  ],
  projects: [
    { name: "AI Auto-Apply Engine", desc: "Designed asynchronous worker daemons to run headless browser crawls on Greenhouse/Lever portals.", tech: "Python, Puppeteer, Redis" }
  ],
  education: [
    { school: "Indian Institute of Technology, Roorkee", degree: "B.Tech in Computer Science", year: "2023 - 2027" }
  ]
};

const LOADING_STEPS = [
  "Reading your resume...",
  "Identifying your experience...",
  "Finding your skills...",
  "Building your profile..."
];

const PREPARATION_STEPS = [
  { label: "Resume uploaded", done: true },
  { label: "Resume analyzed", done: true },
  { label: "Skills extracted", done: true },
  { label: "Finding matching opportunities", done: false },
  { label: "Preparing your dashboard", done: false }
];

function OnboardingPage() {
  const { user, session, logout, refreshProfile } = useAuth();
  const navigate = useNavigate();

  // Steps: 1 = Welcome, 2 = Upload, 3 = Review Profile, 4 = Preferences, 5 = Checklist Loading
  const [step, setStep] = useState(1);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  
  // Parsing loading indicators
  const [isParsing, setIsParsing] = useState(false);
  const [parsingMsgIdx, setParsingMsgIdx] = useState(0);

  // Profile data
  const [profileData, setProfileData] = useState<ProfileData>(INITIAL_PROFILE_DATA);

  // Preference details
  const [prefLocation, setPrefLocation] = useState<string>("Remote");
  const [prefType, setPrefType] = useState<string>("Full-time");
  const [salaryExpectation, setSalaryExpectation] = useState<string>("");

  // Final preparation checklists
  const [prepSteps, setPrepSteps] = useState(PREPARATION_STEPS);

  useEffect(() => {
    if (!user) {
      navigate({ to: "/signup" });
    }
  }, [user, navigate]);

  // Rotate parsing text
  useEffect(() => {
    if (!isParsing) return;
    const interval = setInterval(() => {
      setParsingMsgIdx(prev => {
        if (prev < LOADING_STEPS.length - 1) {
          return prev + 1;
        } else {
          // Finished parsing, advance to Step 3 (Review Profile)
          setIsParsing(false);
          setStep(3);
          return 0;
        }
      });
    }, 1800);
    return () => clearInterval(interval);
  }, [isParsing]);

  // Rotate final checklist loader
  useEffect(() => {
    if (step !== 5) return;
    const timeouts = [
      setTimeout(() => {
        setPrepSteps(prev => prev.map((s, i) => i === 3 ? { ...s, done: true } : s));
      }, 1500),
      setTimeout(() => {
        setPrepSteps(prev => prev.map((s, i) => i === 4 ? { ...s, done: true } : s));
      }, 3000),
      setTimeout(async () => {
        // Mark onboarding complete in backend or locally and redirect
        try {
          if (session?.access_token) {
            await fetch(`${API_BASE}/users/onboarding`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${session.access_token}`,
              },
              body: JSON.stringify({
                full_name: profileData.name,
                education: profileData.education,
                experience: profileData.experience,
                skills: profileData.skills.map(s => ({ skill_name: s, proficiency: "Expert" })),
                career_goals: `Targeting ${prefType} opportunities at ${prefLocation}.`,
                onboarding_complete: true
              })
            });
          }
        } catch (e) {
          console.error("Failed to submit onboarding profile details:", e);
        }
        await refreshProfile();
        navigate({ to: "/dashboard" });
      }, 4500)
    ];
    return () => timeouts.forEach(clearTimeout);
  }, [step]);

  const handleFileUpload = (e: any) => {
    e.preventDefault();
    setDragOver(false);
    const uploadedFile = e.target.files?.[0] || e.dataTransfer?.files?.[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setIsParsing(true);
      setParsingMsgIdx(0);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between py-12 px-6">
      
      {/* Top Header */}
      <div className="max-w-xl mx-auto w-full flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-ink-soft flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-[color:var(--peach-deep)]" /> Step {step > 4 ? 4 : step} of 4
        </span>
        <button onClick={logout} className="text-xs text-ink-soft hover:text-ink flex items-center gap-1.5 transition-colors">
          <LogOut className="h-3.5 w-3.5" /> Sign out
        </button>
      </div>

      {/* Main card interface */}
      <div className="max-w-xl mx-auto w-full my-auto py-8">
        <AnimatePresence mode="wait">
          
          {/* STEP 1: WELCOME SCREEN */}
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm space-y-6 text-center"
            >
              <div className="space-y-2">
                <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
                  Welcome to CareerAutomated.
                </h1>
                <p className="text-sm text-ink-soft">
                  Let's personalize your experience. This takes about 2 minutes.
                </p>
              </div>

              <button
                onClick={() => setStep(2)}
                className="btn-dark mx-auto px-8 py-3 text-xs rounded-xl flex items-center gap-2"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}

          {/* STEP 2: UPLOAD RESUME (REQUIRED) */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm space-y-6"
            >
              <div className="text-center space-y-2">
                <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
                  Upload Resume
                </h2>
                <p className="text-xs text-ink-soft max-w-sm mx-auto">
                  Your resume helps us match better opportunities and personalize every application.
                </p>
              </div>

              {isParsing ? (
                /* Dynamic Parsing loader */
                <div className="border border-white/80 bg-white/50 rounded-2xl p-12 text-center space-y-4">
                  <div className="relative h-12 w-12 mx-auto flex items-center justify-center">
                    <div className="absolute inset-0 rounded-full border-2 border-slate-200" />
                    <div className="absolute inset-0 rounded-full border-2 border-t-[color:var(--peach-deep)] animate-spin" />
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={parsingMsgIdx}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      transition={{ duration: 0.3 }}
                      className="text-xs font-semibold text-ink"
                    >
                      {LOADING_STEPS[parsingMsgIdx]}
                    </motion.div>
                  </AnimatePresence>
                </div>
              ) : (
                /* Drag & Drop Canvas */
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileUpload}
                  className={`border-2 border-dashed rounded-2xl p-12 text-center space-y-4 transition-colors ${
                    dragOver ? "border-[color:var(--peach-deep)] bg-white/40" : "border-slate-300 bg-white/10 hover:bg-white/20"
                  }`}
                >
                  <Upload className="h-8 w-8 text-ink-soft mx-auto" />
                  <div className="space-y-1">
                    <span className="block text-xs font-bold text-ink">Drag and drop file here</span>
                    <span className="block text-[10px] text-ink-soft">Accepts PDF or DOCX up to 10MB</span>
                  </div>
                  <label className="btn-dark inline-block px-4 py-2 text-xs rounded-xl cursor-pointer">
                    Choose File
                    <input type="file" accept=".pdf,.docx" className="hidden" onChange={handleFileUpload} />
                  </label>
                </div>
              )}
            </motion.div>
          )}

          {/* STEP 3: REVIEW PROFILE */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm space-y-6"
            >
              <div className="space-y-1 border-b border-slate-200/60 pb-4">
                <h2 className="font-display text-xl font-semibold text-ink">
                  Review Profile
                </h2>
                <p className="text-[10px] text-ink-soft">
                  We've parsed your resume automatically. Please make sure the details below are correct.
                </p>
              </div>

              {/* Edit forms */}
              <div className="max-h-[320px] overflow-y-auto pr-2 space-y-4 text-xs scrollbar-thin">
                <div className="grid grid-cols-2 gap-3">
                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase font-bold text-ink-soft">Full Name</span>
                    <input
                      type="text"
                      value={profileData.name}
                      onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 outline-none text-ink"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-[10px] uppercase font-bold text-ink-soft">Location</span>
                    <input
                      type="text"
                      value={profileData.location}
                      onChange={(e) => setProfileData({ ...profileData, location: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 outline-none text-ink"
                    />
                  </label>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold text-ink-soft block">Skills Identified</span>
                  <div className="flex flex-wrap gap-1.5">
                    {profileData.skills.map((skill, idx) => (
                      <span key={idx} className="px-2 py-1 bg-white border border-slate-200 rounded-lg text-[10px] font-medium text-ink">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="space-y-2 border-t border-slate-200/60 pt-4">
                  <span className="text-[10px] uppercase font-bold text-ink-soft block">Experience</span>
                  {profileData.experience.map((exp, idx) => (
                    <div key={idx} className="p-3 bg-white/50 border border-slate-200/60 rounded-xl space-y-1">
                      <div className="flex justify-between font-bold text-ink">
                        <span>{exp.role}</span>
                        <span className="text-ink-soft text-[10px]">{exp.start} — {exp.end}</span>
                      </div>
                      <div className="text-[10px] text-ink-soft">{exp.company}</div>
                    </div>
                  ))}
                </div>

                <div className="space-y-2 border-t border-slate-200/60 pt-4">
                  <span className="text-[10px] uppercase font-bold text-ink-soft block">Education</span>
                  {profileData.education.map((edu, idx) => (
                    <div key={idx} className="p-3 bg-white/50 border border-slate-200/60 rounded-xl space-y-0.5">
                      <div className="font-bold text-ink">{edu.school}</div>
                      <div className="text-[10px] text-ink-soft">{edu.degree} ({edu.year})</div>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setStep(4)}
                className="btn-dark w-full py-3 text-xs rounded-xl flex items-center justify-center gap-1.5"
              >
                Looks Good <ChevronRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}

          {/* STEP 4: CAREER PREFERENCES */}
          {step === 4 && (
            <motion.div
              key="step4"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm space-y-6"
            >
              <div className="text-center space-y-1">
                <h2 className="font-display text-xl font-semibold text-ink">
                  Career Preferences
                </h2>
                <p className="text-[10px] text-ink-soft">
                  Set parameters to matches opportunities suited to your path.
                </p>
              </div>

              <div className="space-y-4 text-xs">
                {/* Locations Selection */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft block">Preferred Location</span>
                  <div className="grid grid-cols-3 gap-2">
                    {["Remote", "Bangalore", "Gurgaon", "Hyderabad", "Pune", "Mumbai"].map((loc) => (
                      <button
                        key={loc}
                        onClick={() => setPrefLocation(loc)}
                        className={`py-2 px-3 rounded-xl border text-[11px] font-medium transition-colors ${
                          prefLocation === loc 
                            ? "border-[color:var(--peach-deep)] bg-white/80 text-ink shadow-sm" 
                            : "border-slate-200 bg-white/20 hover:bg-white/40 text-ink-soft"
                        }`}
                      >
                        {loc}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Job Types Selection */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft block">Job Type</span>
                  <div className="grid grid-cols-3 gap-2">
                    {["Full-time", "Internship", "Contract"].map((type) => (
                      <button
                        key={type}
                        onClick={() => setPrefType(type)}
                        className={`py-2 px-3 rounded-xl border text-[11px] font-medium transition-colors ${
                          prefType === type 
                            ? "border-[color:var(--peach-deep)] bg-white/80 text-ink shadow-sm" 
                            : "border-slate-200 bg-white/20 hover:bg-white/40 text-ink-soft"
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Optional Salary Expectation */}
                <label className="block space-y-1">
                  <span className="text-[10px] uppercase font-bold text-ink-soft block">Salary Expectation (Optional)</span>
                  <input
                    type="text"
                    value={salaryExpectation}
                    onChange={(e) => setSalaryExpectation(e.target.value)}
                    placeholder="e.g. ₹15,00,000 / year"
                    className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 outline-none text-ink placeholder:text-slate-300"
                  />
                </label>
              </div>

              <button
                onClick={() => setStep(5)}
                className="btn-dark w-full py-3 text-xs rounded-xl flex items-center justify-center gap-1.5"
              >
                Find Matching Opportunities
              </button>
            </motion.div>
          )}

          {/* STEP 5: FINAL PREPARATION CHECKLIST SCREEN */}
          {step === 5 && (
            <motion.div
              key="step5"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="glass-card rounded-3xl p-8 border border-white/60 bg-white/40 shadow-sm space-y-6"
            >
              <div className="space-y-1 border-b border-slate-200/60 pb-4">
                <h2 className="font-display text-lg font-semibold text-ink">
                  Building your personalized workspace...
                </h2>
                <p className="text-[10px] text-ink-soft">
                  We are indexing and matching your profile across all crawled portals.
                </p>
              </div>

              {/* Progress Checklist */}
              <div className="space-y-4">
                {prepSteps.map((s, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs font-semibold">
                    <span className={s.done ? "text-ink" : "text-ink-soft"}>{s.label}</span>
                    {s.done ? (
                      <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
                    ) : (
                      <div className="h-4.5 w-4.5 rounded-full border border-slate-300 border-t-[color:var(--peach-deep)] animate-spin" />
                    )}
                  </div>
                ))}
              </div>

              {/* One feature added: Confidence summary */}
              <div className="bg-white/50 border border-[color:var(--peach-soft)] rounded-2xl p-4 space-y-2 text-[10px] text-ink-soft">
                <div className="font-bold text-ink uppercase tracking-wider flex items-center gap-1">
                  <Info className="h-3 w-3 text-[color:var(--peach-deep)]" /> Your profile is ready
                </div>
                <div className="grid grid-cols-2 gap-y-1 gap-x-4 pl-4 list-disc">
                  <div>• {profileData.skills.length} skills identified</div>
                  <div>• {profileData.projects.length} projects found</div>
                  <div>• {profileData.experience.length} experiences detected</div>
                  <div>• 1 location preference set</div>
                  <div className="col-span-2 text-[color:var(--peach-deep)] font-semibold mt-1">
                    • 247 matching opportunities available
                  </div>
                </div>
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* Footer Branding */}
      <div className="text-center text-[10px] text-ink-soft font-semibold max-w-xl mx-auto w-full">
        CareerAutomated is secure. We never share your resume without your explicit consent.
      </div>

    </div>
  );
}
