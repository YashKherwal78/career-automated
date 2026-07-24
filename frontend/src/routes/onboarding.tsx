import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  ArrowRight, Upload, CheckCircle2, Sparkles, LogOut, Edit3, Plus, ArrowLeft, 
  ShieldCheck, Check, Briefcase, GraduationCap, Code, Target, MapPin, 
  Trash2, PlusCircle, ChevronDown, ChevronUp, ExternalLink, Award, FileText, 
  Info, Sparkle, Loader2, ArrowUp, ArrowDown 
} from "lucide-react";
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

// Schema definitions matching backend ResumeParserService
interface PersonalInfo {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  linkedin: string | null;
  github: string | null;
  portfolio: string | null;
}

interface EducationEntry {
  institution: string;
  degree: string | null;
  field_of_study: string | null;
  gpa: string | null;
  start_date: string | null;
  end_date: string | null;
  location: string | null;
}

interface ExperienceEntry {
  company: string;
  role: string;
  employment_type: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  current_position: boolean;
  bullet_points: string[];
  technologies: string[];
}

interface ProjectEntry {
  name: string;
  description: string | null;
  technologies: string[];
  github_link: string | null;
  live_link: string | null;
}

interface SkillsCategorized {
  programming_languages: string[];
  frameworks: string[];
  libraries: string[];
  databases: string[];
  cloud: string[];
  ai_ml: string[];
  developer_tools: string[];
  other: string[];
}

interface CertificationEntry {
  name: string;
  issuer: string | null;
  date: string | null;
}

interface PublicationEntry {
  title: string;
  publisher: string | null;
  date: string | null;
}

interface ExternalLinkEntry {
  label: string;
  url: string;
}

interface ProfileData {
  personal_info: PersonalInfo;
  summary: string | null;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  skills: SkillsCategorized;
  certifications: CertificationEntry[];
  achievements: string[];
  awards: string[];
  publications: PublicationEntry[];
  languages: string[];
  external_links: ExternalLinkEntry[];
  resume_url?: string;
  resume_file_name?: string;
}

const INITIAL_PARSED_PROFILE: ProfileData = {
  personal_info: {
    full_name: "",
    email: "",
    phone: "",
    location: "",
    linkedin: "",
    github: "",
    portfolio: ""
  },
  summary: "",
  education: [],
  experience: [],
  projects: [],
  skills: {
    programming_languages: [],
    frameworks: [],
    libraries: [],
    databases: [],
    cloud: [],
    ai_ml: [],
    developer_tools: [],
    other: []
  },
  certifications: [],
  achievements: [],
  awards: [],
  publications: [],
  languages: [],
  external_links: []
};

// Premium progress stages for UX during parsing
const UX_PARSING_STAGES = [
  "Uploading resume...",
  "Reading document...",
  "Understanding your experience...",
  "Identifying projects...",
  "Organizing skills...",
  "Building your candidate profile..."
];

const ROTATING_MESSAGES = [
  "Your dream job deserves more than a generic resume.",
  "You deserve interviews, not silence.",
  "Every resume is tailored using Google's XYZ framework.",
  "The right opportunity is one tailored resume away.",
  "The best candidates aren't always the best at writing resumes.",
  "You worked hard for your experience. Let it speak for itself.",
  "Your next offer letter could start with this upload.",
];

