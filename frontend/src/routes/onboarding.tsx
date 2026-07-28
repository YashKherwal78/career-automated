import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../lib/auth";
import { API_BASE } from "../lib/api";
import { DsLogo } from "../components/ds/Logo";

export const Route = createFileRoute("/onboarding")({
  head: () => ({
    meta: [{ title: "Personalize your CareerAutomated workspace" }],
  }),
  component: OnboardingPage,
});

// Schema definitions matching backend ResumeParserService (POST /users/extract_profile response)
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
  achievements: string[];
  domains: string[];
  keywords: string[];
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

interface ProfileData {
  personal_info: PersonalInfo;
  summary: string | null;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  skills: SkillsCategorized;
  resume_url?: string;
  resume_file_name?: string;
}

const EMPTY_PROFILE: ProfileData = {
  personal_info: {
    full_name: "",
    email: "",
    phone: "",
    location: "",
    linkedin: "",
    github: "",
    portfolio: "",
  },
  summary: "",
  education: [],
  experience: [],
  skills: {
    programming_languages: [],
    frameworks: [],
    libraries: [],
    databases: [],
    cloud: [],
    ai_ml: [],
    developer_tools: [],
    other: [],
  },
};

const LOADING_LINES = [
  "Understanding your professional background…",
  "Analyzing your skills and experience…",
  "Identifying your strongest projects and achievements…",
];

type UploadPhase = "idle" | "uploading" | "done" | "error";

function Spinner({ size = 56 }: { size?: number }) {
  return (
    <div
      className="animate-spin rounded-full mx-auto"
      style={{
        width: size,
        height: size,
        border: "3px solid rgba(226,116,72,0.2)",
        borderTopColor: "var(--ds-accent-primary)",
        marginBottom: 22,
      }}
    />
  );
}

