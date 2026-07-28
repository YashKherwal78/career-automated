import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { DsInput } from "../../components/ds/Input";
import { DsModal, DsModalCloseButton } from "../../components/ds/Modal";

export const Route = createFileRoute("/dashboard/applications")({
  component: ApplicationsPage,
});

type AppStatus = "Applied" | "Resume Viewed" | "Interview" | "Assessment" | "Offer" | "Rejected";

interface ApplicationRecord {
  id: string;
  company: string;
  role: string;
  location: string;
  initial: string;
  avatarBg: string;
  status: AppStatus;
  date: string;
  group: "waiting" | "finished";
  needsAction: boolean;
  statusLine: string;
  description: string;
  responsibilities: string[];
}

interface WorkingItem {
  company: string;
  role: string;
  stage: string;
}

// Frontend-only mock data — real Applications tracking API is a stub today (see plan Phase 5).
const WORKING: WorkingItem[] = [
  { company: "Figma", role: "Product Designer", stage: "Tailoring your resume for this role…" },
  { company: "Vercel", role: "Platform Engineer", stage: "Filling out the application…" },
];

const APPLICATIONS: ApplicationRecord[] = [
  {
    id: "stripe",
    company: "Stripe",
    role: "Senior Product Designer",
    location: "Remote",
    initial: "S",
    avatarBg: "#5A4FCF",
    status: "Interview",
    date: "Jul 21",
    group: "waiting",
    needsAction: true,
    statusLine: "Interview scheduled for Jul 25 — confirm when you can.",
    description:
      "Leading design for Stripe's core payments dashboard, working closely with engineering and PM.",
    responsibilities: [
      "Own end-to-end design for key merchant flows",
      "Partner with research to validate concepts",
      "Maintain design system consistency",
    ],
  },
  {
    id: "notion",
    company: "Notion",
    role: "Staff Frontend Engineer",
    location: "Remote",
    initial: "N",
    avatarBg: "#2E2E2E",
    status: "Resume Viewed",
    date: "Jul 19",
    group: "waiting",
    needsAction: false,
    statusLine: "Recruiter opened your resume 2 days ago.",
    description: "Building performant, delightful editing experiences used by millions daily.",
    responsibilities: [
      "Ship high-quality UI for the core editor",
      "Improve web performance and accessibility",
      "Mentor junior engineers",
    ],
  },
  {
    id: "razorpay",
    company: "Razorpay",
    role: "Senior Backend Engineer",
    location: "Bengaluru",
    initial: "R",
    avatarBg: "#0A6BFF",
    status: "Applied",
    date: "Jul 18",
    group: "waiting",
    needsAction: false,
    statusLine: "Applied 3 days ago — most replies take 1–2 weeks.",
    description: "Scaling payment infrastructure serving millions of transactions daily.",
    responsibilities: [
      "Design and build scalable backend services",
      "Own reliability of critical payment paths",
      "Collaborate with cross-functional teams",
    ],
  },
  {
    id: "zoho",
    company: "Zoho",
    role: "Product Manager",
    location: "Chennai",
    initial: "Z",
    avatarBg: "#C8202E",
    status: "Assessment",
    date: "Jul 17",
    group: "waiting",
    needsAction: true,
    statusLine: "A short assessment is waiting — due in 3 days.",
    description: "Owning product strategy for a core Zoho suite product.",
    responsibilities: [
      "Define product roadmap",
      "Work with engineering on execution",
      "Analyze usage data to prioritize",
    ],
  },
  {
    id: "freshworks",
    company: "Freshworks",
    role: "UX Researcher",
    location: "Chennai",
    initial: "F",
    avatarBg: "#3D9E6B",
    status: "Applied",
    date: "Jul 16",
    group: "waiting",
    needsAction: false,
    statusLine: "Applied 4 days ago — sit tight.",
    description: "Leading qualitative and quantitative research across the product suite.",
    responsibilities: [
      "Plan and run user research studies",
      "Synthesize insights for product teams",
      "Build a research repository",
    ],
  },
  {
    id: "cred",
    company: "CRED",
    role: "Design Systems Lead",
    location: "Bengaluru",
    initial: "C",
    avatarBg: "#1B1B1B",
    status: "Offer",
    date: "Jul 14",
    group: "finished",
    needsAction: true,
    statusLine: "An offer is waiting for your response.",
    description: "Owning the design system powering CRED's product suite.",
    responsibilities: [
      "Define and evolve the design system",
      "Partner with engineering on componentry",
      "Drive adoption across teams",
    ],
  },
  {
    id: "swiggy",
    company: "Swiggy",
    role: "Growth Product Manager",
    location: "Bengaluru",
    initial: "S",
    avatarBg: "#FC8019",
    status: "Rejected",
    date: "Jul 12",
    group: "finished",
    needsAction: false,
    statusLine: "Didn't move forward this time — on to the next one.",
    description: "Driving growth initiatives across Swiggy's core ordering experience.",
    responsibilities: [
      "Own growth experimentation roadmap",
      "Partner with data science on modeling",
      "Report on key growth metrics",
    ],
  },
];

