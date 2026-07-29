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

interface LanguageEntry {
  language: string;
  proficiency: string;
}

interface VolunteerEntry {
  organization: string;
  role: string;
  date: string;
  description: string;
}

interface PublicationEntry {
  title: string;
  publisher: string;
  date: string;
  url: string;
}

interface CareerPreferences {
  desired_role: string;
  work_type: string;
  locations: string;
  min_salary: string;
  open_to_relocation: boolean;
}

interface ProfileData {
  personal_info: PersonalInfo;
  summary: string;
  skills: Record<string, string[]>;
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  education: EducationEntry[];
  certifications: string[];
  achievements: string[];
  languages: LanguageEntry[];
  volunteer: VolunteerEntry[];
  publications: PublicationEntry[];
  awards: string[];
  career_preferences: CareerPreferences;
  ai_instructions: string;
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
  achievements: [],
  languages: [],
  volunteer: [],
  publications: [],
  awards: [],
  career_preferences: {
    desired_role: "",
    work_type: "",
    locations: "",
    min_salary: "",
    open_to_relocation: false,
  },
  ai_instructions: "",
  custom_sections: [],
};

function buildSavePayload(profile: ProfileData) {
  return {
    personal_info: profile.personal_info,
    summary: profile.summary,
    skills: profile.skills,
    experience: profile.experience,
    projects: profile.projects,
    education: profile.education,
    certifications: profile.certifications,
    achievements: profile.achievements,
    languages: profile.languages,
    volunteer: profile.volunteer,
    publications: profile.publications,
    awards: profile.awards,
    career_preferences: profile.career_preferences,
    ai_instructions: profile.ai_instructions,
    custom_sections: profile.custom_sections,
  };
}

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
        achievements: p.achievements || [],
        languages: p.languages || [],
        volunteer: p.volunteer || [],
        publications: p.publications || [],
        awards: p.awards || [],
        career_preferences: { ...EMPTY_PROFILE.career_preferences, ...p.career_preferences },
        ai_instructions: p.ai_instructions || "",
        custom_sections: p.custom_sections || [],
      };
    },
    enabled: !!session,
  });
}

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 12,
  letterSpacing: "var(--ds-tracking-wide)",
  color: "var(--ds-ink-400)",
};

const addLinkStyle: React.CSSProperties = {
  fontSize: 13,
  color: "var(--ds-accent-primary)",
  fontWeight: 600,
  background: "none",
  border: "none",
  cursor: "pointer",
};

const removeLinkStyle: React.CSSProperties = {
  marginLeft: "auto",
  fontSize: 12,
  color: "#B4392C",
  background: "none",
  border: "none",
  cursor: "pointer",
};

