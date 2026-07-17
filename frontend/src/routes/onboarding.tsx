import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ArrowRight, ArrowLeft, Plus, X, Upload, CheckCircle2, Sparkles, LogOut } from "lucide-react";
import { Button } from "@/components/primitives/button";
import { FadeIn } from "@/components/primitives/motion";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [
      { title: "Complete your onboarding — CareerAutomated" },
    ],
  }),
  component: OnboardingPage,
});

interface EducationItem {
  institution: string;
  degree: string;
  field_of_study: string;
  start_year: number;
  end_year: number;
}

interface ExperienceItem {
  company: string;
  title: string;
  start_date: string;
  end_date: string;
  description: string;
}

interface SkillItem {
  skill_name: string;
  proficiency: string;
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

function OnboardingPage() {
  const { user, profile, session, logout, refreshProfile } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [fullName, setFullName] = useState("");
  const [careerGoals, setCareerGoals] = useState("");
  
  // Lists
  const [education, setEducation] = useState<EducationItem[]>([]);
  const [experience, setExperience] = useState<ExperienceItem[]>([]);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [skillInput, setSkillInput] = useState("");
  
  // File
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
  const [uploadedName, setUploadedName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form Temp Fields
  const [tempEdu, setTempEdu] = useState({ institution: "", degree: "", field_of_study: "", start_year: 2020, end_year: 2024 });
  const [tempExp, setTempExp] = useState({ company: "", title: "", start_date: "", end_date: "", description: "" });

  useEffect(() => {
    if (!user) {
      navigate({ to: "/signup" });
    } else if (profile?.onboarding_complete) {
      navigate({ to: "/dashboard" });
    }
  }, [user, profile, navigate]);

  const handleFileUpload = async (f: File) => {
    if (!session?.access_token) return;
    setUploading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append("file", f);

    try {
      const response = await fetch(`${API_BASE}/users/upload_resume`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to upload file");
      }

      const result = await response.json();
      setUploadedUrl(result.url);
      setUploadedName(result.file_name);
      setFile(f);
    } catch (e: any) {
      setError(e.message || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleAddEducation = () => {
    if (!tempEdu.institution) return;
    setEducation([...education, { ...tempEdu }]);
    setTempEdu({ institution: "", degree: "", field_of_study: "", start_year: 2020, end_year: 2024 });
  };

  const handleAddExperience = () => {
    if (!tempExp.company || !tempExp.title) return;
    setExperience([...experience, { ...tempExp }]);
    setTempExp({ company: "", title: "", start_date: "", end_date: "", description: "" });
  };

  const handleAddSkill = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && skillInput.trim()) {
      e.preventDefault();
      if (!skills.some(s => s.skill_name.toLowerCase() === skillInput.trim().toLowerCase())) {
        setSkills([...skills, { skill_name: skillInput.trim(), proficiency: "Intermediate" }]);
      }
      setSkillInput("");
    }
  };

  const handleSubmit = async () => {
    if (!session?.access_token) return;
    setUploading(true);
    try {
      const response = await fetch(`${API_BASE}/users/onboarding`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: json_payload(),
      });

      if (!response.ok) {
        throw new Error("Failed to save profile information");
      }

      await refreshProfile();
      navigate({ to: "/dashboard" });
    } catch (e: any) {
      setError(e.message || "Failed to complete onboarding.");
    } finally {
      setUploading(false);
    }
  };

  const json_payload = () => {
    return JSON.stringify({
      full_name: fullName || user?.email?.split("@")[0] || "User",
      career_goals: careerGoals,
      education,
      experience,
      skills,
      resume_url: uploadedUrl,
      resume_file_name: uploadedName,
    });
  };

  return (
    <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-2">
      {/* Step side */}
      <div className="flex flex-col justify-between px-6 py-12 lg:px-16">
        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-2 rounded-full border hairline bg-white/70 px-3 py-1 text-xs text-ink-soft">
            <Sparkles className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" />
            <span>Onboarding Wizard · Step {step} of 5</span>
          </div>
          <button onClick={logout} className="inline-flex items-center gap-1.5 text-xs text-ink-soft hover:text-ink">
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </button>
        </div>

        <div className="my-auto py-8">
          <FadeIn className="w-full max-w-lg">
            {step === 1 && (
              <div className="space-y-5">
                <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">What's your name?</h1>
                <label className="block">
                  <div className="mb-1.5 text-[13px] font-medium text-ink">Full name</div>
                  <input
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Yash Kherwal"
                    className="w-full h-11 rounded-xl border hairline bg-white px-3 text-sm text-ink outline-none"
                  />
                </label>
                <label className="block">
                  <div className="mb-1.5 text-[13px] font-medium text-ink">Career Goals</div>
                  <textarea
                    rows={4}
                    value={careerGoals}
                    onChange={(e) => setCareerGoals(e.target.value)}
                    placeholder="e.g. Seeking a Senior Machine Learning Engineer role in remote SaaS companies."
                    className="w-full rounded-xl border hairline bg-white p-3 text-sm text-ink outline-none resize-none"
                  />
                </label>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">Tell us about your Education</h1>
                <div className="space-y-3">
                  <input
                    value={tempEdu.institution}
                    onChange={(e) => setTempEdu({ ...tempEdu, institution: e.target.value })}
                    placeholder="Institution (e.g. IIT Delhi)"
                    className="w-full h-11 rounded-xl border hairline bg-white px-3 text-sm outline-none"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={tempEdu.degree}
                      onChange={(e) => setTempEdu({ ...tempEdu, degree: e.target.value })}
                      placeholder="Degree (e.g. B.Tech)"
                      className="w-full h-11 rounded-xl border hairline bg-white px-3 text-sm outline-none"
                    />
                    <input
                      value={tempEdu.field_of_study}
                      onChange={(e) => setTempEdu({ ...tempEdu, field_of_study: e.target.value })}
                      placeholder="Field (e.g. CS)"
                      className="w-full h-11 rounded-xl border hairline bg-white px-3 text-sm outline-none"
                    />
                  </div>
                  <button onClick={handleAddEducation} className="inline-flex items-center gap-1.5 text-xs text-[color:var(--peach-deep)] font-medium">
                    <Plus className="h-3.5 w-3.5" /> Add Education
                  </button>
                </div>

                {education.length > 0 && (
                  <div className="pt-2 space-y-2">
                    <div className="text-xs uppercase tracking-wider text-ink-soft">Education History</div>
                    {education.map((edu, idx) => (
                      <div key={idx} className="flex justify-between items-center bg-white border hairline rounded-xl p-3 text-sm">
                        <div>
                          <div className="font-medium text-ink">{edu.institution}</div>
                          <div className="text-xs text-ink-soft">{edu.degree} in {edu.field_of_study}</div>
                        </div>
                        <button onClick={() => setEducation(education.filter((_, i) => i !== idx))}>
                          <X className="h-4 w-4 text-ink-soft hover:text-ink" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">Add Professional Experience</h1>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={tempExp.company}
                      onChange={(e) => setTempExp({ ...tempExp, company: e.target.value })}
                      placeholder="Company (e.g. Stripe)"
                      className="w-full h-11 rounded-xl border hairline bg-white px-3 text-sm outline-none"
                    />
                    <input
                      value={tempExp.title}
                      onChange={(e) => setTempExp({ ...tempExp, title: e.target.value })}
                      placeholder="Title (e.g. SE)"
                      className="w-full h-11 rounded-xl border hairline bg-white px-3 text-sm outline-none"
                    />
                  </div>
                  <textarea
                    rows={2}
                    value={tempExp.description}
                    onChange={(e) => setTempExp({ ...tempExp, description: e.target.value })}
                    placeholder="Key achievements/details"
                    className="w-full rounded-xl border hairline bg-white p-3 text-sm outline-none resize-none"
                  />
                  <button onClick={handleAddExperience} className="inline-flex items-center gap-1.5 text-xs text-[color:var(--peach-deep)] font-medium">
                    <Plus className="h-3.5 w-3.5" /> Add Experience
                  </button>
                </div>

                {experience.length > 0 && (
                  <div className="pt-2 space-y-2">
                    <div className="text-xs uppercase tracking-wider text-ink-soft">Experience History</div>
                    {experience.map((exp, idx) => (
                      <div key={idx} className="flex justify-between items-center bg-white border hairline rounded-xl p-3 text-sm">
                        <div>
                          <div className="font-medium text-ink">{exp.title} at {exp.company}</div>
                          <div className="text-xs text-ink-soft">{exp.description}</div>
                        </div>
                        <button onClick={() => setExperience(experience.filter((_, i) => i !== idx))}>
                          <X className="h-4 w-4 text-ink-soft hover:text-ink" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4">
                <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">Add your key Skills</h1>
                <div className="rounded-xl border hairline bg-white p-3">
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {skills.map((s, idx) => (
                      <span key={idx} className="inline-flex items-center gap-1 bg-[color:var(--peach-soft)] rounded-full px-2.5 py-0.5 text-xs text-ink">
                        {s.skill_name}
                        <button onClick={() => setSkills(skills.filter((_, i) => i !== idx))}><X className="h-3 w-3" /></button>
                      </span>
                    ))}
                  </div>
                  <input
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={handleAddSkill}
                    placeholder="Type a skill and press Enter"
                    className="w-full bg-transparent text-sm outline-none px-1 py-1.5"
                  />
                </div>
              </div>
            )}

            {step === 5 && (
              <div className="space-y-4">
                <h1 className="font-display text-3xl tracking-tight text-ink md:text-4xl">Upload your Resume</h1>
                
                {uploadedName ? (
                  <div className="flex items-center justify-between border hairline rounded-xl bg-white p-4">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                      <div className="text-sm font-medium">{uploadedName}</div>
                    </div>
                    <button onClick={() => { setUploadedName(null); setUploadedUrl(null); }} className="text-xs text-destructive hover:underline">Remove</button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center border-2 border-dashed border-ink/20 rounded-xl p-8 bg-white cursor-pointer hover:bg-[color:var(--peach-soft)]/20 transition">
                    <Upload className="h-8 w-8 text-ink-soft mb-2" />
                    <span className="text-sm font-medium">Choose a PDF or DOCX file</span>
                    <input
                      type="file"
                      accept=".pdf,.docx"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileUpload(f);
                      }}
                    />
                  </label>
                )}

                {uploading && <div className="text-xs text-ink-soft">Uploading to Cloudflare R2...</div>}
                {error && <div className="text-xs text-destructive">{error}</div>}
              </div>
            )}

            <div className="mt-8 flex justify-between gap-3">
              {step > 1 ? (
                <Button type="button" variant="outline" onClick={() => setStep(step - 1)} leading={<ArrowLeft className="h-4 w-4" />}>
                  Back
                </Button>
              ) : (
                <div />
              )}
              {step < 5 ? (
                <Button type="button" onClick={() => setStep(step + 1)} trailing={<ArrowRight className="h-4 w-4" />}>
                  Continue
                </Button>
              ) : (
                <Button type="button" onClick={handleSubmit} loading={uploading} trailing={<ArrowRight className="h-4 w-4" />}>
                  Finish & Start Matching
                </Button>
              )}
            </div>
          </FadeIn>
        </div>

        <div className="text-xs text-ink-soft">
          Secure onboarding verified with RLS partition rules.
        </div>
      </div>

      {/* Brand side */}
      <div className="relative hidden overflow-hidden bg-ink lg:block">
        <div className="pointer-events-none absolute inset-0 grid-lines opacity-10" />
        <div className="pointer-events-none absolute -right-24 -top-24 h-[520px] w-[520px] rounded-full peach-gradient opacity-30 blur-3xl" />
        <div className="relative flex h-full flex-col justify-between p-12 text-white">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-white/70 backdrop-blur">
            <Sparkles className="h-3 w-3 text-[color:var(--peach)]" />
            Centralized User Onboarding
          </div>

          <div className="max-w-md">
            <h2 className="font-display text-4xl text-white">A tailored search awaits.</h2>
            <p className="mt-4 text-sm text-white/70 leading-relaxed">
              We extract matching skills, experience, and background parameters to coordinate job discovery crawl daemons automatically.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
