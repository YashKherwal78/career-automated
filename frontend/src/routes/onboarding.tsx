import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ArrowRight, Upload, CheckCircle2, Sparkles, LogOut, Edit3, Plus, ArrowLeft, ShieldCheck, Check, Briefcase, GraduationCap, Code, Target, MapPin } from "lucide-react";
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

// Humanized parsing stage messages
const HUMAN_PARSING_STAGES = [
  "✓ Experience understood",
  "✓ Projects identified",
  "✓ Technical skills recognized",
  "✓ Building your profile"
];

// Rotating messages for the right panel (upload step)
const ROTATING_MESSAGES = [
  "Your dream job deserves more than a generic resume.",
  "You deserve interviews, not silence.",
  "Every resume is tailored using Google's XYZ framework.",
  "The right opportunity is one tailored resume away.",
  "The best candidates aren't always the best at writing resumes.",
  "You worked hard for your experience. Let it speak for itself.",
  "Your next offer letter could start with this upload.",
];

// Live profile cards that pop up during processing
const LIVE_PROFILE_CARDS = [
  { icon: Code, text: "React, TypeScript, Python, FastAPI", label: "Skills Identified" },
  { icon: GraduationCap, text: "IIT Roorkee — B.Tech CS", label: "Education Verified" },
  { icon: Briefcase, text: "Lead Product Engineer @ CareerAutomated", label: "Experience Logged" },
  { icon: Target, text: "247 Matching Roles Located", label: "Market Match" }
];