const TIMELINE_STAGES: AppStatus[] = ["Applied", "Resume Viewed", "Interview", "Offer"];

const STATUS_COLOR: Record<AppStatus, string> = {
  Applied: "var(--ds-ink-400)",
  "Resume Viewed": "var(--ds-lavender-500)",
  Interview: "var(--ds-accent-primary)",
  Assessment: "var(--ds-amber-500)",
  Offer: "var(--ds-accent-success)",
  Rejected: "var(--ds-ink-300)",
};

function ApplicationDetailModal({ app, onClose }: { app: ApplicationRecord; onClose: () => void }) {
  const isRejected = app.status === "Rejected";
  const currentIndex = TIMELINE_STAGES.indexOf(app.status);

  return (
    <DsModal onClose={onClose} maxWidth={520}>
      <div style={{ padding: 28 }}>
        <div className="flex items-start justify-between gap-3" style={{ marginBottom: 18 }}>
          <div className="flex items-center gap-3.5 min-w-0">
            <div
              className="flex items-center justify-center flex-shrink-0 text-white font-bold"
              style={{
                width: 44,
                height: 44,
                borderRadius: 11,
                background: app.avatarBg,
                fontSize: 16,
              }}
            >
              {app.initial}
            </div>
            <div className="min-w-0">
              <div className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: 18 }}>
                {app.role}
              </div>
              <div style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
                {app.company} · {app.location}
              </div>
            </div>
          </div>
          <div style={{ position: "relative", width: 28, height: 28 }}>
            <DsModalCloseButton onClose={onClose} />
          </div>
        </div>

        <div
          className="flex gap-5"
          style={{
            padding: "14px 0",
            borderTop: "1px solid var(--ds-border-default)",
            borderBottom: "1px solid var(--ds-border-default)",
            marginBottom: 18,
          }}
        >
          <div>
            <div
              className="uppercase font-bold"
              style={{ fontSize: 11, color: "var(--ds-ink-400)", marginBottom: 4 }}
            >
              Status
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="rounded-full flex-shrink-0"
                style={{ width: 8, height: 8, background: STATUS_COLOR[app.status] }}
              />
              <span style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-700)" }}>
                {app.status}
              </span>
            </div>
          </div>
          <div>
            <div
              className="uppercase font-bold"
              style={{ fontSize: 11, color: "var(--ds-ink-400)", marginBottom: 4 }}
            >
              Applied
            </div>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-ink-700)" }}>
              {app.date}
            </div>
          </div>
        </div>

        <div
          className="uppercase font-bold"
          style={{ fontSize: 12.5, color: "var(--ds-ink-400)", marginBottom: 8 }}
        >
          About the role
        </div>
        <p
          style={{
            fontSize: 13.5,
            color: "var(--ds-ink-600)",
            lineHeight: 1.6,
            margin: "0 0 16px",
          }}
        >
          {app.description}
        </p>

        {!isRejected && (
          <>
            <div
              className="uppercase font-bold"
              style={{ fontSize: 12.5, color: "var(--ds-ink-400)", marginBottom: 12 }}
            >
              Timeline
            </div>
            <div className="flex items-center" style={{ marginBottom: 6 }}>
              {TIMELINE_STAGES.map((stage, i) => (
                <div key={stage} className="flex items-center" style={{ flex: 1 }}>
                  <span
                    className="rounded-full flex-shrink-0"
                    style={{
                      width: 8,
                      height: 8,
                      background:
                        i <= currentIndex ? "var(--ds-accent-primary)" : "var(--ds-border-strong)",
                    }}
                  />
                  {i < TIMELINE_STAGES.length - 1 && (
                    <div
                      className="flex-1"
                      style={{
                        height: 2,
                        background:
                          i < currentIndex
                            ? "var(--ds-accent-primary)"
                            : "var(--ds-border-default)",
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="flex" style={{ marginBottom: 20 }}>
              {TIMELINE_STAGES.map((stage) => (
                <div
                  key={stage}
                  className="font-semibold"
                  style={{ flex: 1, fontSize: 11, color: "var(--ds-ink-450)" }}
                >
                  {stage}
                </div>
              ))}
            </div>
          </>
        )}
        {isRejected && (
          <div
            style={{
              fontSize: 13,
              color: "var(--ds-ink-500)",
              background: "var(--ds-surface-tint)",
              borderRadius: "var(--ds-radius-md)",
              padding: "10px 14px",
              marginBottom: 20,
            }}
          >
            This application didn't move forward. On to the next one.
          </div>
        )}

        <div
          className="uppercase font-bold"
          style={{ fontSize: 12.5, color: "var(--ds-ink-400)", marginBottom: 8 }}
        >
          What you'll do
        </div>
        <ul
          style={{
            margin: "0 0 22px",
            paddingLeft: 18,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {app.responsibilities.map((item) => (
            <li key={item} style={{ fontSize: 13.5, color: "var(--ds-ink-600)", lineHeight: 1.5 }}>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </DsModal>
  );
}

function ApplicationsPage() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!search) return APPLICATIONS;
    const q = search.toLowerCase();
    return APPLICATIONS.filter(
      (a) => a.company.toLowerCase().includes(q) || a.role.toLowerCase().includes(q),
    );
  }, [search]);

  const waitingItems = filtered.filter((a) => a.group === "waiting");
  const finishedItems = filtered.filter((a) => a.group === "finished");
  const selected = APPLICATIONS.find((a) => a.id === selectedId) || null;

  return (
    <div style={{ padding: "40px clamp(24px,4vw,56px)" }}>
      <h1
        className="font-[var(--ds-font-display)] font-semibold"
        style={{ fontSize: "clamp(24px,2.8vw,34px)", margin: "0 0 8px" }}
      >
        Everything is moving.
      </h1>
      <p
        style={{
          fontSize: 15,
          color: "var(--ds-ink-500)",
          margin: "0 0 28px",
          maxWidth: 440,
          lineHeight: 1.6,
        }}
      >
        You don't need to check in on any of this — we'll tell you the moment something needs you.
      </p>

      <div style={{ maxWidth: 340, marginBottom: 32 }}>
        <DsInput
          placeholder="Search company or role…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {waitingItems.length === 0 && finishedItems.length === 0 ? (
        <div style={{ textAlign: "center", padding: "70px 24px" }}>
          <div
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: 16.5, marginBottom: 8 }}
          >
            No matches for "{search}".
          </div>
          <button
            type="button"
            onClick={() => setSearch("")}
            style={{
              fontSize: 13.5,
              fontWeight: 600,
              color: "var(--ds-accent-primary)",
              background: "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            Clear search
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-9">
          {WORKING.length > 0 && (
            <div>
              <div
                className="uppercase font-bold"
                style={{
                  fontSize: 12.5,
                  letterSpacing: "var(--ds-tracking-wide)",
                  color: "var(--ds-ink-400)",
                  marginBottom: 12,
                }}
              >
                Working — {WORKING.length}
              </div>
              <div className="flex flex-col gap-2.5">
                {WORKING.map((w) => (
                  <div
                    key={w.company}
                    className="flex items-center gap-3.5"
                    style={{
                      padding: "16px 18px",
                      background: "rgba(139,123,192,0.06)",
                      border: "1px solid rgba(139,123,192,0.18)",
                      borderRadius: "var(--ds-radius-lg)",
                    }}
                  >
                    <span
                      className="rounded-full flex-shrink-0 animate-pulse"
                      style={{ width: 9, height: 9, background: "var(--ds-lavender-500)" }}
                    />
                    <div className="flex-1 min-w-0">
                      <div
                        style={{ fontSize: 14, fontWeight: 600, color: "var(--ds-text-primary)" }}
                      >
                        {w.role} · {w.company}
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--ds-ink-500)", marginTop: 2 }}>
                        {w.stage}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {waitingItems.length > 0 && (
            <div>
              <div
                className="uppercase font-bold"
                style={{
                  fontSize: 12.5,
                  letterSpacing: "var(--ds-tracking-wide)",
                  color: "var(--ds-ink-400)",
                  marginBottom: 12,
                }}
              >
                Waiting — {waitingItems.length}
              </div>
              <div className="flex flex-col gap-2.5">
                {waitingItems.map((app) => (
                  <button
                    key={app.id}
                    type="button"
                    onClick={() => setSelectedId(app.id)}
                    className="flex items-center gap-3.5 text-left transition-transform hover:-translate-y-0.5"
                    style={{
                      padding: "16px 18px",
                      background: "var(--ds-surface-card)",
                      border: "1px solid var(--ds-border-default)",
                      borderRadius: "var(--ds-radius-lg)",
                    }}
                  >
                    <div
                      className="flex items-center justify-center flex-shrink-0 text-white font-bold"
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: 10,
                        background: app.avatarBg,
                        fontSize: 14,
                      }}
                    >
                      {app.initial}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div
                        className="whitespace-nowrap overflow-hidden text-ellipsis"
                        style={{ fontSize: 14.5, fontWeight: 600, color: "var(--ds-text-primary)" }}
                      >
                        {app.role} · {app.company}
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--ds-ink-500)", marginTop: 2 }}>
                        {app.statusLine}
                      </div>
                    </div>
                    {app.needsAction ? (
                      <div
                        className="flex-shrink-0 font-bold whitespace-nowrap"
                        style={{
                          fontSize: 12,
                          color: "var(--ds-brand-orange-text)",
                          background: "var(--ds-brand-orange-tint-10)",
                          padding: "6px 12px",
                          borderRadius: "var(--ds-radius-pill)",
                        }}
                      >
                        Needs you →
                      </div>
                    ) : (
                      <div
                        className="flex-shrink-0"
                        style={{ color: "var(--ds-ink-300)", fontSize: 15 }}
                      >
                        ✓
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {finishedItems.length > 0 && (
            <div>
              <div
                className="uppercase font-bold"
                style={{
                  fontSize: 12.5,
                  letterSpacing: "var(--ds-tracking-wide)",
                  color: "var(--ds-ink-400)",
                  marginBottom: 12,
                }}
              >
                Finished — {finishedItems.length}
              </div>
              <div className="flex flex-col gap-2.5">
                {finishedItems.map((app) => (
                  <button
                    key={app.id}
                    type="button"
                    onClick={() => setSelectedId(app.id)}
                    className="flex items-center gap-3.5 text-left transition-transform hover:-translate-y-0.5"
                    style={{
                      padding: "16px 18px",
                      background: "var(--ds-surface-card)",
                      border: "1px solid var(--ds-border-default)",
                      borderRadius: "var(--ds-radius-lg)",
                    }}
                  >
                    <div
                      className="flex items-center justify-center flex-shrink-0 text-white font-bold"
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: 10,
                        background: app.avatarBg,
                        fontSize: 14,
                        opacity: 0.75,
                      }}
                    >
                      {app.initial}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div
                        className="whitespace-nowrap overflow-hidden text-ellipsis"
                        style={{ fontSize: 14.5, fontWeight: 600, color: "var(--ds-ink-600)" }}
                      >
                        {app.role} · {app.company}
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)", marginTop: 2 }}>
                        {app.statusLine}
                      </div>
                    </div>
                    {app.needsAction && (
                      <div
                        className="flex-shrink-0 font-bold whitespace-nowrap"
                        style={{
                          fontSize: 12,
                          color: "var(--ds-brand-orange-text)",
                          background: "var(--ds-brand-orange-tint-10)",
                          padding: "6px 12px",
                          borderRadius: "var(--ds-radius-pill)",
                        }}
                      >
                        Needs you →
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {selected && <ApplicationDetailModal app={selected} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