function OnboardingPage() {
  const { user, session, refreshProfile } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<1 | 2>(1);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [fileName, setFileName] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [lineIndex, setLineIndex] = useState(0);
  const [profile, setProfile] = useState<ProfileData>(EMPTY_PROFILE);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lineTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!user) navigate({ to: "/signup" });
  }, [user, navigate]);

  useEffect(
    () => () => {
      if (lineTimerRef.current) clearInterval(lineTimerRef.current);
    },
    [],
  );

  const startUpload = async (file: File) => {
    setFileName(file.name);
    setPhase("uploading");
    setLineIndex(0);
    lineTimerRef.current = setInterval(() => {
      setLineIndex((i) => (i + 1) % LOADING_LINES.length);
    }, 1000);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/users/extract_profile`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.access_token}` },
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to extract profile");
      }
      const data = await response.json();
      setProfile(data);
      setPhase("done");
    } catch (err) {
      console.error(err);
      setPhase("error");
    } finally {
      if (lineTimerRef.current) clearInterval(lineTimerRef.current);
    }
  };

  const handleContinue = () => {
    if (phase !== "done") return;
    setStep(2);
  };

  const handleFinish = async () => {
    try {
      if (session?.access_token) {
        const allSkillsFlat = Object.values(profile.skills)
          .flat()
          .filter(Boolean)
          .map((s) => ({ skill_name: s, proficiency: "Expert" }));

        await fetch(`${API_BASE}/users/onboarding`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            full_name: profile.personal_info.full_name || "Verified Candidate",
            education: profile.education.map((e) => ({
              institution: e.institution,
              degree: e.degree,
              field_of_study: e.field_of_study,
              start_year: e.start_date ? parseInt(e.start_date.split(" ")[1]) || null : null,
              end_year: e.end_date ? parseInt(e.end_date.split(" ")[1]) || null : null,
            })),
            experience: profile.experience.map((e) => ({
              company: e.company,
              title: e.role,
              start_date: e.start_date,
              end_date: e.end_date,
              description: e.bullet_points.join("\n"),
            })),
            skills: allSkillsFlat,
            resume_url: profile.resume_url,
            resume_file_name: profile.resume_file_name,
          }),
        });
      }
    } catch (err) {
      console.error("Failed to save onboarding profile:", err);
    }
    await refreshProfile();
    navigate({ to: "/dashboard" });
  };

  const yearsExperience = profile.experience.length;
  const topSkills = Object.values(profile.skills).flat().filter(Boolean).slice(0, 6);
  const mostRecentRole = profile.experience[0];
  const initial = (profile.personal_info.full_name || user?.email || "?").charAt(0).toUpperCase();

  return (
    <div
      className="flex items-center justify-center relative overflow-hidden"
      style={{
        minHeight: "100vh",
        padding: "40px 24px",
        fontFamily: "var(--ds-font-body)",
        color: "var(--ds-text-primary)",
      }}
    >
      <div
        className="pointer-events-none fixed"
        style={{
          top: -140,
          left: "10%",
          width: 480,
          height: 480,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(232,93,44,0.14), transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div className="relative z-10" style={{ width: "100%", maxWidth: 560 }}>
        <div className="flex items-center gap-1.5" style={{ marginBottom: 32 }}>
          <DsLogo size="sm" />
        </div>

        {step === 1 ? (
          <>
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 12.5,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-brand-orange-text)",
                marginBottom: 10,
              }}
            >
              Step 1 of 2 · Getting started
            </div>
            <h1
              className="font-[var(--ds-font-display)] font-semibold"
              style={{
                fontSize: "clamp(26px,3vw,32px)",
                margin: "0 0 10px",
                letterSpacing: "-0.01em",
              }}
            >
              Let's start with your resume.
            </h1>
            <p
              style={{
                fontSize: 15,
                color: "var(--ds-ink-500)",
                margin: "0 0 32px",
                lineHeight: 1.6,
                maxWidth: 460,
              }}
            >
              We'll read it once to understand your experience, then use it to find and tailor
              matches. Nothing is shared until you approve an application.
            </p>

            <div
              role="button"
              tabIndex={0}
              onClick={() => phase === "idle" && fileInputRef.current?.click()}
              onKeyDown={(e) =>
                e.key === "Enter" && phase === "idle" && fileInputRef.current?.click()
              }
              onDragOver={(e) => {
                e.preventDefault();
                if (phase === "idle") setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const f = e.dataTransfer.files?.[0];
                if (f) startUpload(f);
              }}
              style={{
                border: `2px dashed ${dragOver ? "var(--ds-accent-primary)" : phase === "error" ? "rgba(180,57,44,0.3)" : "var(--ds-border-medium)"}`,
                borderRadius: "var(--ds-radius-2xl)",
                padding: "56px 32px",
                textAlign: "center",
                background: dragOver
                  ? "rgba(226,116,72,0.05)"
                  : phase === "error"
                    ? "rgba(180,57,44,0.03)"
                    : "var(--ds-surface-card)",
                cursor: phase === "idle" ? "pointer" : "default",
                transition: "border-color 160ms linear, background 160ms linear",
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) startUpload(f);
                }}
              />

              {phase === "idle" && (
                <>
                  <div
                    className="mx-auto flex items-center justify-center"
                    style={{
                      width: 56,
                      height: 56,
                      borderRadius: "var(--ds-radius-xl)",
                      background: "var(--ds-brand-orange-tint-10)",
                      marginBottom: 22,
                    }}
                  >
                    <div
                      style={{
                        width: 0,
                        height: 0,
                        borderLeft: "8px solid transparent",
                        borderRight: "8px solid transparent",
                        borderBottom: "12px solid var(--ds-accent-primary)",
                      }}
                    />
                  </div>
                  <div
                    className="font-[var(--ds-font-display)] font-semibold"
                    style={{ fontSize: 19, marginBottom: 8 }}
                  >
                    Drop your resume here
                  </div>
                  <div
                    style={{
                      fontSize: "var(--ds-text-md)",
                      color: "var(--ds-text-secondary)",
                      marginBottom: 20,
                    }}
                  >
                    or click to browse your files
                  </div>
                  <div className="flex justify-center gap-2">
                    {["PDF", "DOCX", "DOC"].map((f) => (
                      <span
                        key={f}
                        className="font-semibold"
                        style={{
                          fontSize: 11.5,
                          color: "var(--ds-text-secondary)",
                          background: "var(--ds-surface-tint)",
                          padding: "5px 11px",
                          borderRadius: "var(--ds-radius-pill)",
                        }}
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                </>
              )}

              {phase === "uploading" && (
                <>
                  <Spinner />
                  <div
                    className="font-[var(--ds-font-display)] font-semibold"
                    style={{ fontSize: 17, marginBottom: 6 }}
                  >
                    Uploading {fileName}…
                  </div>
                  <div style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
                    {LOADING_LINES[lineIndex]}
                  </div>
                </>
              )}

              {phase === "done" && (
                <>
                  <div
                    className="mx-auto flex items-center justify-center rounded-full"
                    style={{ width: 56, height: 56, background: "#6B8F5E", marginBottom: 22 }}
                  >
                    <svg width="26" height="26" viewBox="0 0 16 16">
                      <path
                        d="M3 8.5l3 3 7-7"
                        stroke="#FFFDFA"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        fill="none"
                      />
                    </svg>
                  </div>
                  <div
                    className="font-[var(--ds-font-display)] font-semibold"
                    style={{ fontSize: 17, marginBottom: 6 }}
                  >
                    {fileName}
                  </div>
                  <div style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
                    Uploaded. We'll take it from here.
                  </div>
                </>
              )}

              {phase === "error" && (
                <>
                  <div
                    className="mx-auto flex items-center justify-center rounded-full"
                    style={{
                      width: 56,
                      height: 56,
                      background: "rgba(180,57,44,0.1)",
                      marginBottom: 22,
                      fontSize: 22,
                    }}
                  >
                    ⚠
                  </div>
                  <div
                    className="font-[var(--ds-font-display)] font-semibold"
                    style={{ fontSize: 17, marginBottom: 6 }}
                  >
                    We couldn't read that file
                  </div>
                  <div style={{ fontSize: 13.5, color: "var(--ds-ink-450)", marginBottom: 18 }}>
                    It happens sometimes — try a different PDF or DOCX, no rush.
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPhase("idle");
                      setFileName("");
                    }}
                    className="font-semibold"
                    style={{
                      padding: "10px 20px",
                      borderRadius: "var(--ds-radius-md)",
                      border: "1px solid var(--ds-border-medium)",
                      background: "transparent",
                      color: "var(--ds-ink-700)",
                      fontSize: 13.5,
                      cursor: "pointer",
                    }}
                  >
                    Try again
                  </button>
                </>
              )}
            </div>

            <div className="flex items-center justify-between" style={{ marginTop: 28 }}>
              <Link to="/dashboard" style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
                Skip for now
              </Link>
              <button
                type="button"
                onClick={handleContinue}
                disabled={phase !== "done"}
                className="font-bold transition-transform"
                style={{
                  padding: "12px 26px",
                  borderRadius: "var(--ds-radius-md)",
                  border: "none",
                  background: phase === "done" ? "var(--ds-accent-primary)" : "var(--ds-cream-300)",
                  color: phase === "done" ? "var(--ds-text-on-brand)" : "var(--ds-ink-400)",
                  fontSize: 14,
                  cursor: phase === "done" ? "pointer" : "default",
                  boxShadow: phase === "done" ? "0 10px 22px -8px rgba(226,116,72,0.45)" : "none",
                }}
              >
                Continue
              </button>
            </div>
          </>
        ) : (
          <>
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 12.5,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-brand-orange-text)",
                marginBottom: 10,
              }}
            >
              Step 2 of 2 · Getting started
            </div>
            <h1
              className="font-[var(--ds-font-display)] font-semibold"
              style={{
                fontSize: "clamp(24px,2.8vw,30px)",
                margin: "0 0 10px",
                letterSpacing: "-0.01em",
              }}
            >
              Here's what we understood.
            </h1>
            <p
              style={{
                fontSize: 14.5,
                color: "var(--ds-ink-500)",
                margin: "0 0 28px",
                lineHeight: 1.6,
                maxWidth: 460,
              }}
            >
              Nothing here is set in stone — you can change any of it later from your career
              profile.
            </p>

            <div
              style={{
                background: "var(--ds-surface-card)",
                border: "1px solid var(--ds-border-default)",
                borderRadius: "var(--ds-radius-xl)",
                padding: 24,
                marginBottom: 14,
              }}
            >
              <div
                className="flex items-center gap-3.5"
                style={{
                  marginBottom: 20,
                  paddingBottom: 20,
                  borderBottom: "1px solid var(--ds-border-default)",
                }}
              >
                <div
                  className="flex items-center justify-center flex-shrink-0 font-bold"
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: "50%",
                    background: "var(--ds-ink-800)",
                    color: "var(--ds-text-on-dark)",
                    fontSize: 16,
                  }}
                >
                  {initial}
                </div>
                <div>
                  <div
                    className="font-[var(--ds-font-display)] font-semibold"
                    style={{ fontSize: 16 }}
                  >
                    {profile.personal_info.full_name || "Your profile"}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--ds-ink-450)" }}>
                    {mostRecentRole ? mostRecentRole.role : "Role not detected"}
                    {yearsExperience > 0
                      ? ` · ${yearsExperience} role${yearsExperience === 1 ? "" : "s"} on record`
                      : ""}
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-3.5">
                {mostRecentRole && (
                  <div>
                    <div
                      className="uppercase font-bold"
                      style={{
                        fontSize: 11,
                        letterSpacing: "0.5px",
                        color: "var(--ds-ink-400)",
                        marginBottom: 6,
                      }}
                    >
                      Most recent role
                    </div>
                    <div style={{ fontSize: 13.5, color: "var(--ds-ink-700)" }}>
                      {mostRecentRole.role} at {mostRecentRole.company}
                    </div>
                  </div>
                )}
                {topSkills.length > 0 && (
                  <div>
                    <div
                      className="uppercase font-bold"
                      style={{
                        fontSize: 11,
                        letterSpacing: "0.5px",
                        color: "var(--ds-ink-400)",
                        marginBottom: 6,
                      }}
                    >
                      Core skills
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {topSkills.map((s) => (
                        <span
                          key={s}
                          className="font-semibold"
                          style={{
                            fontSize: 12.5,
                            color: "var(--ds-ink-600)",
                            background: "var(--ds-surface-tint)",
                            padding: "5px 11px",
                            borderRadius: "var(--ds-radius-pill)",
                          }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {profile.summary && (
                  <div>
                    <div
                      className="uppercase font-bold"
                      style={{
                        fontSize: 11,
                        letterSpacing: "0.5px",
                        color: "var(--ds-ink-400)",
                        marginBottom: 6,
                      }}
                    >
                      Summary
                    </div>
                    <div style={{ fontSize: 13.5, color: "var(--ds-ink-700)" }}>
                      {profile.summary}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <p
              style={{
                fontSize: 12.5,
                color: "var(--ds-ink-400)",
                margin: "0 0 24px",
                lineHeight: 1.5,
              }}
            >
              We'll use this to find and tailor matches. It stays private until you approve an
              application.
            </p>

            <div className="flex items-center justify-between">
              <Link to="/dashboard/career-profile" style={{ fontSize: 13.5, fontWeight: 600 }}>
                Edit details
              </Link>
              <button
                type="button"
                onClick={handleFinish}
                className="font-bold transition-transform"
                style={{
                  padding: "13px 22px",
                  borderRadius: "var(--ds-radius-md)",
                  border: "none",
                  background: "var(--ds-accent-primary)",
                  color: "var(--ds-text-on-brand)",
                  fontSize: 14,
                  cursor: "pointer",
                  boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
                }}
              >
                Looks good, continue
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
