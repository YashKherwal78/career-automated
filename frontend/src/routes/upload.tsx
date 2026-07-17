import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useMemo, useState } from "react";
import { Upload, FileText, ArrowRight, Plus, X, Check, ShieldCheck } from "lucide-react";

export const Route = createFileRoute("/upload")({
  head: () => ({
    meta: [
      { title: "Upload your resume — CareerAutomated" },
      { name: "description", content: "Upload an existing resume or build one from scratch. Takes under 2 minutes." },
      { property: "og:title", content: "Upload your resume — CareerAutomated" },
      { property: "og:description", content: "Get discovered. Upload a resume or build one from scratch and we'll start matching you with opportunities." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: UploadPage,
});

type Path = "upload" | "build";

function UploadPage() {
  const [path, setPath] = useState<Path>("upload");
  const [confirmed, setConfirmed] = useState<null | { name: string; skills: string[] }>(null);

  return (
    <div className="mx-auto max-w-5xl px-6 pb-24 pt-16">
      <div className="text-center">
        <h1 className="font-display text-5xl leading-tight md:text-6xl">
          Let's get you <em className="italic">discovered</em>.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-[15px] text-ink-soft">
          Upload an existing resume, or build one from scratch — either way, takes under 2 minutes.
        </p>
      </div>

      {!confirmed && (
        <>
          <div className="mx-auto mt-10 inline-flex w-full max-w-md rounded-full border hairline bg-white p-1 text-sm">
            <button
              onClick={() => setPath("upload")}
              className={`flex-1 rounded-full px-4 py-2 transition ${path === "upload" ? "peach-gradient font-medium" : "text-ink-soft"}`}
            >
              Upload existing
            </button>
            <button
              onClick={() => setPath("build")}
              className={`flex-1 rounded-full px-4 py-2 transition ${path === "build" ? "peach-gradient font-medium" : "text-ink-soft"}`}
            >
              Build from scratch
            </button>
          </div>

          <div className="mt-10">
            {path === "upload" ? (
              <UploadPath onDone={setConfirmed} />
            ) : (
              <BuildPath onDone={setConfirmed} />
            )}
          </div>

          <p className="mx-auto mt-8 flex max-w-lg items-center justify-center gap-2 text-center text-xs text-ink-soft">
            <ShieldCheck className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" />
            Your resume is never shared with anyone without your permission.
            <Link to="/privacy" className="underline underline-offset-2">Privacy Policy</Link>
          </p>
        </>
      )}

      {confirmed && <Confirmation data={confirmed} />}
    </div>
  );
}

/* ---------- UPLOAD PATH ---------- */
function UploadPath({ onDone }: { onDone: (r: { name: string; skills: string[] }) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState<null | { name: string; skills: string[] }>(null);

  const onFile = useCallback((f: File) => {
    setFile(f);
    setParsing(true);
    setTimeout(() => {
      setParsing(false);
      setParsed({
        name: f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "),
        skills: ["React", "Node.js", "TypeScript", "PostgreSQL", "Data Structures", "System Design"],
      });
    }, 1600);
  }, []);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <label
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) onFile(f);
          }}
          className="group flex h-full min-h-[280px] cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-[color:var(--peach-deep)]/40 bg-white p-10 text-center transition hover:bg-[color:var(--peach-soft)]/40"
        >
          <div className="grid h-14 w-14 place-items-center rounded-2xl peach-gradient">
            <Upload className="h-6 w-6 text-ink" />
          </div>
          <div>
            <div className="text-lg font-medium">Drag & drop your resume</div>
            <div className="mt-1 text-xs text-ink-soft">PDF or DOCX · up to 5 MB</div>
          </div>
          <input
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFile(f);
            }}
          />
          <span className="btn-ghost-ink pointer-events-none text-sm">Or choose file</span>
        </label>
        <p className="mt-3 text-xs text-ink-soft">We'll extract your skills, projects and experience automatically.</p>
      </div>

      <div className="rounded-3xl border hairline bg-white p-6">
        {!file && (
          <div className="flex h-full min-h-[240px] flex-col items-center justify-center text-center text-sm text-ink-soft">
            <FileText className="h-8 w-8 text-ink-soft/60" />
            <div className="mt-3">Your parsed resume will appear here.</div>
          </div>
        )}

        {file && (
          <>
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl peach-gradient">
                <FileText className="h-5 w-5 text-ink" />
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{file.name}</div>
                <div className="text-xs text-ink-soft">{parsing ? "Reading resume…" : "Ready"}</div>
              </div>
            </div>

            <div className="mt-4 space-y-2 text-sm">
              <Row label="Name" value={parsed?.name ?? ""} loading={parsing} />
              <Row label="Skills" value={parsed?.skills.join(" · ") ?? ""} loading={parsing} />
              <Row label="Projects" value={parsed ? "4 detected" : ""} loading={parsing} />
              <Row label="Experience" value={parsed ? "2 detected" : ""} loading={parsing} />
            </div>

            {parsed && (
              <button
                onClick={() => onDone(parsed)}
                className="btn-peach mt-6 w-full text-sm"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b hairline py-2 last:border-0">
      <div className="text-xs uppercase tracking-widest text-ink-soft">{label}</div>
      <div className="max-w-[65%] text-right">
        {loading ? (
          <span className="inline-block h-3 w-32 animate-pulse rounded bg-secondary" />
        ) : (
          <span className="text-sm">{value || "—"}</span>
        )}
      </div>
    </div>
  );
}

/* ---------- BUILD PATH ---------- */
function BuildPath({ onDone }: { onDone: (r: { name: string; skills: string[] }) => void }) {
  const [name, setName] = useState("");
  const [education, setEducation] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [projects, setProjects] = useState<{ title: string; desc: string }[]>([{ title: "", desc: "" }]);
  const [experience, setExperience] = useState<{ role: string; company: string }[]>([{ role: "", company: "" }]);

  const canGenerate = useMemo(() => name.trim().length > 1, [name]);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-3xl border hairline bg-white p-6">
        <div className="space-y-5">
          <Field label="Full name">
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-xl border hairline bg-white px-3 py-2 text-sm outline-none focus:border-[color:var(--peach-deep)]" placeholder="Aarav Sharma" />
          </Field>

          <Field label="Education">
            <input value={education} onChange={(e) => setEducation(e.target.value)} className="w-full rounded-xl border hairline bg-white px-3 py-2 text-sm outline-none focus:border-[color:var(--peach-deep)]" placeholder="B.Tech, CSE · 2026" />
          </Field>

          <Field label="Skills">
            <div className="flex flex-wrap items-center gap-2 rounded-xl border hairline bg-white p-2">
              {skills.map((s) => (
                <span key={s} className="inline-flex items-center gap-1 rounded-full bg-[color:var(--peach-soft)] px-2.5 py-1 text-xs">
                  {s}
                  <button onClick={() => setSkills(skills.filter((x) => x !== s))}><X className="h-3 w-3" /></button>
                </span>
              ))}
              <input
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && skillInput.trim()) {
                    e.preventDefault();
                    setSkills([...new Set([...skills, skillInput.trim()])]);
                    setSkillInput("");
                  }
                }}
                className="flex-1 min-w-[120px] bg-transparent px-2 py-1 text-sm outline-none"
                placeholder="Type a skill, press Enter"
              />
            </div>
          </Field>

          <Field label="Projects">
            <div className="space-y-2">
              {projects.map((p, i) => (
                <div key={i} className="rounded-xl border hairline p-3">
                  <input
                    value={p.title}
                    onChange={(e) => setProjects(projects.map((x, xi) => (xi === i ? { ...x, title: e.target.value } : x)))}
                    className="w-full bg-transparent text-sm outline-none"
                    placeholder="Project title"
                  />
                  <input
                    value={p.desc}
                    onChange={(e) => setProjects(projects.map((x, xi) => (xi === i ? { ...x, desc: e.target.value } : x)))}
                    className="mt-1 w-full bg-transparent text-xs text-ink-soft outline-none"
                    placeholder="One-line description"
                  />
                </div>
              ))}
              <button onClick={() => setProjects([...projects, { title: "", desc: "" }])} className="inline-flex items-center gap-1 text-xs text-[color:var(--peach-deep)]">
                <Plus className="h-3 w-3" /> Add project
              </button>
            </div>
          </Field>

          <Field label="Experience">
            <div className="space-y-2">
              {experience.map((x, i) => (
                <div key={i} className="rounded-xl border hairline p-3">
                  <input
                    value={x.role}
                    onChange={(e) => setExperience(experience.map((xx, xi) => (xi === i ? { ...xx, role: e.target.value } : xx)))}
                    className="w-full bg-transparent text-sm outline-none"
                    placeholder="Role · e.g. Frontend intern"
                  />
                  <input
                    value={x.company}
                    onChange={(e) => setExperience(experience.map((xx, xi) => (xi === i ? { ...xx, company: e.target.value } : xx)))}
                    className="mt-1 w-full bg-transparent text-xs text-ink-soft outline-none"
                    placeholder="Company"
                  />
                </div>
              ))}
              <button onClick={() => setExperience([...experience, { role: "", company: "" }])} className="inline-flex items-center gap-1 text-xs text-[color:var(--peach-deep)]">
                <Plus className="h-3 w-3" /> Add experience
              </button>
            </div>
          </Field>

          <button
            disabled={!canGenerate}
            onClick={() => onDone({ name: name || "Your resume", skills })}
            className={`w-full text-sm ${canGenerate ? "btn-peach" : "btn-ghost-ink opacity-60"}`}
          >
            Generate my resume <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Live preview */}
      <div className="sticky top-24 h-fit rounded-3xl border hairline bg-white p-8 shadow-sm">
        <div className="text-xs uppercase tracking-widest text-ink-soft">Live preview</div>
        <div className="mt-2 font-display text-2xl">{name || "Your name"}</div>
        <div className="text-sm text-ink-soft">{education || "Education"}</div>

        <div className="mt-6">
          <SectionTitle>Skills</SectionTitle>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {skills.length === 0 && <span className="text-xs text-ink-soft">Skills you add will appear here.</span>}
            {skills.map((s) => (
              <span key={s} className="rounded-full bg-secondary px-2 py-0.5 text-xs">{s}</span>
            ))}
          </div>
        </div>

        <div className="mt-6">
          <SectionTitle>Projects</SectionTitle>
          <ul className="mt-2 space-y-2">
            {projects.filter((p) => p.title).map((p, i) => (
              <li key={i} className="text-sm">
                <div className="font-medium">{p.title}</div>
                <div className="text-xs text-ink-soft">{p.desc}</div>
              </li>
            ))}
            {projects.filter((p) => p.title).length === 0 && <span className="text-xs text-ink-soft">Add projects to see them here.</span>}
          </ul>
        </div>

        <div className="mt-6">
          <SectionTitle>Experience</SectionTitle>
          <ul className="mt-2 space-y-2">
            {experience.filter((e) => e.role || e.company).map((e, i) => (
              <li key={i} className="text-sm">
                <div className="font-medium">{e.role}</div>
                <div className="text-xs text-ink-soft">{e.company}</div>
              </li>
            ))}
            {experience.filter((e) => e.role || e.company).length === 0 && <span className="text-xs text-ink-soft">Add experience to see it here.</span>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs uppercase tracking-widest text-ink-soft">{label}</div>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-[10px] font-medium uppercase tracking-widest text-[color:var(--peach-deep)]">{children}</div>;
}

