import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { API_BASE } from "../../lib/api";
import { DsAccordionSection } from "../../components/ds/Accordion";
import { DsDropzone } from "../../components/ds/Dropzone";
import { DsModal } from "../../components/ds/Modal";

export const Route = createFileRoute("/dashboard/career-profile")({
  component: CareerProfilePage,
});

interface PersonalInfo {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  portfolio: string;
}

interface ExperienceEntry {
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  description: string;
}
interface ProjectEntry {
  name: string;
  description: string;
}
interface EducationEntry {
  institution: string;
  degree: string;
}

interface ProfileData {
  personal_info: PersonalInfo;
  skills: Record<string, string[]>;
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  education: EducationEntry[];
  certifications: string[];
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
  skills: { other: [] },
  experience: [],
  projects: [],
  education: [],
  certifications: [],
};

const PILL_STYLE = (active: boolean): React.CSSProperties => ({
  fontSize: 12.5,
  fontWeight: 600,
  padding: "7px 14px",
  borderRadius: "var(--ds-radius-pill)",
  background: active ? "var(--ds-ink-800)" : "var(--ds-surface-tint)",
  color: active ? "var(--ds-text-on-dark)" : "var(--ds-ink-700)",
  cursor: "pointer",
  border: "none",
});

function CareerProfilePage() {
  const { profile: authProfile, session } = useAuth();
  const [profile, setProfile] = useState<ProfileData>(EMPTY_PROFILE);
  const [skillsDraft, setSkillsDraft] = useState("");
  const [resumeStyle, setResumeStyle] = useState("Modern");
  const [writingTone, setWritingTone] = useState("Professional");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [showReplaceModal, setShowReplaceModal] = useState(false);

  const { data: loaded, isLoading } = useQuery({
    queryKey: ["candidate-profile"],
    queryFn: async (): Promise<ProfileData> => {
      const res = await fetch(`${API_BASE}/candidate/profile`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (!res.ok) throw new Error("Failed to load profile");
      const data = await res.json();
      const p = data.profile_data || {};
      return {
        personal_info: { ...EMPTY_PROFILE.personal_info, ...p.personal_info },
        skills: p.skills && Object.keys(p.skills).length ? p.skills : { other: [] },
        experience: p.experience || [],
        projects: p.projects || [],
        education: p.education || [],
        certifications: p.certifications || [],
      };
    },
    enabled: !!session,
  });

  useEffect(() => {
    if (loaded) {
      setProfile(loaded);
      setSkillsDraft(Object.values(loaded.skills).flat().join(", "));
    }
  }, [loaded]);

  const flatSkills = Object.values(profile.skills).flat();

  const saveField = async (updates: Partial<ProfileData>) => {
    const next = { ...profile, ...updates };
    setProfile(next);
    setSaveState("saving");
    try {
      await fetch(`${API_BASE}/candidate/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          personal_info: next.personal_info,
          skills: next.skills,
          experience: next.experience,
          projects: next.projects,
          education: next.education,
          certifications: next.certifications,
        }),
      });
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 1500);
    } catch {
      setSaveState("idle");
    }
  };

  const saveSkills = () => {
    const list = skillsDraft
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    saveField({ skills: { other: list } });
  };

  const checks = [
    {
      id: "personal",
      label: "your contact details",
      done: !!(profile.personal_info.phone && profile.personal_info.location),
    },
    { id: "experience", label: "your experience", done: profile.experience.length > 0 },
    { id: "education", label: "your education", done: profile.education.length > 0 },
    { id: "skills", label: "your skills", done: flatSkills.length > 0 },
  ];
  const doneCount = checks.filter((c) => c.done).length;
  const completenessPct = Math.round((doneCount / checks.length) * 100);
  const firstMissing = checks.find((c) => !c.done);

  const initial = (profile.personal_info.full_name || authProfile?.full_name || "?")
    .charAt(0)
    .toUpperCase();

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ minHeight: "60vh", color: "var(--ds-ink-450)", fontSize: 13.5 }}
      >
        Loading your profile…
      </div>
    );
  }

  return (
    <div style={{ padding: "40px clamp(24px,4vw,56px)", maxWidth: 760 }}>
      <div
        className="uppercase font-bold"
        style={{
          fontSize: 12.5,
          letterSpacing: "var(--ds-tracking-wide)",
          color: "var(--ds-brand-orange-text)",
          marginBottom: 14,
        }}
      >
        One profile. Everything builds from it.
      </div>
      <p
        style={{
          fontSize: 14.5,
          color: "var(--ds-ink-500)",
          margin: "0 0 20px",
          maxWidth: 520,
          lineHeight: 1.6,
        }}
      >
        Every resume, tailored application, and interview starts here. Keep this up to date once,
        and the rest stays in sync.
      </p>

      {firstMissing && (
        <div
          className="flex items-center justify-between flex-wrap gap-4"
          style={{
            background: "rgba(226,116,72,0.06)",
            border: "1px solid rgba(226,116,72,0.2)",
            borderRadius: "var(--ds-radius-lg)",
            padding: "16px 20px",
            marginBottom: 36,
          }}
        >
          <div>
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 600,
                color: "var(--ds-ink-800)",
                marginBottom: 3,
              }}
            >
              Your profile is {completenessPct}% complete.
            </div>
            <div style={{ fontSize: 12.5, color: "var(--ds-ink-500)" }}>
              A fuller profile means sharper matches and better-tailored resumes. Finish{" "}
              {firstMissing.label} to strengthen it.
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-5" style={{ marginBottom: 40 }}>
        <div
          className="flex items-center justify-center flex-shrink-0 font-bold"
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            background: "var(--ds-ink-800)",
            color: "var(--ds-text-on-dark)",
            fontSize: 26,
          }}
        >
          {initial}
        </div>
        <div className="min-w-0">
          <div
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: 24, marginBottom: 4 }}
          >
            {profile.personal_info.full_name || authProfile?.full_name || "Your name"}
          </div>
          <div style={{ fontSize: 14.5, color: "var(--ds-ink-500)" }}>
            {profile.experience[0]?.role || "Add your most recent role"}
            {profile.personal_info.location ? ` · ${profile.personal_info.location}` : ""}
          </div>
        </div>
      </div>

      <DsAccordionSection
        title="Base resume"
        summary="View or replace your uploaded resume"
        icon="📄"
      >
        <div className="flex items-center justify-between">
          <div style={{ fontSize: 13.5, color: "var(--ds-ink-600)" }}>
            Your most recently uploaded resume.
          </div>
          <button
            type="button"
            onClick={() => setShowReplaceModal(true)}
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--ds-accent-primary)",
              background: "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            Replace resume
          </button>
        </div>
      </DsAccordionSection>

      <DsAccordionSection
        title="Personal info"
        summary="Name and email are locked; phone and location keep your matches accurate"
        icon="◈"
      >
        <div className="flex flex-col gap-3">
          <div>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--ds-ink-500)",
                marginBottom: 5,
              }}
            >
              Name
            </label>
            <input
              value={profile.personal_info.full_name}
              readOnly
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "var(--ds-radius-md)",
                border: "1px solid var(--ds-border-medium)",
                background: "var(--ds-surface-tint)",
                color: "var(--ds-ink-450)",
                fontSize: 13.5,
                cursor: "not-allowed",
              }}
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--ds-ink-500)",
                marginBottom: 5,
              }}
            >
              Email
            </label>
            <input
              value={profile.personal_info.email || authProfile?.email || ""}
              readOnly
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "var(--ds-radius-md)",
                border: "1px solid var(--ds-border-medium)",
                background: "var(--ds-surface-tint)",
                color: "var(--ds-ink-450)",
                fontSize: 13.5,
                cursor: "not-allowed",
              }}
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--ds-ink-500)",
                marginBottom: 5,
              }}
            >
              Phone
            </label>
            <input
              value={profile.personal_info.phone}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  personal_info: { ...profile.personal_info, phone: e.target.value },
                })
              }
              onBlur={() => saveField({ personal_info: profile.personal_info })}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "var(--ds-radius-md)",
                border: "1px solid var(--ds-border-medium)",
                fontSize: 13.5,
              }}
            />
          </div>
          <div>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--ds-ink-500)",
                marginBottom: 5,
              }}
            >
              Location
            </label>
            <input
              value={profile.personal_info.location}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  personal_info: { ...profile.personal_info, location: e.target.value },
                })
              }
              onBlur={() => saveField({ personal_info: profile.personal_info })}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "var(--ds-radius-md)",
                border: "1px solid var(--ds-border-medium)",
                fontSize: 13.5,
              }}
            />
          </div>
        </div>
      </DsAccordionSection>

      <DsAccordionSection
        title="Experience"
        summary={`${profile.experience.length} role${profile.experience.length === 1 ? "" : "s"} on record`}
        icon="◫"
      >
        <div className="flex flex-col gap-2">
          {profile.experience.length === 0 && (
            <span style={{ fontSize: 13, color: "var(--ds-ink-400)" }}>
              No experience added yet.
            </span>
          )}
          {profile.experience.map((exp, i) => (
            <div
              key={i}
              className="flex items-center justify-between"
              style={{ padding: "10px 0", borderBottom: "1px solid var(--ds-border-default)" }}
            >
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-800)" }}>
                  {exp.role}
                </div>
                <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)" }}>{exp.company}</div>
              </div>
              <div style={{ fontSize: 13, color: "var(--ds-ink-500)" }}>
                {exp.start_date} — {exp.end_date || "Present"}
              </div>
            </div>
          ))}
        </div>
      </DsAccordionSection>

      <DsAccordionSection
        title="Education"
        summary={`${profile.education.length} entr${profile.education.length === 1 ? "y" : "ies"}`}
        icon="◪"
      >
        <div className="flex flex-col gap-2">
          {profile.education.length === 0 && (
            <span style={{ fontSize: 13, color: "var(--ds-ink-400)" }}>
              No education added yet.
            </span>
          )}
          {profile.education.map((edu, i) => (
            <div
              key={i}
              style={{ padding: "10px 0", borderBottom: "1px solid var(--ds-border-default)" }}
            >
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-800)" }}>
                {edu.degree}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)" }}>{edu.institution}</div>
            </div>
          ))}
        </div>
      </DsAccordionSection>

      <DsAccordionSection
        title="Projects"
        summary={`${profile.projects.length} project${profile.projects.length === 1 ? "" : "s"} worth bragging about`}
        icon="◈"
      >
        <div className="flex flex-col gap-2">
          {profile.projects.length === 0 && (
            <span style={{ fontSize: 13, color: "var(--ds-ink-400)" }}>No projects added yet.</span>
          )}
          {profile.projects.map((p, i) => (
            <div
              key={i}
              style={{ padding: "10px 0", borderBottom: "1px solid var(--ds-border-default)" }}
            >
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-800)" }}>
                {p.name}
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ds-ink-500)" }}>{p.description}</div>
            </div>
          ))}
        </div>
      </DsAccordionSection>

      <DsAccordionSection
        title="Skills"
        summary={`${flatSkills.length} things you're genuinely good at`}
        icon="✦"
      >
        <textarea
          value={skillsDraft}
          onChange={(e) => setSkillsDraft(e.target.value)}
          onBlur={saveSkills}
          placeholder="Figma, SQL, public speaking — whatever you're good at"
          rows={3}
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: "10px 12px",
            borderRadius: "var(--ds-radius-md)",
            border: "1px solid var(--ds-border-medium)",
            fontSize: 13.5,
            resize: "vertical",
          }}
        />
        <div style={{ fontSize: 11.5, color: "var(--ds-ink-400)", marginTop: 6 }}>
          Separate each with a comma. We'll use these to match and tailor.
        </div>
      </DsAccordionSection>

      <DsAccordionSection
        title="Career preferences"
        summary="What counts as a good opportunity, in your words"
        icon="◆"
      >
        <p style={{ fontSize: 13, color: "var(--ds-ink-500)", margin: 0 }}>
          Set your minimum salary, locations, and work mode from the Career Preferences prompt when
          you enable Auto Apply from the Dashboard.
        </p>
      </DsAccordionSection>

      <DsAccordionSection
        title="AI preferences"
        summary={`How your resumes should sound — ${writingTone.toLowerCase()}, ${resumeStyle.toLowerCase()}`}
        icon="◉"
      >
        <div className="flex flex-col gap-4">
          <div>
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 600,
                color: "var(--ds-ink-600)",
                marginBottom: 8,
              }}
            >
              Default resume style
            </div>
            <div className="flex gap-2">
              {["Modern", "Classic", "Minimal"].map((opt) => (
                <button
                  key={opt}
                  type="button"
                  style={PILL_STYLE(resumeStyle === opt)}
                  onClick={() => setResumeStyle(opt)}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: 12.5,
                fontWeight: 600,
                color: "var(--ds-ink-600)",
                marginBottom: 8,
              }}
            >
              AI writing tone
            </div>
            <div className="flex gap-2">
              {["Professional", "Confident", "Warm"].map((opt) => (
                <button
                  key={opt}
                  type="button"
                  style={PILL_STYLE(writingTone === opt)}
                  onClick={() => setWritingTone(opt)}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        </div>
      </DsAccordionSection>

      {saveState !== "idle" && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            fontSize: 13,
            fontWeight: 600,
            color: saveState === "saved" ? "var(--ds-sage-text)" : "var(--ds-ink-450)",
            background: "var(--ds-surface-card)",
            padding: "10px 16px",
            borderRadius: "var(--ds-radius-md)",
            boxShadow: "var(--ds-shadow-card)",
          }}
        >
          {saveState === "saving" ? "Saving…" : "Saved ✓"}
        </div>
      )}

      {showReplaceModal && (
        <DsModal onClose={() => setShowReplaceModal(false)} maxWidth={480}>
          <div style={{ padding: 28 }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 18 }}>
              <h2
                className="font-[var(--ds-font-display)] font-semibold"
                style={{ fontSize: 18, margin: 0 }}
              >
                Replace resume
              </h2>
              <button
                type="button"
                onClick={() => setShowReplaceModal(false)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--ds-ink-400)",
                  fontSize: 16,
                }}
              >
                ✕
              </button>
            </div>
            <DsDropzone
              onFile={async (file) => {
                const formData = new FormData();
                formData.append("file", file);
                try {
                  await fetch(`${API_BASE}/users/upload_resume`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${session?.access_token}` },
                    body: formData,
                  });
                } catch (err) {
                  console.error("Resume upload failed:", err);
                }
                setShowReplaceModal(false);
              }}
            />
          </div>
        </DsModal>
      )}
    </div>
  );
}