function OnboardingPage() {
  const { user, session, logout, refreshProfile } = useAuth();
  const navigate = useNavigate();

  // Steps: 1 = Welcome, 2 = Uploading & Rotating messages, 3 = Review Profile, 4 = Preferences, 5 = Wow Ready
  const [step, setStep] = useState(1);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [parsingStageIndex, setParsingStageIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Profile data state
  const [profile, setProfile] = useState<ProfileData>(INITIAL_PARSED_PROFILE);

  // Preferences (Step 4)
  const [prefLocation, setPrefLocation] = useState<string>("Remote");
  const [prefJobType, setPrefJobType] = useState<string>("Full-time");
  const [remotePreference, setRemotePreference] = useState<string>("Remote Only");

  // Rotating messages carousel state
  const [msgIndex, setMsgIndex] = useState(() =>
    Math.floor(Math.random() * ROTATING_MESSAGES.length)
  );
  const [msgVisible, setMsgVisible] = useState(true);

  // Accordion active keys for Step 3
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    personal: true,
    summary: true,
    experience: true,
    education: true,
    projects: true,
    skills: true,
    certifications: false,
    achievements: false,
    links: false
  });

  const toggleSection = (sec: string) => {
    setOpenSections(prev => ({ ...prev, [sec]: !prev[sec] }));
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgVisible(false);
      setTimeout(() => {
        setMsgIndex((prev) => (prev + 1) % ROTATING_MESSAGES.length);
        setMsgVisible(true);
      }, 600);
    }, 7000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!user) {
      navigate({ to: "/signup" });
    }
  }, [user, navigate]);

  // UX step increment simulation while parsing
  useEffect(() => {
    if (!isParsing) return;
    const stageInterval = setInterval(() => {
      setParsingStageIndex((prev) => {
        if (prev < UX_PARSING_STAGES.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 1500);
    return () => clearInterval(stageInterval);
  }, [isParsing]);

  const handleFileUpload = async (e: any) => {
    e.preventDefault();
    setDragOver(false);
    setErrorMessage(null);
    const uploadedFile = e.target.files?.[0] || e.dataTransfer?.files?.[0];
    if (!uploadedFile) return;

    setFile(uploadedFile);
    setIsParsing(true);
    setParsingStageIndex(0);

    const formData = new FormData();
    formData.append("file", uploadedFile);

    try {
      const response = await fetch(`${API_BASE}/users/parse_resume`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to parse resume");
      }

      const data = await response.json();
      setProfile(data);
      
      // Complete parsing cycle gracefully
      setParsingStageIndex(UX_PARSING_STAGES.length - 1);
      setTimeout(() => {
        setIsParsing(false);
        setStep(3); // Go to review screen
      }, 1000);

    } catch (err: any) {
      console.error(err);
      setErrorMessage(err.message || "An error occurred during resume processing.");
      setIsParsing(false);
    }
  };

  // Reorder items
  const moveItem = (section: "education" | "experience" | "projects" | "certifications" | "external_links", index: number, direction: "up" | "down") => {
    const list = [...profile[section]] as any[];
    if (direction === "up" && index > 0) {
      const temp = list[index];
      list[index] = list[index - 1];
      list[index - 1] = temp;
    } else if (direction === "down" && index < list.length - 1) {
      const temp = list[index];
      list[index] = list[index + 1];
      list[index + 1] = temp;
    }
    setProfile({ ...profile, [section]: list });
  };

  const handleCompleteOnboarding = async () => {
    try {
      if (session?.access_token) {
        // Prepare list-format skills for backend onboarding payload compat
        const allSkillsFlat = Object.values(profile.skills)
          .flat()
          .filter(Boolean)
          .map(s => ({ skill_name: s, proficiency: "Expert" }));

        await fetch(`${API_BASE}/users/onboarding`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            full_name: profile.personal_info.full_name || "Verified Candidate",
            education: profile.education.map(e => ({
              institution: e.institution,
              degree: e.degree,
              field_of_study: e.field_of_study,
              start_year: e.start_date ? parseInt(e.start_date.split(" ")[1]) || null : null,
              end_year: e.end_date ? parseInt(e.end_date.split(" ")[1]) || null : null
            })),
            experience: profile.experience.map(e => ({
              company: e.company,
              title: e.role,
              start_date: e.start_date,
              end_date: e.end_date,
              description: e.bullet_points.join("\n")
            })),
            skills: allSkillsFlat,
            resume_url: profile.resume_url,
            resume_file_name: profile.resume_file_name,
            career_goals: `Targeting ${prefJobType} roles (${remotePreference}) in ${prefLocation}.`,
          }),
        });
      }
    } catch (err) {
      console.error("Failed to save verified onboarding metadata:", err);
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

      {/* Main Experience Container */}
      <div className={`w-full my-auto py-6 ${
        step === 2 ? "max-w-[95%] mx-auto" : step === 3 ? "max-w-[85%] mx-auto" : "max-w-xl mx-auto"
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

          {/* STEP 2: RESUME UPLOAD & ROTATING MESSAGE */}
          {step === 2 && (
            <motion.div
              key="step2"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col md:flex-row gap-10 md:gap-16 items-center justify-between min-h-[550px] w-full"
            >
              {/* LEFT 55%: Large Upload Card */}
              <div className="w-full md:w-[55%] glass-card rounded-3xl p-10 md:p-14 space-y-8 flex-1">
                {isParsing ? (
                  /* Premium Progress UX Indicator */
                  <div className="space-y-6 py-6">
                    <div className="text-center space-y-2">
                      <h2 className="font-display text-2xl md:text-3xl font-semibold text-ink">
                        Structuring your identity...
                      </h2>
                      <p className="text-xs text-ink-soft max-w-sm mx-auto">
                        This takes about 10-15 seconds. Please wait.
                      </p>
                    </div>

                    <div className="bg-white/60 rounded-2xl p-6 border hairline flex flex-col items-center justify-center space-y-4">
                      <Loader2 className="h-8 w-8 text-[color:var(--peach-deep)] animate-spin" />
                      <span className="text-xs font-semibold text-ink animate-pulse">
                        {UX_PARSING_STAGES[parsingStageIndex]}
                      </span>
                    </div>
                  </div>
                ) : (
                  /* Drag & Drop canvas */
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

                    {errorMessage && (
                      <div className="text-xs text-red-500 bg-red-50/50 p-2.5 rounded-lg border border-red-200">
                        {errorMessage}
                      </div>
                    )}

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
                          ease: [0.16, 1, 0.3, 1],
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

          {/* STEP 3: COLLAPSIBLE REVIEW SCREEN */}
          {step === 3 && (
            <motion.div
              key="step3"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.3 }}
              className="glass-card rounded-3xl p-8 md:p-12 space-y-8 w-full"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between border-b hairline pb-6">
                <div className="space-y-1">
                  <h2 className="font-display text-2xl md:text-3xl font-bold tracking-tight text-ink">
                    Verify Professional Identity
                  </h2>
                  <p className="text-xs text-ink-soft max-w-xl">
                    We've structured your profile. Make any edits below to ensure your background is exactly represented.
                  </p>
                </div>
                <button
                  onClick={() => setStep(4)}
                  className="btn-dark px-6 py-2.5 text-xs font-semibold rounded-xl flex items-center gap-1.5 mt-4 md:mt-0"
                >
                  Confirm Profile <ArrowRight className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-4">
                {/* 1. PERSONAL INFO SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("personal")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Personal Information
                    </span>
                    {openSections.personal ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.personal && (
                    <div className="p-5 border-t hairline bg-white/30 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Full Name</label>
                        <input
                          type="text"
                          value={profile.personal_info.full_name || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, full_name: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Email</label>
                        <input
                          type="email"
                          value={profile.personal_info.email || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, email: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Phone Number</label>
                        <input
                          type="text"
                          value={profile.personal_info.phone || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, phone: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Location</label>
                        <input
                          type="text"
                          value={profile.personal_info.location || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, location: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">LinkedIn URL</label>
                        <input
                          type="text"
                          value={profile.personal_info.linkedin || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, linkedin: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">GitHub URL</label>
                        <input
                          type="text"
                          value={profile.personal_info.github || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, github: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Portfolio Website</label>
                        <input
                          type="text"
                          value={profile.personal_info.portfolio || ""}
                          onChange={(e) => setProfile({
                            ...profile,
                            personal_info: { ...profile.personal_info, portfolio: e.target.value }
                          })}
                          className="w-full px-3 py-2 rounded-xl bg-white border hairline outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* 2. SUMMARY SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("summary")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Professional Summary
                    </span>
                    {openSections.summary ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.summary && (
                    <div className="p-5 border-t hairline bg-white/30 text-xs">
                      <textarea
                        value={profile.summary || ""}
                        onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
                        className="w-full h-24 px-3 py-2 rounded-xl bg-white border hairline outline-none resize-none leading-relaxed"
                        placeholder="Write a brief professional summary..."
                      />
                    </div>
                  )}
                </div>

                {/* 3. EDUCATION SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("education")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <GraduationCap className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Education ({profile.education.length})
                    </span>
                    {openSections.education ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.education && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-4">
                      {profile.education.map((edu, idx) => (
                        <div key={idx} className="p-4 bg-white/70 border hairline rounded-2xl text-xs space-y-3 relative">
                          <div className="absolute right-3 top-3 flex items-center gap-1">
                            <button onClick={() => moveItem("education", idx, "up")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowUp className="h-3 w-3" /></button>
                            <button onClick={() => moveItem("education", idx, "down")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowDown className="h-3 w-3" /></button>
                            <button
                              onClick={() => {
                                const list = [...profile.education];
                                list.splice(idx, 1);
                                setProfile({ ...profile, education: list });
                              }}
                              className="text-red-500 hover:bg-red-50 p-1.5 rounded transition-all ml-1"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-4 md:pt-0">
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Institution</label>
                              <input
                                type="text"
                                value={edu.institution}
                                onChange={(e) => {
                                  const list = [...profile.education];
                                  list[idx].institution = e.target.value;
                                  setProfile({ ...profile, education: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Degree</label>
                              <input
                                type="text"
                                value={edu.degree || ""}
                                onChange={(e) => {
                                  const list = [...profile.education];
                                  list[idx].degree = e.target.value;
                                  setProfile({ ...profile, education: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Field of Study</label>
                              <input
                                type="text"
                                value={edu.field_of_study || ""}
                                onChange={(e) => {
                                  const list = [...profile.education];
                                  list[idx].field_of_study = e.target.value;
                                  setProfile({ ...profile, education: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">GPA / CGPA</label>
                              <input
                                type="text"
                                value={edu.gpa || ""}
                                onChange={(e) => {
                                  const list = [...profile.education];
                                  list[idx].gpa = e.target.value;
                                  setProfile({ ...profile, education: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Start Date</label>
                              <input
                                type="text"
                                value={edu.start_date || ""}
                                onChange={(e) => {
                                  const list = [...profile.education];
                                  list[idx].start_date = e.target.value;
                                  setProfile({ ...profile, education: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">End Date</label>
                              <input
                                type="text"
                                value={edu.end_date || ""}
                                onChange={(e) => {
                                  const list = [...profile.education];
                                  list[idx].end_date = e.target.value;
                                  setProfile({ ...profile, education: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                          </div>
                        </div>
                      ))}

                      <button
                        onClick={() => setProfile({
                          ...profile,
                          education: [...profile.education, { institution: "New Institution", degree: "", field_of_study: "", gpa: "", start_date: "", end_date: "", location: "" }]
                        })}
                        className="btn-ghost-ink w-full py-2.5 text-xs rounded-xl flex items-center justify-center gap-1.5"
                      >
                        <PlusCircle className="h-4 w-4" /> Add Education Entry
                      </button>
                    </div>
                  )}
                </div>

                {/* 4. WORK EXPERIENCE SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("experience")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Briefcase className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Work Experience ({profile.experience.length})
                    </span>
                    {openSections.experience ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.experience && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-6">
                      {profile.experience.map((exp, idx) => (
                        <div key={idx} className="p-4 bg-white/70 border hairline rounded-2xl text-xs space-y-4 relative">
                          <div className="absolute right-3 top-3 flex items-center gap-1">
                            <button onClick={() => moveItem("experience", idx, "up")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowUp className="h-3 w-3" /></button>
                            <button onClick={() => moveItem("experience", idx, "down")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowDown className="h-3 w-3" /></button>
                            <button
                              onClick={() => {
                                const list = [...profile.experience];
                                list.splice(idx, 1);
                                setProfile({ ...profile, experience: list });
                              }}
                              className="text-red-500 hover:bg-red-50 p-1.5 rounded transition-all ml-1"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-4 md:pt-0">
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Company</label>
                              <input
                                type="text"
                                value={exp.company}
                                onChange={(e) => {
                                  const list = [...profile.experience];
                                  list[idx].company = e.target.value;
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none font-semibold"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Role / Title</label>
                              <input
                                type="text"
                                value={exp.role}
                                onChange={(e) => {
                                  const list = [...profile.experience];
                                  list[idx].role = e.target.value;
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Employment Type</label>
                              <input
                                type="text"
                                value={exp.employment_type || ""}
                                onChange={(e) => {
                                  const list = [...profile.experience];
                                  list[idx].employment_type = e.target.value;
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                                placeholder="Full-time / Internship"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Start Date</label>
                              <input
                                type="text"
                                value={exp.start_date || ""}
                                onChange={(e) => {
                                  const list = [...profile.experience];
                                  list[idx].start_date = e.target.value;
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">End Date</label>
                              <input
                                type="text"
                                value={exp.end_date || ""}
                                onChange={(e) => {
                                  const list = [...profile.experience];
                                  list[idx].end_date = e.target.value;
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div className="flex items-center gap-2 pt-5">
                              <input
                                type="checkbox"
                                checked={exp.current_position}
                                onChange={(e) => {
                                  const list = [...profile.experience];
                                  list[idx].current_position = e.target.checked;
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="h-4 w-4 rounded border-gray-300 text-peach-deep focus:ring-peach-deep"
                              />
                              <label className="text-xs font-medium text-ink">Currently Employed Here</label>
                            </div>
                          </div>

                          {/* Bullet points sub list */}
                          <div className="space-y-2">
                            <label className="block text-[10px] uppercase font-bold text-ink-soft">Responsibilities (Bullet Points)</label>
                            <div className="space-y-1.5">
                              {exp.bullet_points.map((bullet, bIdx) => (
                                <div key={bIdx} className="flex items-start gap-2">
                                  <textarea
                                    value={bullet}
                                    onChange={(e) => {
                                      const list = [...profile.experience];
                                      list[idx].bullet_points[bIdx] = e.target.value;
                                      setProfile({ ...profile, experience: list });
                                    }}
                                    className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none resize-none h-12 leading-normal"
                                  />
                                  <button
                                    onClick={() => {
                                      const list = [...profile.experience];
                                      list[idx].bullet_points.splice(bIdx, 1);
                                      setProfile({ ...profile, experience: list });
                                    }}
                                    className="text-red-400 hover:text-red-600 mt-2"
                                  >
                                    ×
                                  </button>
                                </div>
                              ))}
                              <button
                                onClick={() => {
                                  const list = [...profile.experience];
                                  list[idx].bullet_points.push("New responsibility details...");
                                  setProfile({ ...profile, experience: list });
                                }}
                                className="text-xs text-[color:var(--peach-deep)] font-medium hover:underline flex items-center gap-1"
                              >
                                + Add Responsibility Bullet
                              </button>
                            </div>
                          </div>

                          {/* Technologies used chips */}
                          <div className="space-y-2">
                            <label className="block text-[10px] uppercase font-bold text-ink-soft">Technologies Used</label>
                            <div className="flex flex-wrap gap-1.5">
                              {exp.technologies.map((tech, tIdx) => (
                                <span key={tIdx} className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-100 border text-[11px] font-medium text-slate-700">
                                  {tech}
                                  <button
                                    onClick={() => {
                                      const list = [...profile.experience];
                                      list[idx].technologies.splice(tIdx, 1);
                                      setProfile({ ...profile, experience: list });
                                    }}
                                    className="hover:text-red-500 opacity-60 hover:opacity-100"
                                  >
                                    ×
                                  </button>
                                </span>
                              ))}
                              <input
                                type="text"
                                placeholder="Add tech..."
                                onKeyDown={(e: any) => {
                                  if (e.key === "Enter" && e.target.value.trim()) {
                                    const list = [...profile.experience];
                                    list[idx].technologies.push(e.target.value.trim());
                                    setProfile({ ...profile, experience: list });
                                    e.target.value = "";
                                  }
                                }}
                                className="px-2 py-0.5 rounded border hairline text-[11px] outline-none max-w-[100px]"
                              />
                            </div>
                          </div>
                        </div>
                      ))}

                      <button
                        onClick={() => setProfile({
                          ...profile,
                          experience: [...profile.experience, { company: "New Company", role: "Software Engineer", employment_type: "", location: "", start_date: "", end_date: "", current_position: false, bullet_points: [], technologies: [] }]
                        })}
                        className="btn-ghost-ink w-full py-2.5 text-xs rounded-xl flex items-center justify-center gap-1.5"
                      >
                        <PlusCircle className="h-4 w-4" /> Add Experience Entry
                      </button>
                    </div>
                  )}
                </div>

                {/* 5. PROJECTS SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("projects")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Target className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Projects ({profile.projects.length})
                    </span>
                    {openSections.projects ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.projects && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-4">
                      {profile.projects.map((proj, idx) => (
                        <div key={idx} className="p-4 bg-white/70 border hairline rounded-2xl text-xs space-y-3 relative">
                          <div className="absolute right-3 top-3 flex items-center gap-1">
                            <button onClick={() => moveItem("projects", idx, "up")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowUp className="h-3 w-3" /></button>
                            <button onClick={() => moveItem("projects", idx, "down")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowDown className="h-3 w-3" /></button>
                            <button
                              onClick={() => {
                                const list = [...profile.projects];
                                list.splice(idx, 1);
                                setProfile({ ...profile, projects: list });
                              }}
                              className="text-red-500 hover:bg-red-50 p-1.5 rounded transition-all ml-1"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 md:pt-0">
                            <div className="md:col-span-1">
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Project Name</label>
                              <input
                                type="text"
                                value={proj.name}
                                onChange={(e) => {
                                  const list = [...profile.projects];
                                  list[idx].name = e.target.value;
                                  setProfile({ ...profile, projects: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none font-semibold"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">GitHub Link</label>
                              <input
                                type="text"
                                value={proj.github_link || ""}
                                onChange={(e) => {
                                  const list = [...profile.projects];
                                  list[idx].github_link = e.target.value;
                                  setProfile({ ...profile, projects: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Live Demo Link</label>
                              <input
                                type="text"
                                value={proj.live_link || ""}
                                onChange={(e) => {
                                  const list = [...profile.projects];
                                  list[idx].live_link = e.target.value;
                                  setProfile({ ...profile, projects: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                          </div>

                          <div>
                            <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Description</label>
                            <textarea
                              value={proj.description || ""}
                              onChange={(e) => {
                                const list = [...profile.projects];
                                list[idx].description = e.target.value;
                                setProfile({ ...profile, projects: list });
                              }}
                              className="w-full h-14 px-3 py-1.5 rounded-xl bg-white border hairline outline-none resize-none leading-normal"
                            />
                          </div>

                          <div className="space-y-1.5">
                            <label className="block text-[10px] uppercase font-bold text-ink-soft">Technologies Used</label>
                            <div className="flex flex-wrap gap-1.5">
                              {proj.technologies.map((tech, tIdx) => (
                                <span key={tIdx} className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-100 border text-[11px] font-medium text-slate-700">
                                  {tech}
                                  <button
                                    onClick={() => {
                                      const list = [...profile.projects];
                                      list[idx].technologies.splice(tIdx, 1);
                                      setProfile({ ...profile, projects: list });
                                    }}
                                    className="hover:text-red-500 opacity-60 hover:opacity-100"
                                  >
                                    ×
                                  </button>
                                </span>
                              ))}
                              <input
                                type="text"
                                placeholder="Add tech..."
                                onKeyDown={(e: any) => {
                                  if (e.key === "Enter" && e.target.value.trim()) {
                                    const list = [...profile.projects];
                                    list[idx].technologies.push(e.target.value.trim());
                                    setProfile({ ...profile, projects: list });
                                    e.target.value = "";
                                  }
                                }}
                                className="px-2 py-0.5 rounded border hairline text-[11px] outline-none max-w-[100px]"
                              />
                            </div>
                          </div>
                        </div>
                      ))}

                      <button
                        onClick={() => setProfile({
                          ...profile,
                          projects: [...profile.projects, { name: "New Project", description: "", technologies: [], github_link: "", live_link: "" }]
                        })}
                        className="btn-ghost-ink w-full py-2.5 text-xs rounded-xl flex items-center justify-center gap-1.5"
                      >
                        <PlusCircle className="h-4 w-4" /> Add Project Entry
                      </button>
                    </div>
                  )}
                </div>

                {/* 6. SKILLS SECTION (CATEGORIZED) */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("skills")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Code className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Categorized Skills
                    </span>
                    {openSections.skills ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.skills && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-4">
                      {Object.keys(profile.skills).map((categoryKey) => {
                        const skillsList = profile.skills[categoryKey as keyof SkillsCategorized] || [];
                        const formattedLabel = categoryKey.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                        
                        return (
                          <div key={categoryKey} className="space-y-2">
                            <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider block">
                              {formattedLabel}
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {skillsList.map((skill, sIdx) => (
                                <span
                                  key={sIdx}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border hairline text-[11px] font-medium text-ink shadow-2xs group"
                                >
                                  {skill}
                                  <button
                                    onClick={() => {
                                      const updatedList = skillsList.filter((_, i) => i !== sIdx);
                                      setProfile({
                                        ...profile,
                                        skills: { ...profile.skills, [categoryKey]: updatedList }
                                      });
                                    }}
                                    className="text-ink-soft hover:text-red-500 opacity-60 group-hover:opacity-100 transition-opacity"
                                  >
                                    ×
                                  </button>
                                </span>
                              ))}
                              
                              <input
                                type="text"
                                placeholder="Add skill..."
                                onKeyDown={(e: any) => {
                                  if (e.key === "Enter" && e.target.value.trim()) {
                                    const value = e.target.value.trim();
                                    if (!skillsList.includes(value)) {
                                      const updatedList = [...skillsList, value];
                                      setProfile({
                                        ...profile,
                                        skills: { ...profile.skills, [categoryKey]: updatedList }
                                      });
                                    }
                                    e.target.value = "";
                                  }
                                }}
                                className="px-3 py-1 rounded-xl bg-white border hairline text-xs outline-none max-w-[120px]"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* 7. CERTIFICATIONS SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("certifications")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Award className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Certifications ({profile.certifications.length})
                    </span>
                    {openSections.certifications ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.certifications && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-4">
                      {profile.certifications.map((cert, idx) => (
                        <div key={idx} className="p-4 bg-white/70 border hairline rounded-2xl text-xs space-y-3 relative">
                          <div className="absolute right-3 top-3 flex items-center gap-1">
                            <button onClick={() => moveItem("certifications", idx, "up")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowUp className="h-3 w-3" /></button>
                            <button onClick={() => moveItem("certifications", idx, "down")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowDown className="h-3 w-3" /></button>
                            <button
                              onClick={() => {
                                const list = [...profile.certifications];
                                list.splice(idx, 1);
                                setProfile({ ...profile, certifications: list });
                              }}
                              className="text-red-500 hover:bg-red-50 p-1.5 rounded transition-all ml-1"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 md:pt-0">
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Certification Name</label>
                              <input
                                type="text"
                                value={cert.name}
                                onChange={(e) => {
                                  const list = [...profile.certifications];
                                  list[idx].name = e.target.value;
                                  setProfile({ ...profile, certifications: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Issuer</label>
                              <input
                                type="text"
                                value={cert.issuer || ""}
                                onChange={(e) => {
                                  const list = [...profile.certifications];
                                  list[idx].issuer = e.target.value;
                                  setProfile({ ...profile, certifications: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Date</label>
                              <input
                                type="text"
                                value={cert.date || ""}
                                onChange={(e) => {
                                  const list = [...profile.certifications];
                                  list[idx].date = e.target.value;
                                  setProfile({ ...profile, certifications: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                          </div>
                        </div>
                      ))}

                      <button
                        onClick={() => setProfile({
                          ...profile,
                          certifications: [...profile.certifications, { name: "New Certification", issuer: "", date: "" }]
                        })}
                        className="btn-ghost-ink w-full py-2.5 text-xs rounded-xl flex items-center justify-center gap-1.5"
                      >
                        <PlusCircle className="h-4 w-4" /> Add Certification Entry
                      </button>
                    </div>
                  )}
                </div>

                {/* 8. ACHIEVEMENTS SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("achievements")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      Achievements ({profile.achievements.length})
                    </span>
                    {openSections.achievements ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.achievements && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-3">
                      {profile.achievements.map((ach, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            type="text"
                            value={ach}
                            onChange={(e) => {
                              const list = [...profile.achievements];
                              list[idx] = e.target.value;
                              setProfile({ ...profile, achievements: list });
                            }}
                            className="w-full px-3 py-2 rounded-xl bg-white border hairline text-xs outline-none"
                          />
                          <button
                            onClick={() => {
                              const list = [...profile.achievements];
                              list.splice(idx, 1);
                              setProfile({ ...profile, achievements: list });
                            }}
                            className="text-red-500 hover:bg-red-50 p-2 rounded transition-all"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                      <button
                        onClick={() => setProfile({ ...profile, achievements: [...profile.achievements, "New achievement details..."] })}
                        className="text-xs text-[color:var(--peach-deep)] font-medium hover:underline flex items-center gap-1 pt-1"
                      >
                        + Add Achievement
                      </button>
                    </div>
                  )}
                </div>

                {/* 9. EXTERNAL LINKS SECTION */}
                <div className="border border-slate-200/80 rounded-2xl overflow-hidden bg-white/50">
                  <button
                    onClick={() => toggleSection("links")}
                    className="w-full px-5 py-4 flex items-center justify-between font-semibold text-sm text-ink hover:bg-slate-50/50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <ExternalLink className="h-4 w-4 text-[color:var(--peach-deep)]" />
                      External Links ({profile.external_links.length})
                    </span>
                    {openSections.links ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </button>

                  {openSections.links && (
                    <div className="p-5 border-t hairline bg-white/30 space-y-4">
                      {profile.external_links.map((link, idx) => (
                        <div key={idx} className="p-4 bg-white/70 border hairline rounded-2xl text-xs space-y-3 relative">
                          <div className="absolute right-3 top-3 flex items-center gap-1">
                            <button onClick={() => moveItem("external_links", idx, "up")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowUp className="h-3 w-3" /></button>
                            <button onClick={() => moveItem("external_links", idx, "down")} className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"><ArrowDown className="h-3 w-3" /></button>
                            <button
                              onClick={() => {
                                const list = [...profile.external_links];
                                list.splice(idx, 1);
                                setProfile({ ...profile, external_links: list });
                              }}
                              className="text-red-500 hover:bg-red-50 p-1.5 rounded transition-all ml-1"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-4 md:pt-0">
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">Label (e.g. GitHub, Portfolio)</label>
                              <input
                                type="text"
                                value={link.label}
                                onChange={(e) => {
                                  const list = [...profile.external_links];
                                  list[idx].label = e.target.value;
                                  setProfile({ ...profile, external_links: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                            <div>
                              <label className="block text-[10px] uppercase font-bold text-ink-soft mb-1">URL</label>
                              <input
                                type="text"
                                value={link.url}
                                onChange={(e) => {
                                  const list = [...profile.external_links];
                                  list[idx].url = e.target.value;
                                  setProfile({ ...profile, external_links: list });
                                }}
                                className="w-full px-3 py-1.5 rounded-xl bg-white border hairline outline-none"
                              />
                            </div>
                          </div>
                        </div>
                      ))}

                      <button
                        onClick={() => setProfile({
                          ...profile,
                          external_links: [...profile.external_links, { label: "LinkedIn", url: "https://" }]
                        })}
                        className="btn-ghost-ink w-full py-2.5 text-xs rounded-xl flex items-center justify-center gap-1.5"
                      >
                        <PlusCircle className="h-4 w-4" /> Add Link
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-6 flex justify-end">
                <button
                  onClick={() => setStep(4)}
                  className="btn-dark px-10 py-3.5 text-xs font-semibold rounded-2xl flex items-center justify-center gap-1.5 shadow-md hover:shadow-lg transition-all"
                >
                  Save &amp; Continue <ArrowRight className="h-4 w-4" />
                </button>
              </div>
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

          {/* STEP 5: WOW ACTIVATION MOMENT */}
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
                    <span>Structured profile parsed successfully</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>{profile.experience.length} experiences detected</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>{profile.projects.length} projects detected</span>
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