/* ---------- CONFIRMATION ---------- */
function Confirmation({ data }: { data: { name: string; skills: string[] } }) {
  const [skills, setSkills] = useState(data.skills);
  const [input, setInput] = useState("");
  return (
    <div className="mx-auto mt-14 max-w-2xl rounded-3xl border hairline bg-white p-8 shadow-sm">
      <div className="inline-flex items-center gap-2 rounded-full bg-[color:var(--peach-soft)] px-2.5 py-1 text-[10px] font-medium uppercase tracking-widest text-ink">
        <Check className="h-3 w-3" /> Here's what we found
      </div>
      <h2 className="mt-4 font-display text-3xl">{data.name}</h2>
      <p className="mt-2 text-sm text-ink-soft">Edit skills below. Add anything we missed — this is what matching runs on.</p>

      <div className="mt-6 flex flex-wrap items-center gap-2 rounded-2xl border hairline p-3">
        {skills.map((s) => (
          <span key={s} className="inline-flex items-center gap-1 rounded-full bg-[color:var(--peach-soft)] px-2.5 py-1 text-xs">
            {s}
            <button onClick={() => setSkills(skills.filter((x) => x !== s))}><X className="h-3 w-3" /></button>
          </span>
        ))}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && input.trim()) {
              e.preventDefault();
              setSkills([...new Set([...skills, input.trim()])]);
              setInput("");
            }
          }}
          className="flex-1 min-w-[140px] bg-transparent px-2 py-1 text-sm outline-none"
          placeholder="Add a skill, press Enter"
        />
      </div>

      <button className="btn-peach mt-8 w-full text-sm">
        Start matching me with jobs <ArrowRight className="h-4 w-4" />
      </button>
      <p className="mt-3 text-center text-xs text-ink-soft">You'll be asked to create your account next.</p>
    </div>
  );
}