/** Collapsible section matching the design handoff's accordion builder cards. */
function AccordionSection({
  title,
  summary,
  isOpen,
  onToggle,
  children,
  action,
}: {
  title: string;
  summary: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div
      style={{
        border: "1px solid var(--ds-border-default)",
        borderRadius: "var(--ds-radius-lg)",
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between"
        style={{
          padding: "14px 18px",
          background: "var(--ds-surface-tint)",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <div>
          <div className="font-semibold" style={{ fontSize: 14.5 }}>
            {title}
          </div>
          <div style={{ fontSize: 12, color: "var(--ds-ink-450)" }}>{summary}</div>
        </div>
        <div
          style={{
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 200ms ease",
            fontSize: 12,
            color: "var(--ds-ink-400)",
          }}
        >
          ▾
        </div>
      </button>
      {isOpen && (
        <div className="flex flex-col gap-3" style={{ padding: 18 }}>
          {children}
          {action}
        </div>
      )}
    </div>
  );
}

/** Simple editable list of plain strings (Achievements, Awards). */
function StringListEditor({
  items,
  onChange,
  placeholder,
}: {
  items: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      {items.map((item, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <input
            value={item}
            placeholder={placeholder}
            onChange={(e) => {
              const next = [...items];
              next[idx] = e.target.value;
              onChange(next);
            }}
            className="bg-transparent outline-none flex-1"
            style={{
              fontSize: 13.5,
              borderBottom: "1px dashed var(--ds-border-medium)",
              padding: "4px 0",
            }}
          />
          <button
            type="button"
            onClick={() => onChange(items.filter((_, i) => i !== idx))}
            style={removeLinkStyle}
          >
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...items, ""])} style={addLinkStyle}>
        + Add
      </button>
    </div>
  );
}

function SkillsEditor({
  skills,
  onChange,
}: {
  skills: Record<string, string[]>;
  onChange: (next: Record<string, string[]>) => void;
}) {
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const categories = Object.keys(skills).length ? Object.keys(skills) : ["other"];

  const commitDraft = (category: string) => {
    const raw = drafts[category] || "";
    const additions = raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!additions.length) return;
    onChange({
      ...skills,
      [category]: [...(skills[category] || []), ...additions],
    });
    setDrafts({ ...drafts, [category]: "" });
  };

  const removeSkill = (category: string, skill: string) => {
    onChange({ ...skills, [category]: (skills[category] || []).filter((s) => s !== skill) });
  };

  return (
    <div className="flex flex-col gap-4">
      {categories.map((category) => (
        <div key={category} className="flex flex-col gap-2">
          <div
            className="uppercase font-bold"
            style={{ fontSize: 11, color: "var(--ds-ink-400)", letterSpacing: "0.5px" }}
          >
            {category.replace(/_/g, " ")}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(skills[category] || []).map((s) => (
              <span
                key={s}
                className="font-semibold flex items-center gap-1"
                style={{
                  fontSize: 12.5,
                  color: "var(--ds-ink-600)",
                  background: "var(--ds-surface-tint)",
                  padding: "5px 8px 5px 11px",
                  borderRadius: "var(--ds-radius-pill)",
                }}
              >
                {s}
                <button
                  type="button"
                  onClick={() => removeSkill(category, s)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--ds-ink-400)",
                    fontSize: 12,
                    lineHeight: 1,
                    padding: 0,
                  }}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
          <input
            value={drafts[category] || ""}
            placeholder="Type skills, comma-separated, then press Enter"
            onChange={(e) => setDrafts({ ...drafts, [category]: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commitDraft(category);
              }
            }}
            onBlur={() => commitDraft(category)}
            className="bg-transparent outline-none"
            style={{
              fontSize: 13,
              borderBottom: "1px dashed var(--ds-border-medium)",
              padding: "4px 0",
            }}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => {
          const name = window.prompt("New skill category name (e.g. Tools, Soft Skills)");
          if (name && !skills[name]) onChange({ ...skills, [name]: [] });
        }}
        style={{ ...addLinkStyle, alignSelf: "flex-start" }}
      >
        + Add category
      </button>
    </div>
  );
}

function ResumePage() {
  const { session } = useAuth();
  const { data: loadedProfile, isLoading } = useCandidateProfile();
  const [mode, setMode] = useState<"chooser" | "builder">("chooser");
  const [profile, setProfile] = useState<ProfileData>(EMPTY_PROFILE);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [draftState, setDraftState] = useState<"idle" | "saving" | "saved">("idle");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    personal: true,
  });
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

  const toggleSection = (key: string) =>
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));

  const saveProfile = async () => {
    setSaveState("saving");
    try {
      const res = await fetch(`${API_BASE}/candidate/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify(buildSavePayload(profile)),
      });
      if (!res.ok) throw new Error("save failed");
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 2000);
    } catch {
      setSaveState("error");
    }
  };

  const saveDraft = async () => {
    setDraftState("saving");
    try {
      const res = await fetch(`${API_BASE}/candidate/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify(buildSavePayload(profile)),
      });
      if (!res.ok) throw new Error("save failed");
      setDraftState("saved");
      setTimeout(() => setDraftState("idle"), 2000);
    } catch {
      setDraftState("idle");
    }
  };

  const generateResume = async () => {
    setGenerateState("generating");
    setGenerateError(null);
    try {
      await fetch(`${API_BASE}/candidate/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify(buildSavePayload(profile)),
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
          ...EMPTY_PROFILE,
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
            (p: {
              name: string;
              description: string;
              bullet_points?: string[];
              technologies?: string[];
            }) => ({
              name: p.name,
              description: p.bullet_points?.length
                ? p.bullet_points.join("\n")
                : p.description || "",
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
                <div className="relative" style={{ width: 12, height: 15 }}>
                  <div
                    style={{
                      position: "absolute",
                      bottom: 0,
                      left: 0,
                      width: 12,
                      height: 2,
                      borderRadius: 1,
                      background: "var(--ds-accent-primary)",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      bottom: 2,
                      left: 5,
                      width: 2,
                      height: 10,
                      background: "var(--ds-accent-primary)",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 1.5,
                      width: 0,
                      height: 0,
                      borderLeft: "4.5px solid transparent",
                      borderRight: "4.5px solid transparent",
                      borderBottom: "5px solid var(--ds-accent-primary)",
                    }}
                  />
                </div>
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
                  className="relative flex items-center justify-center"
                  style={{
                    width: 15,
                    height: 15,
                    border: "1.5px dashed var(--ds-accent-success)",
                    borderRadius: 3,
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      width: 7,
                      height: 1.5,
                      background: "var(--ds-accent-success)",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      width: 1.5,
                      height: 7,
                      background: "var(--ds-accent-success)",
                    }}
                  />
                </div>
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
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={saveDraft}
            className="font-semibold"
            style={{
              padding: "10px 16px",
              borderRadius: "var(--ds-radius-md)",
              border: "1px solid var(--ds-border-medium)",
              background: "transparent",
              color: "var(--ds-ink-700)",
              fontSize: 13.5,
              cursor: "pointer",
            }}
          >
            {draftState === "saving"
              ? "Saving…"
              : draftState === "saved"
                ? "Draft saved ✓"
                : "Save draft"}
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
      </div>

      <div className="flex flex-col gap-3" style={{ marginBottom: 32 }}>
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
          {(["email", "phone", "location", "portfolio", "linkedin", "github"] as const).map(
            (field) => (
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
            ),
          )}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <AccordionSection
          title="Summary"
          summary={profile.summary ? "Added" : "Not added yet"}
          isOpen={!!openSections.summary}
          onToggle={() => toggleSection("summary")}
        >
          <textarea
            value={profile.summary}
            onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
            placeholder="Introduce yourself and specify your target roles…"
            rows={3}
            className="w-full bg-transparent border-none outline-none resize-none"
            style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ds-text-primary)" }}
          />
        </AccordionSection>

        <AccordionSection
          title="Experience"
          summary={
            profile.experience.length
              ? `${profile.experience.length} ${profile.experience.length === 1 ? "entry" : "entries"}`
              : "None added yet"
          }
          isOpen={!!openSections.experience}
          onToggle={() => toggleSection("experience")}
        >
          {profile.experience.map((exp, idx) => (
            <div
              key={idx}
              className="flex flex-col gap-2"
              style={{
                paddingBottom: 12,
                borderBottom:
                  idx < profile.experience.length - 1
                    ? "1px solid var(--ds-border-default)"
                    : "none",
              }}
            >
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
                  style={removeLinkStyle}
                >
                  Remove
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={exp.start_date}
                  placeholder="Start date"
                  onChange={(e) => {
                    const next = [...profile.experience];
                    next[idx] = { ...next[idx], start_date: e.target.value };
                    setProfile({ ...profile, experience: next });
                  }}
                  className="bg-transparent outline-none"
                  style={{ fontSize: 12.5, color: "var(--ds-ink-500)", width: 110 }}
                />
                <span style={{ color: "var(--ds-ink-300)" }}>–</span>
                <input
                  value={exp.end_date}
                  placeholder="End date"
                  onChange={(e) => {
                    const next = [...profile.experience];
                    next[idx] = { ...next[idx], end_date: e.target.value };
                    setProfile({ ...profile, experience: next });
                  }}
                  className="bg-transparent outline-none"
                  style={{ fontSize: 12.5, color: "var(--ds-ink-500)", width: 110 }}
                />
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
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add experience
          </button>
        </AccordionSection>

        <AccordionSection
          title="Education"
          summary={
            profile.education.length
              ? `${profile.education.length} ${profile.education.length === 1 ? "entry" : "entries"}`
              : "None added yet"
          }
          isOpen={!!openSections.education}
          onToggle={() => toggleSection("education")}
        >
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
                style={removeLinkStyle}
              >
                Remove
              </button>
            </div>
          ))}
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
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add education
          </button>
        </AccordionSection>

        <AccordionSection
          title="Projects"
          summary={
            profile.projects.length
              ? `${profile.projects.length} ${profile.projects.length === 1 ? "entry" : "entries"}`
              : "None added yet"
          }
          isOpen={!!openSections.projects}
          onToggle={() => toggleSection("projects")}
        >
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
                  style={removeLinkStyle}
                >
                  Remove
                </button>
              </div>
              <input
                value={proj.technologies}
                placeholder="Technologies (comma-separated)"
                onChange={(e) => {
                  const next = [...profile.projects];
                  next[idx] = { ...next[idx], technologies: e.target.value };
                  setProfile({ ...profile, projects: next });
                }}
                className="bg-transparent outline-none"
                style={{ fontSize: 12.5, color: "var(--ds-ink-500)" }}
              />
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
          <button
            type="button"
            onClick={() =>
              setProfile({
                ...profile,
                projects: [...profile.projects, { name: "", description: "", technologies: "" }],
              })
            }
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add project
          </button>
        </AccordionSection>

        <AccordionSection
          title="Skills"
          summary={flatSkills.length ? `${flatSkills.length} skills` : "None added yet"}
          isOpen={!!openSections.skills}
          onToggle={() => toggleSection("skills")}
        >
          <SkillsEditor
            skills={profile.skills}
            onChange={(skills) => setProfile({ ...profile, skills })}
          />
        </AccordionSection>

        <AccordionSection
          title="Certifications"
          summary={
            profile.certifications.length
              ? `${profile.certifications.length} entries`
              : "None added yet"
          }
          isOpen={!!openSections.certifications}
          onToggle={() => toggleSection("certifications")}
        >
          <StringListEditor
            items={profile.certifications}
            placeholder="e.g. AWS Certified Solutions Architect"
            onChange={(certifications) => setProfile({ ...profile, certifications })}
          />
        </AccordionSection>

        <AccordionSection
          title="Achievements"
          summary={
            profile.achievements.length
              ? `${profile.achievements.length} entries`
              : "None added yet"
          }
          isOpen={!!openSections.achievements}
          onToggle={() => toggleSection("achievements")}
        >
          <StringListEditor
            items={profile.achievements}
            placeholder="e.g. Led a team that shipped X, reducing Y by 40%"
            onChange={(achievements) => setProfile({ ...profile, achievements })}
          />
        </AccordionSection>

        <AccordionSection
          title="Awards"
          summary={profile.awards.length ? `${profile.awards.length} entries` : "None added yet"}
          isOpen={!!openSections.awards}
          onToggle={() => toggleSection("awards")}
        >
          <StringListEditor
            items={profile.awards}
            placeholder="e.g. Dean's List, 2023"
            onChange={(awards) => setProfile({ ...profile, awards })}
          />
        </AccordionSection>

        <AccordionSection
          title="Languages"
          summary={
            profile.languages.length ? `${profile.languages.length} entries` : "None added yet"
          }
          isOpen={!!openSections.languages}
          onToggle={() => toggleSection("languages")}
        >
          {profile.languages.map((lang, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                value={lang.language}
                placeholder="Language"
                onChange={(e) => {
                  const next = [...profile.languages];
                  next[idx] = { ...next[idx], language: e.target.value };
                  setProfile({ ...profile, languages: next });
                }}
                className="bg-transparent outline-none font-semibold"
                style={{ fontSize: 13.5 }}
              />
              <input
                value={lang.proficiency}
                placeholder="Proficiency (e.g. Fluent)"
                onChange={(e) => {
                  const next = [...profile.languages];
                  next[idx] = { ...next[idx], proficiency: e.target.value };
                  setProfile({ ...profile, languages: next });
                }}
                className="bg-transparent outline-none"
                style={{ fontSize: 13, color: "var(--ds-ink-500)" }}
              />
              <button
                type="button"
                onClick={() =>
                  setProfile({
                    ...profile,
                    languages: profile.languages.filter((_, i) => i !== idx),
                  })
                }
                style={removeLinkStyle}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setProfile({
                ...profile,
                languages: [...profile.languages, { language: "", proficiency: "" }],
              })
            }
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add language
          </button>
        </AccordionSection>

        <AccordionSection
          title="Volunteer experience"
          summary={
            profile.volunteer.length ? `${profile.volunteer.length} entries` : "None added yet"
          }
          isOpen={!!openSections.volunteer}
          onToggle={() => toggleSection("volunteer")}
        >
          {profile.volunteer.map((v, idx) => (
            <div key={idx} className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={v.role}
                  placeholder="Role"
                  onChange={(e) => {
                    const next = [...profile.volunteer];
                    next[idx] = { ...next[idx], role: e.target.value };
                    setProfile({ ...profile, volunteer: next });
                  }}
                  className="bg-transparent outline-none font-semibold"
                  style={{ fontSize: 14 }}
                />
                <span style={{ color: "var(--ds-ink-300)" }}>at</span>
                <input
                  value={v.organization}
                  placeholder="Organization"
                  onChange={(e) => {
                    const next = [...profile.volunteer];
                    next[idx] = { ...next[idx], organization: e.target.value };
                    setProfile({ ...profile, volunteer: next });
                  }}
                  className="bg-transparent outline-none font-semibold"
                  style={{ fontSize: 14 }}
                />
                <input
                  value={v.date}
                  placeholder="Date"
                  onChange={(e) => {
                    const next = [...profile.volunteer];
                    next[idx] = { ...next[idx], date: e.target.value };
                    setProfile({ ...profile, volunteer: next });
                  }}
                  className="bg-transparent outline-none"
                  style={{ fontSize: 12.5, color: "var(--ds-ink-500)", width: 100 }}
                />
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      volunteer: profile.volunteer.filter((_, i) => i !== idx),
                    })
                  }
                  style={removeLinkStyle}
                >
                  Remove
                </button>
              </div>
              <textarea
                value={v.description}
                placeholder="What did you do?"
                rows={1}
                onChange={(e) => {
                  const next = [...profile.volunteer];
                  next[idx] = { ...next[idx], description: e.target.value };
                  setProfile({ ...profile, volunteer: next });
                }}
                className="w-full bg-transparent outline-none resize-none"
                style={{ fontSize: 13, color: "var(--ds-ink-600)" }}
              />
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setProfile({
                ...profile,
                volunteer: [
                  ...profile.volunteer,
                  { organization: "", role: "", date: "", description: "" },
                ],
              })
            }
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add volunteer experience
          </button>
        </AccordionSection>

        <AccordionSection
          title="Publications"
          summary={
            profile.publications.length
              ? `${profile.publications.length} entries`
              : "None added yet"
          }
          isOpen={!!openSections.publications}
          onToggle={() => toggleSection("publications")}
        >
          {profile.publications.map((pub, idx) => (
            <div key={idx} className="flex flex-wrap items-center gap-2">
              <input
                value={pub.title}
                placeholder="Title"
                onChange={(e) => {
                  const next = [...profile.publications];
                  next[idx] = { ...next[idx], title: e.target.value };
                  setProfile({ ...profile, publications: next });
                }}
                className="bg-transparent outline-none font-semibold"
                style={{ fontSize: 14 }}
              />
              <input
                value={pub.publisher}
                placeholder="Publisher"
                onChange={(e) => {
                  const next = [...profile.publications];
                  next[idx] = { ...next[idx], publisher: e.target.value };
                  setProfile({ ...profile, publications: next });
                }}
                className="bg-transparent outline-none"
                style={{ fontSize: 13, color: "var(--ds-ink-500)" }}
              />
              <input
                value={pub.date}
                placeholder="Date"
                onChange={(e) => {
                  const next = [...profile.publications];
                  next[idx] = { ...next[idx], date: e.target.value };
                  setProfile({ ...profile, publications: next });
                }}
                className="bg-transparent outline-none"
                style={{ fontSize: 12.5, color: "var(--ds-ink-500)", width: 100 }}
              />
              <button
                type="button"
                onClick={() =>
                  setProfile({
                    ...profile,
                    publications: profile.publications.filter((_, i) => i !== idx),
                  })
                }
                style={removeLinkStyle}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setProfile({
                ...profile,
                publications: [
                  ...profile.publications,
                  { title: "", publisher: "", date: "", url: "" },
                ],
              })
            }
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add publication
          </button>
        </AccordionSection>

        <AccordionSection
          title="Career preferences"
          summary={profile.career_preferences.desired_role ? "Set" : "Not set yet"}
          isOpen={!!openSections.career_preferences}
          onToggle={() => toggleSection("career_preferences")}
        >
          <div className="grid grid-cols-2 gap-3">
            <input
              value={profile.career_preferences.desired_role}
              placeholder="Desired role"
              onChange={(e) =>
                setProfile({
                  ...profile,
                  career_preferences: {
                    ...profile.career_preferences,
                    desired_role: e.target.value,
                  },
                })
              }
              className="bg-transparent outline-none"
              style={{
                fontSize: 13.5,
                borderBottom: "1px dashed var(--ds-border-medium)",
                padding: "4px 0",
              }}
            />
            <input
              value={profile.career_preferences.work_type}
              placeholder="Work type (Remote / Hybrid / On-site)"
              onChange={(e) =>
                setProfile({
                  ...profile,
                  career_preferences: { ...profile.career_preferences, work_type: e.target.value },
                })
              }
              className="bg-transparent outline-none"
              style={{
                fontSize: 13.5,
                borderBottom: "1px dashed var(--ds-border-medium)",
                padding: "4px 0",
              }}
            />
            <input
              value={profile.career_preferences.locations}
              placeholder="Preferred locations"
              onChange={(e) =>
                setProfile({
                  ...profile,
                  career_preferences: { ...profile.career_preferences, locations: e.target.value },
                })
              }
              className="bg-transparent outline-none"
              style={{
                fontSize: 13.5,
                borderBottom: "1px dashed var(--ds-border-medium)",
                padding: "4px 0",
              }}
            />
            <input
              value={profile.career_preferences.min_salary}
              placeholder="Minimum salary"
              onChange={(e) =>
                setProfile({
                  ...profile,
                  career_preferences: { ...profile.career_preferences, min_salary: e.target.value },
                })
              }
              className="bg-transparent outline-none"
              style={{
                fontSize: 13.5,
                borderBottom: "1px dashed var(--ds-border-medium)",
                padding: "4px 0",
              }}
            />
          </div>
          <label className="flex items-center gap-2" style={{ fontSize: 13.5, marginTop: 4 }}>
            <input
              type="checkbox"
              checked={profile.career_preferences.open_to_relocation}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  career_preferences: {
                    ...profile.career_preferences,
                    open_to_relocation: e.target.checked,
                  },
                })
              }
            />
            Open to relocation
          </label>
        </AccordionSection>

        <AccordionSection
          title="AI instructions"
          summary={profile.ai_instructions ? "Set" : "Not set yet"}
          isOpen={!!openSections.ai_instructions}
          onToggle={() => toggleSection("ai_instructions")}
        >
          <p style={{ fontSize: 12.5, color: "var(--ds-ink-450)", margin: "0 0 4px" }}>
            Guidance the tailoring engine follows every time it rewrites your resume — tone,
            emphasis, anything to always keep in mind.
          </p>
          <textarea
            value={profile.ai_instructions}
            onChange={(e) => setProfile({ ...profile, ai_instructions: e.target.value })}
            placeholder="e.g. Always lead with impact metrics. Keep language direct, no buzzwords."
            rows={3}
            className="w-full bg-transparent outline-none resize-none"
            style={{
              fontSize: 13.5,
              lineHeight: 1.6,
              border: "1px solid var(--ds-border-default)",
              borderRadius: "var(--ds-radius-md)",
              padding: 10,
              boxSizing: "border-box",
            }}
          />
        </AccordionSection>

        <AccordionSection
          title="Additional sections"
          summary={
            profile.custom_sections.length
              ? `${profile.custom_sections.length} sections`
              : "For freelance work, or anything else"
          }
          isOpen={!!openSections.custom}
          onToggle={() => toggleSection("custom")}
        >
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
                  style={removeLinkStyle}
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
                      style={removeLinkStyle}
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
                style={{ ...addLinkStyle, alignSelf: "flex-start" }}
              >
                + Add item
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setProfile({
                ...profile,
                custom_sections: [...profile.custom_sections, { section_title: "", items: [] }],
              })
            }
            style={{ ...addLinkStyle, alignSelf: "flex-start" }}
          >
            + Add section
          </button>
        </AccordionSection>
      </div>

      <div
        className="flex flex-col gap-3"
        style={{
          borderTop: "1px solid var(--ds-border-default)",
          paddingTop: 24,
          marginTop: 24,
        }}
      >
        <div style={sectionTitleStyle} className="uppercase font-bold">
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
  );
}
