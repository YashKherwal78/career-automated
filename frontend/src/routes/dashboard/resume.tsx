import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { API_BASE } from "../../lib/api";
import { DsDropzone } from "../../components/ds/Dropzone";
import { DsModal } from "../../components/ds/Modal";

export const Route = createFileRoute("/dashboard/resume")({
  component: ResumePage,
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
  technologies: string;
}

interface EducationEntry {
  institution: string;
  degree: string;
  field_of_study: string;
}

interface CustomSectionItem {
  title: string;
  subtitle: string;
  date: string;
  description: string;
}

interface CustomSectionEntry {
  section_title: string;
  items: CustomSectionItem[];
}

interface ProfileData {
  personal_info: PersonalInfo;
  summary: string;
  skills: Record<string, string[]>;
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  education: EducationEntry[];
  certifications: string[];
  custom_sections: CustomSectionEntry[];
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
  skills: { other: [] },
  experience: [],
  projects: [],
  education: [],
  certifications: [],
  custom_sections: [],
};

function useCandidateProfile() {
  const { session } = useAuth();
  return useQuery({
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
        summary: p.summary || "",
        skills: p.skills && Object.keys(p.skills).length ? p.skills : { other: [] },
        experience: p.experience || [],
        projects: p.projects || [],
        education: p.education || [],
        certifications: p.certifications || [],
        custom_sections: p.custom_sections || [],
      };
    },
    enabled: !!session,
  });
}