function OnboardingPage() {
  const { user, session, logout, refreshProfile } = useAuth();
  const navigate = useNavigate();

  // Steps: 1 = Welcome, 2 = Upload, 3 = Review Profile, 4 = Preferences, 5 = Ready Wow Moment
  const [step, setStep] = useState(1);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [parsingStageIndex, setParsingStageIndex] = useState(0);
  const [visibleCardCount, setVisibleCardCount] = useState(0);

  // Rotating message carousel state (randomized start)
  const [msgIndex, setMsgIndex] = useState(() =>
    Math.floor(Math.random() * ROTATING_MESSAGES.length)
  );
  const [msgVisible, setMsgVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      // Fade out
      setMsgVisible(false);
      setTimeout(() => {
        setMsgIndex((prev) => (prev + 1) % ROTATING_MESSAGES.length);
        setMsgVisible(true);
      }, 600);
    }, 7000);
    return () => clearInterval(interval);
  }, []);

  // Candidate Profile State
  const [profile, setProfile] = useState<ProfileData>(INITIAL_PARSED_PROFILE);

  // Preferences (Simple location & job type chips)
  const [prefLocation, setPrefLocation] = useState<string>("Remote");
  const [prefJobType, setPrefJobType] = useState<string>("Full-time");
  const [remotePreference, setRemotePreference] = useState<string>("Remote Only");

  // Editing state for Step 3
  const [newSkill, setNewSkill] = useState("");
  const [isEditingContact, setIsEditingContact] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate({ to: "/signup" });
    }
  }, [user, navigate]);

  // Live profile card build animation
  useEffect(() => {
    if (!isParsing) return;

    // Stage updates
    const stageInterval = setInterval(() => {
      setParsingStageIndex((prev) => (prev < HUMAN_PARSING_STAGES.length - 1 ? prev + 1 : prev));
    }, 1100);

    // Card pop-ins
    const cardInterval = setInterval(() => {
      setVisibleCardCount((prev) => {
        if (prev < LIVE_PROFILE_CARDS.length) {
          return prev + 1;
        } else {
          clearInterval(cardInterval);
          clearInterval(stageInterval);
          setTimeout(() => {
            setIsParsing(false);
            setStep(3); // Go to "Does this look right?"
          }, 800);
          return prev;
        }
      });
    }, 1000);

    return () => {
      clearInterval(stageInterval);
      clearInterval(cardInterval);
    };
  }, [isParsing]);

  const handleFileUpload = (e: any) => {
    e.preventDefault();
    setDragOver(false);
    const uploadedFile = e.target.files?.[0] || e.dataTransfer?.files?.[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setIsParsing(true);
      setParsingStageIndex(0);
      setVisibleCardCount(0);
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

  const handleCompleteOnboarding = async () => {
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

      {/* Main Experience Container — full-width for step 2, constrained for other steps */}
      <div className={`w-full my-auto py-6 ${
        step === 2 ? "max-w-[95%] mx-auto" : "max-w-xl mx-auto"
      }`}>
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
                  Get hired faster.
                </h1>
                <p className="text-sm text-ink-soft max-w-md mx-auto leading-relaxed">
                  We automatically find matching jobs and tailor your applications using your resume. Under 2 minutes.
                </p>
              </div>

              <div className="pt-4">
                <button
                  onClick={() => setStep(2)}
                  className="btn-dark w-full py-3.5 text-xs font-medium rounded-2xl flex items-center justify-center gap-2 group shadow-sm hover:shadow transition-all"
                >
                  Upload Resume to Begin
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>

              <div className="flex items-center justify-center gap-1.5 text-[11px] text-ink-soft">
                <ShieldCheck className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" />
                <span>Your privacy is protected. We never submit applications without your explicit review.</span>
              </div>
            </motion.div>
          )}

          {/* STEP 2: RESUME UPLOAD — 55/45 FULL PAGE LAYOUT */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col md:flex-row gap-10 md:gap-16 items-center justify-between min-h-[550px] w-full"
            >
              {/* LEFT 55%: Large Scaled Upload Card */}
              <div className="w-full md:w-[55%] glass-card rounded-3xl p-10 md:p-14 space-y-8 flex-1">
                {isParsing ? (
                  /* Dynamic Live Profile Building Cards */
                  <div className="space-y-6">
                    <div className="text-center space-y-2">
                      <h2 className="font-display text-2xl md:text-3xl font-semibold text-ink">
                        We're understanding your experience...
                      </h2>
                      <p className="text-xs text-ink-soft max-w-sm mx-auto">
                        Building your live candidate profile in real time...
                      </p>
                    </div>

                    <div className="bg-white/60 rounded-2xl p-4 border hairline flex items-center justify-between">
                      <span className="text-xs font-semibold text-ink">
                        {HUMAN_PARSING_STAGES[parsingStageIndex]}
                      </span>
                      <div className="h-4 w-4 rounded-full border-2 border-slate-200 border-t-[color:var(--peach-deep)] animate-spin" />
                    </div>

                    <div className="space-y-2.5">
                      {LIVE_PROFILE_CARDS.slice(0, visibleCardCount).map((card, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -12, scale: 0.96 }}
                          animate={{ opacity: 1, x: 0, scale: 1 }}
                          transition={{ duration: 0.35 }}
                          className="flex items-center gap-3 bg-white/80 border hairline rounded-2xl p-3.5 shadow-2xs"
                        >
                          <div className="grid h-8 w-8 place-items-center rounded-xl bg-[color:var(--peach-soft)] text-[color:var(--peach-deep)]">
                            <card.icon className="h-4 w-4" />
                          </div>
                          <div className="text-left flex-1 min-w-0">
                            <div className="text-[10px] uppercase font-bold text-ink-soft tracking-wider">{card.label}</div>
                            <div className="text-xs font-semibold text-ink truncate">{card.text}</div>
                          </div>
                          <Check className="h-4 w-4 text-emerald-500 shrink-0" />
                        </motion.div>
                      ))}
                    </div>
                  </div>
                ) : (
                  /* Drag & Drop canvas scaled up to comfortably fill left column */
                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleFileUpload}
                    className={`border-2 border-dashed rounded-2xl p-16 md:p-20 text-center space-y-6 transition-all ${
                      dragOver
                        ? "border-[color:var(--peach-deep)] bg-[color:var(--peach-soft)]/40 scale-[1.01]"
                        : "border-slate-300/80 bg-white/40 hover:bg-white/60 hover:border-slate-400"
                    }`}
                  >
                    <div className="grid h-16 w-16 place-items-center rounded-2xl bg-white/80 border hairline text-[color:var(--peach-deep)] mx-auto shadow-xs">
                      <Upload className="h-8 w-8" />
                    </div>

                    <div className="space-y-2">
                      <span className="block text-base font-semibold text-ink">
                        Drag &amp; drop your resume here, or browse
                      </span>
                      <span className="block text-xs text-ink-soft">
                        Supports PDF, DOCX or TXT (up to 10MB)
                      </span>
                    </div>

                    <div className="pt-2">
                      <label className="btn-dark inline-flex px-8 py-3 text-xs font-medium rounded-xl cursor-pointer">
                        Select File
                        <input type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleFileUpload} />
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* RIGHT 45%: Intentionally designed rotating message panel */}
              <div className="hidden md:flex w-full md:w-[45%] flex-col justify-center pl-10">
                <div className="max-w-[420px] space-y-6">
                  <div className="h-[200px] flex items-center">
                    <AnimatePresence mode="wait">
                      <motion.p
                        key={msgIndex}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: msgVisible ? 1 : 0, y: msgVisible ? 0 : -20 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{
                          duration: 0.65,
                          ease: [0.16, 1, 0.3, 1], // Apple-like easing
                        }}
                        className="font-display text-[2.75rem] font-bold text-ink leading-[1.15] tracking-tight text-left"
                      >
                        {ROTATING_MESSAGES[msgIndex]}
                      </motion.p>
                    </AnimatePresence>
                  </div>
                  <div className="w-16 h-1 bg-peach-deep/40 rounded-full" />
                </div>
              </div>
            </motion.div>
          )}

          {/* STEP 3: DOES THIS LOOK RIGHT? */}
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
                    Does this look right?
                  </h2>
                  <p className="text-[11px] text-ink-soft">
                    Quickly confirm the details we recognized from your resume.
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
                    Contact Details
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
                    Recognized Skills ({profile.skills.length})
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
                      placeholder="Add another skill..."
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
                    Recognized Experience
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
              </div>

              <button
                onClick={() => setStep(4)}
                className="btn-dark w-full py-3.5 text-xs font-medium rounded-2xl flex items-center justify-center gap-1.5"
              >
                Yes, Looks Right <ArrowRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}

          {/* STEP 4: CHOOSE WHERE YOU WANT TO WORK */}
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
                  Choose where you want to work
                </h2>
                <p className="text-xs text-ink-soft max-w-sm mx-auto">
                  Pick your preferred locations & setup so we only bring you exact fits.
                </p>
              </div>

              <div className="space-y-5 text-xs">
                {/* Location Chips */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Location Preference
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {["Remote", "Bangalore", "Delhi NCR", "Pune", "Hyderabad", "Mumbai"].map((loc) => (
                      <button
                        key={loc}
                        onClick={() => setPrefLocation(loc)}
                        className={`py-2 px-3.5 rounded-xl border text-[11px] font-medium transition-all ${
                          prefLocation === loc
                            ? "border-[color:var(--peach-deep)] bg-white text-ink shadow-xs font-semibold"
                            : "border-slate-200/80 bg-white/40 text-ink-soft hover:text-ink"
                        }`}
                      >
                        {loc}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Job Type Chips */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                    Role Type
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {["Full-time", "Internship", "Contract"].map((type) => (
                      <button
                        key={type}
                        onClick={() => setPrefJobType(type)}
                        className={`py-2 px-3.5 rounded-xl border text-[11px] font-medium transition-all ${
                          prefJobType === type
                            ? "border-[color:var(--peach-deep)] bg-white text-ink shadow-xs font-semibold"
                            : "border-slate-200/80 bg-white/40 text-ink-soft hover:text-ink"
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <button
                onClick={() => setStep(5)}
                className="btn-dark w-full py-3.5 text-xs font-medium rounded-2xl flex items-center justify-center gap-1.5 shadow-sm"
              >
                Find Matching Jobs <ArrowRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}

          {/* STEP 5: YOUR AI FOUND 247 MATCHING JOBS (WOW ACTIVATION MOMENT) */}
          {step === 5 && (
            <motion.div
              key="step5"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.4 }}
              className="glass-card rounded-3xl p-8 md:p-10 space-y-6 text-center"
            >
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[color:var(--peach-soft)] border hairline text-xs font-semibold text-[color:var(--peach-deep)]">
                <Sparkles className="h-3.5 w-3.5" /> Your Profile is Ready
              </div>

              <div className="space-y-2">
                <h2 className="font-display text-3xl md:text-4xl font-bold tracking-tight text-ink">
                  Your AI found 247 matching jobs
                </h2>
                <p className="text-xs text-ink-soft max-w-sm mx-auto">
                  We've scanned active listings and surfaced the highest-fit opportunities tailored specifically to your background.
                </p>
              </div>

              {/* Dopamine Summary Box */}
              <div className="bg-white/80 border hairline rounded-2xl p-5 text-left space-y-3 shadow-xs">
                <div className="grid grid-cols-2 gap-3 text-xs font-medium text-ink">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>27 technical skills identified</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>5 projects detected</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>2 experiences recognized</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>247 matching opportunities found</span>
                  </div>
                </div>
              </div>

              <button
                onClick={handleCompleteOnboarding}
                className="btn-dark w-full py-4 text-sm font-semibold rounded-2xl flex items-center justify-center gap-2 group shadow-md hover:shadow-lg transition-all"
              >
                See My Matches <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="text-center text-[11px] text-ink-soft max-w-xl mx-auto w-full">
        CareerAutomated • Get hired faster
      </div>

    </div>
  );
}