function ResumePage() {
  const { session } = useAuth();
  const { data: loadedProfile, isLoading } = useCandidateProfile();
  const [mode, setMode] = useState<"chooser" | "builder">("chooser");
  const [profile, setProfile] = useState<ProfileData>(EMPTY_PROFILE);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [generateState, setGenerateState] = useState<"idle" | "generating" | "done" | "error">(
    "idle",
  );
  const [generateResult, setGenerateResult] = useState<{
    page_count: number;
    fit_achieved: boolean;
    passes_applied: string[];
    pdf_available: boolean;
  } | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);

  useEffect(() => {
    if (loadedProfile) {
      setProfile(loadedProfile);
      if (loadedProfile.experience.length > 0 || loadedProfile.personal_info.full_name) {
        setMode("builder");
      }
    }
  }, [loadedProfile]);

  const saveProfile = async () => {
    setSaveState("saving");
    try {
      const res = await fetch(`${API_BASE}/candidate/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          personal_info: profile.personal_info,
          summary: profile.summary,
          skills: profile.skills,
          experience: profile.experience,
          projects: profile.projects,
          education: profile.education,
          certifications: profile.certifications,
          custom_sections: profile.custom_sections,
        }),
      });
      if (!res.ok) throw new Error("save failed");
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 2000);
    } catch {
      setSaveState("error");
    }
  };

  const generateResume = async () => {
    setGenerateState("generating");
    setGenerateError(null);
    try {
      // Save first so generation always reflects the latest edits.
      await fetch(`${API_BASE}/candidate/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          personal_info: profile.personal_info,
          summary: profile.summary,
          skills: profile.skills,
          experience: profile.experience,
          projects: profile.projects,
          education: profile.education,
          certifications: profile.certifications,
          custom_sections: profile.custom_sections,
        }),
      });

      const res = await fetch(`${API_BASE}/candidate/generate-base-resume`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to generate resume");
      }
      const data = await res.json();
      setGenerateResult(data);
      setGenerateState("done");
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Something went wrong.");
      setGenerateState("error");
    }
  };

  const handleUploaded = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/users/extract_profile`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.access_token}` },
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setProfile({
          personal_info: { ...EMPTY_PROFILE.personal_info, ...data.personal_info },
          summary: data.summary || "",
          skills: data.skills && Object.keys(data.skills).length ? data.skills : { other: [] },
          experience: (data.experience || []).map(
            (e: {
              company: string;
              role: string;
              start_date: string;
              end_date: string;
              bullet_points?: string[];
            }) => ({
              company: e.company,
              role: e.role,
              start_date: e.start_date,
              end_date: e.end_date,
              description: (e.bullet_points || []).join("\n"),
            }),
          ),
          projects: (data.projects || []).map(
            (p: { name: string; description: string; technologies?: string[] }) => ({
              name: p.name,
              description: p.description,
              technologies: (p.technologies || []).join(", "),
            }),
          ),
          education: (data.education || []).map(
            (e: { institution: string; degree: string; field_of_study: string }) => ({
              institution: e.institution,
              degree: e.degree,
              field_of_study: e.field_of_study,
            }),
          ),
          certifications: (data.certifications || []).map((c: { name: string }) => c.name),
          custom_sections: [],
        });
      }
    } catch (err) {
      console.error("Resume parse failed:", err);
    }
    setShowUploadModal(false);
    setMode("builder");
  };

  const flatSkills = Object.values(profile.skills).flat();

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

  if (mode === "chooser") {
    return (
      <div
        className="flex items-center justify-center"
        style={{ minHeight: "100vh", padding: "clamp(32px,5vw,72px)" }}
      >
        <div
          className="text-center"
          style={{
            width: "100%",
            maxWidth: 640,
            background: "rgba(255,255,255,0.4)",
            backdropFilter: "blur(20px) saturate(160%)",
            border: "1px solid rgba(255,255,255,0.55)",
            borderRadius: "var(--ds-radius-2xl)",
            boxShadow: "var(--ds-shadow-card)",
            padding: "clamp(28px,4vw,40px)",
          }}
        >
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 13,
              letterSpacing: "var(--ds-tracking-wide)",
              color: "var(--ds-brand-orange-text)",
              marginBottom: 12,
            }}
          >
            Resume creation
          </div>
          <h1
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: "clamp(26px,3vw,34px)", margin: "0 0 12px" }}
          >
            Every good resume starts somewhere.
          </h1>
          <p
            style={{
              fontSize: 14,
              color: "var(--ds-ink-500)",
              margin: "0 0 28px",
              maxWidth: 460,
              marginInline: "auto",
            }}
          >
            Don't have one ready, or not sure yours says enough? Either way works — pick whichever
            feels easier.
          </p>
          <div
            className="grid gap-4"
            style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}
          >
            <button
              type="button"
              onClick={() => setShowUploadModal(true)}
              className="text-left transition-transform active:scale-[0.98]"
              style={{
                background: "rgba(255,255,255,0.55)",
                border: "1px solid rgba(255,255,255,0.6)",
                borderRadius: "var(--ds-radius-xl)",
                padding: 28,
                cursor: "pointer",
              }}
            >
              <div
                className="flex items-center justify-center"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "var(--ds-radius-md)",
                  background: "var(--ds-brand-orange-tint-10)",
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: 0,
                    height: 0,
                    borderLeft: "6px solid transparent",
                    borderRight: "6px solid transparent",
                    borderBottom: "7px solid var(--ds-accent-primary)",
                  }}
                />
              </div>
              <div
                className="font-[var(--ds-font-display)] font-semibold"
                style={{ fontSize: 15.5, marginBottom: 6 }}
              >
                Already have a resume?
              </div>
              <div style={{ fontSize: 13, color: "var(--ds-ink-500)" }}>
                Hand it over. We'll read it once and take it from there.
              </div>
            </button>
            <button
              type="button"
              onClick={() => setMode("builder")}
              className="text-left transition-transform active:scale-[0.98]"
              style={{
                background: "rgba(255,255,255,0.55)",
                border: "1px solid rgba(255,255,255,0.6)",
                borderRadius: "var(--ds-radius-xl)",
                padding: 28,
                cursor: "pointer",
              }}
            >
              <div
                className="flex items-center justify-center"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "var(--ds-radius-md)",
                  background: "var(--ds-sage-tint-12)",
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: 15,
                    height: 15,
                    border: "1.5px dashed var(--ds-accent-success)",
                    borderRadius: 3,
                  }}
                />
              </div>
              <div
                className="font-[var(--ds-font-display)] font-semibold"
                style={{ fontSize: 15.5, marginBottom: 6 }}
              >
                Starting fresh?
              </div>
              <div style={{ fontSize: 13, color: "var(--ds-ink-500)" }}>
                A few simple questions about your work is all it takes.
              </div>
            </button>
          </div>
        </div>

        {showUploadModal && (
          <DsModal onClose={() => setShowUploadModal(false)} maxWidth={480}>
            <div style={{ padding: 28 }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 18 }}>
                <h2
                  className="font-[var(--ds-font-display)] font-semibold"
                  style={{ fontSize: 18, margin: 0 }}
                >
                  Upload existing resume
                </h2>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
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
              <DsDropzone onFile={handleUploaded} />
            </div>
          </DsModal>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto" style={{ maxWidth: 720, padding: "48px 24px" }}>
      <div
        className="flex items-center justify-between"
        style={{
          marginBottom: 32,
          borderBottom: "1px solid var(--ds-border-default)",
          paddingBottom: 16,
        }}
      >
        <button
          type="button"
          onClick={() => setMode("chooser")}
          style={{
            fontSize: 13,
            color: "var(--ds-ink-450)",
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          ← Back
        </button>
        <button
          type="button"
          onClick={saveProfile}
          className="font-semibold"
          style={{
            padding: "10px 20px",
            borderRadius: "var(--ds-radius-md)",
            border: "none",
            background: "var(--ds-accent-primary)",
            color: "var(--ds-text-on-brand)",
            fontSize: 13.5,
            cursor: "pointer",
          }}
        >
          {saveState === "saving"
            ? "Saving…"
            : saveState === "saved"
              ? "Saved ✓"
              : saveState === "error"
                ? "Try again"
                : "Save profile"}
        </button>
      </div>

      <div className="flex flex-col gap-10">
        <div className="flex flex-col gap-3">
          <input
            type="text"
            value={profile.personal_info.full_name}
            onChange={(e) =>
              setProfile({
                ...profile,
                personal_info: { ...profile.personal_info, full_name: e.target.value },
              })
            }
            placeholder="Your full name"
            className="w-full bg-transparent border-none outline-none font-[var(--ds-font-display)] font-bold"
            style={{ fontSize: 32, color: "var(--ds-text-primary)" }}
          />
          <div className="grid grid-cols-2 gap-3" style={{ fontSize: 13 }}>
            {(["email", "phone", "location", "portfolio"] as const).map((field) => (
              <input
                key={field}
                type="text"
                value={profile.personal_info[field]}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    personal_info: { ...profile.personal_info, [field]: e.target.value },
                  })
                }
                placeholder={field[0].toUpperCase() + field.slice(1)}
                className="bg-transparent outline-none"
                style={{
                  borderBottom: "1px dashed var(--ds-border-medium)",
                  padding: "4px 0",
                  color: "var(--ds-text-primary)",
                }}
              />
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 12,
              letterSpacing: "var(--ds-tracking-wide)",
              color: "var(--ds-ink-400)",
            }}
          >
            Summary
          </div>
          <textarea
            value={profile.summary}
            onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
            placeholder="Introduce yourself and specify your target roles…"
            rows={3}
            className="w-full bg-transparent border-none outline-none resize-none"
            style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ds-text-primary)" }}
          />
        </div>

        <div className="flex flex-col gap-4">
          <div
            className="flex items-center justify-between"
            style={{ borderBottom: "1px solid var(--ds-border-default)", paddingBottom: 8 }}
          >
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 12,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-ink-400)",
              }}
            >
              Experience
            </div>
            <button
              type="button"
              onClick={() =>
                setProfile({
                  ...profile,
                  experience: [
                    ...profile.experience,
                    { company: "", role: "", start_date: "", end_date: "", description: "" },
                  ],
                })
              }
              style={{
                fontSize: 13,
                color: "var(--ds-accent-primary)",
                fontWeight: 600,
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              + Add experience
            </button>
          </div>
          {profile.experience.map((exp, idx) => (
            <div key={idx} className="flex flex-col gap-2" style={{ paddingBottom: 12 }}>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={exp.role}
                  placeholder="Role title"
                  onChange={(e) => {
                    const next = [...profile.experience];
                    next[idx] = { ...next[idx], role: e.target.value };
                    setProfile({ ...profile, experience: next });
                  }}
                  className="bg-transparent outline-none font-semibold"
                  style={{ fontSize: 14 }}
                />
                <span style={{ color: "var(--ds-ink-300)" }}>at</span>
                <input
                  value={exp.company}
                  placeholder="Company"
                  onChange={(e) => {
                    const next = [...profile.experience];
                    next[idx] = { ...next[idx], company: e.target.value };
                    setProfile({ ...profile, experience: next });
                  }}
                  className="bg-transparent outline-none font-semibold"
                  style={{ fontSize: 14 }}
                />
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      experience: profile.experience.filter((_, i) => i !== idx),
                    })
                  }
                  style={{
                    marginLeft: "auto",
                    fontSize: 12,
                    color: "#B4392C",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Remove
                </button>
              </div>
              <textarea
                value={exp.description}
                placeholder="What did you do here?"
                rows={2}
                onChange={(e) => {
                  const next = [...profile.experience];
                  next[idx] = { ...next[idx], description: e.target.value };
                  setProfile({ ...profile, experience: next });
                }}
                className="w-full bg-transparent outline-none resize-none"
                style={{ fontSize: 13, color: "var(--ds-ink-600)", lineHeight: 1.6 }}
              />
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          <div
            className="flex items-center justify-between"
            style={{ borderBottom: "1px solid var(--ds-border-default)", paddingBottom: 8 }}
          >
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 12,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-ink-400)",
              }}
            >
              Education
            </div>
            <button
              type="button"
              onClick={() =>
                setProfile({
                  ...profile,
                  education: [
                    ...profile.education,
                    { institution: "", degree: "", field_of_study: "" },
                  ],
                })
              }
              style={{
                fontSize: 13,
                color: "var(--ds-accent-primary)",
                fontWeight: 600,
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              + Add education
            </button>
          </div>
          {profile.education.map((edu, idx) => (
            <div key={idx} className="flex flex-wrap items-center gap-2">
              <input
                value={edu.institution}
                placeholder="Institution"
                onChange={(e) => {
                  const next = [...profile.education];
                  next[idx] = { ...next[idx], institution: e.target.value };
                  setProfile({ ...profile, education: next });
                }}
                className="bg-transparent outline-none font-semibold"
                style={{ fontSize: 14 }}
              />
              <input
                value={edu.degree}
                placeholder="Degree"
                onChange={(e) => {
                  const next = [...profile.education];
                  next[idx] = { ...next[idx], degree: e.target.value };
                  setProfile({ ...profile, education: next });
                }}
                className="bg-transparent outline-none"
                style={{ fontSize: 13, color: "var(--ds-ink-500)" }}
              />
              <button
                type="button"
                onClick={() =>
                  setProfile({
                    ...profile,
                    education: profile.education.filter((_, i) => i !== idx),
                  })
                }
                style={{
                  marginLeft: "auto",
                  fontSize: 12,
                  color: "#B4392C",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Remove
              </button>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          <div
            className="flex items-center justify-between"
            style={{ borderBottom: "1px solid var(--ds-border-default)", paddingBottom: 8 }}
          >
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 12,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-ink-400)",
              }}
            >
              Projects
            </div>
            <button
              type="button"
              onClick={() =>
                setProfile({
                  ...profile,
                  projects: [...profile.projects, { name: "", description: "", technologies: "" }],
                })
              }
              style={{
                fontSize: 13,
                color: "var(--ds-accent-primary)",
                fontWeight: 600,
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              + Add project
            </button>
          </div>
          {profile.projects.map((proj, idx) => (
            <div key={idx} className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <input
                  value={proj.name}
                  placeholder="Project name"
                  onChange={(e) => {
                    const next = [...profile.projects];
                    next[idx] = { ...next[idx], name: e.target.value };
                    setProfile({ ...profile, projects: next });
                  }}
                  className="bg-transparent outline-none font-semibold"
                  style={{ fontSize: 14 }}
                />
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      projects: profile.projects.filter((_, i) => i !== idx),
                    })
                  }
                  style={{
                    marginLeft: "auto",
                    fontSize: 12,
                    color: "#B4392C",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Remove
                </button>
              </div>
              <textarea
                value={proj.description}
                placeholder="Briefly describe what it does…"
                rows={1}
                onChange={(e) => {
                  const next = [...profile.projects];
                  next[idx] = { ...next[idx], description: e.target.value };
                  setProfile({ ...profile, projects: next });
                }}
                className="w-full bg-transparent outline-none resize-none"
                style={{ fontSize: 13, color: "var(--ds-ink-600)" }}
              />
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-2">
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 12,
              letterSpacing: "var(--ds-tracking-wide)",
              color: "var(--ds-ink-400)",
            }}
          >
            Skills
          </div>
          <div className="flex flex-wrap gap-1.5">
            {flatSkills.length === 0 && (
              <span style={{ fontSize: 13, color: "var(--ds-ink-400)" }}>No skills added yet.</span>
            )}
            {flatSkills.map((s) => (
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

        <div className="flex flex-col gap-4">
          <div
            className="flex items-center justify-between"
            style={{ borderBottom: "1px solid var(--ds-border-default)", paddingBottom: 8 }}
          >
            <div
              className="uppercase font-bold"
              style={{
                fontSize: 12,
                letterSpacing: "var(--ds-tracking-wide)",
                color: "var(--ds-ink-400)",
              }}
            >
              Additional sections
            </div>
            <button
              type="button"
              onClick={() =>
                setProfile({
                  ...profile,
                  custom_sections: [...profile.custom_sections, { section_title: "", items: [] }],
                })
              }
              style={{
                fontSize: 13,
                color: "var(--ds-accent-primary)",
                fontWeight: 600,
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              + Add section
            </button>
          </div>
          {profile.custom_sections.length === 0 && (
            <span style={{ fontSize: 13, color: "var(--ds-ink-400)" }}>
              For things like freelance work, achievements, or anything else that doesn't fit above.
            </span>
          )}
          {profile.custom_sections.map((sec, secIdx) => (
            <div
              key={secIdx}
              className="flex flex-col gap-3"
              style={{
                background: "var(--ds-surface-tint)",
                borderRadius: "var(--ds-radius-lg)",
                padding: 16,
              }}
            >
              <div className="flex items-center gap-2">
                <input
                  value={sec.section_title}
                  placeholder="Section name (e.g. Freelance Work)"
                  onChange={(e) => {
                    const next = [...profile.custom_sections];
                    next[secIdx] = { ...next[secIdx], section_title: e.target.value };
                    setProfile({ ...profile, custom_sections: next });
                  }}
                  className="bg-transparent outline-none font-semibold"
                  style={{ fontSize: 14 }}
                />
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      custom_sections: profile.custom_sections.filter((_, i) => i !== secIdx),
                    })
                  }
                  style={{
                    marginLeft: "auto",
                    fontSize: 12,
                    color: "#B4392C",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Remove section
                </button>
              </div>

              {sec.items.map((item, itemIdx) => (
                <div key={itemIdx} className="flex flex-col gap-2" style={{ paddingLeft: 8 }}>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      value={item.title}
                      placeholder="Title"
                      onChange={(e) => {
                        const next = [...profile.custom_sections];
                        const items = [...next[secIdx].items];
                        items[itemIdx] = { ...items[itemIdx], title: e.target.value };
                        next[secIdx] = { ...next[secIdx], items };
                        setProfile({ ...profile, custom_sections: next });
                      }}
                      className="bg-transparent outline-none font-semibold"
                      style={{ fontSize: 13.5 }}
                    />
                    <input
                      value={item.subtitle}
                      placeholder="Subtitle (optional)"
                      onChange={(e) => {
                        const next = [...profile.custom_sections];
                        const items = [...next[secIdx].items];
                        items[itemIdx] = { ...items[itemIdx], subtitle: e.target.value };
                        next[secIdx] = { ...next[secIdx], items };
                        setProfile({ ...profile, custom_sections: next });
                      }}
                      className="bg-transparent outline-none"
                      style={{ fontSize: 13, color: "var(--ds-ink-500)" }}
                    />
                    <input
                      value={item.date}
                      placeholder="Date"
                      onChange={(e) => {
                        const next = [...profile.custom_sections];
                        const items = [...next[secIdx].items];
                        items[itemIdx] = { ...items[itemIdx], date: e.target.value };
                        next[secIdx] = { ...next[secIdx], items };
                        setProfile({ ...profile, custom_sections: next });
                      }}
                      className="bg-transparent outline-none"
                      style={{ fontSize: 13, color: "var(--ds-ink-500)", width: 100 }}
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const next = [...profile.custom_sections];
                        next[secIdx] = {
                          ...next[secIdx],
                          items: next[secIdx].items.filter((_, i) => i !== itemIdx),
                        };
                        setProfile({ ...profile, custom_sections: next });
                      }}
                      style={{
                        marginLeft: "auto",
                        fontSize: 12,
                        color: "#B4392C",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      Remove
                    </button>
                  </div>
                  <textarea
                    value={item.description}
                    placeholder="One line per bullet…"
                    rows={2}
                    onChange={(e) => {
                      const next = [...profile.custom_sections];
                      const items = [...next[secIdx].items];
                      items[itemIdx] = { ...items[itemIdx], description: e.target.value };
                      next[secIdx] = { ...next[secIdx], items };
                      setProfile({ ...profile, custom_sections: next });
                    }}
                    className="w-full bg-transparent outline-none resize-none"
                    style={{ fontSize: 13, color: "var(--ds-ink-600)", lineHeight: 1.6 }}
                  />
                </div>
              ))}
              <button
                type="button"
                onClick={() => {
                  const next = [...profile.custom_sections];
                  next[secIdx] = {
                    ...next[secIdx],
                    items: [
                      ...next[secIdx].items,
                      { title: "", subtitle: "", date: "", description: "" },
                    ],
                  };
                  setProfile({ ...profile, custom_sections: next });
                }}
                style={{
                  fontSize: 12.5,
                  color: "var(--ds-accent-primary)",
                  fontWeight: 600,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  alignSelf: "flex-start",
                }}
              >
                + Add item
              </button>
            </div>
          ))}
        </div>

        <div
          className="flex flex-col gap-3"
          style={{
            borderTop: "1px solid var(--ds-border-default)",
            paddingTop: 24,
            marginTop: 8,
          }}
        >
          <div
            className="uppercase font-bold"
            style={{
              fontSize: 12,
              letterSpacing: "var(--ds-tracking-wide)",
              color: "var(--ds-ink-400)",
            }}
          >
            Base resume
          </div>
          <p style={{ fontSize: 13, color: "var(--ds-ink-500)", margin: 0, lineHeight: 1.6 }}>
            Renders everything above into a 1-page resume (Jake's Resume format), fitted and trimmed
            automatically if it runs long. This is what gets used for tailoring.
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={generateResume}
              disabled={generateState === "generating"}
              className="font-semibold"
              style={{
                padding: "10px 20px",
                borderRadius: "var(--ds-radius-md)",
                border: "none",
                background: "var(--ds-ink-900)",
                color: "var(--ds-text-on-dark)",
                fontSize: 13.5,
                cursor: generateState === "generating" ? "default" : "pointer",
                opacity: generateState === "generating" ? 0.7 : 1,
              }}
            >
              {generateState === "generating" ? "Generating…" : "Generate resume"}
            </button>
            {generateState === "done" && generateResult?.pdf_available && (
              <a
                href={`${API_BASE}/candidate/base-resume/pdf`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-accent-primary)" }}
              >
                Download PDF →
              </a>
            )}
          </div>
          {generateState === "done" && generateResult && (
            <p style={{ fontSize: 12.5, color: "var(--ds-ink-450)", margin: 0 }}>
              {generateResult.fit_achieved
                ? `Fit on ${generateResult.page_count} page${generateResult.page_count === 1 ? "" : "s"}.`
                : `Still ${generateResult.page_count} pages after trimming — consider shortening some sections.`}
              {generateResult.passes_applied.length > 0 &&
                ` Adjustments made: ${generateResult.passes_applied.join(", ")}.`}
            </p>
          )}
          {generateState === "error" && (
            <p style={{ fontSize: 12.5, color: "var(--ds-accent-danger, #C4432B)", margin: 0 }}>
              {generateError}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
