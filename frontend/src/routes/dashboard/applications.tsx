import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ServiceRegistry } from "../../lib/services";
import { DsInput } from "../../components/ds/Input";
import { DsButton } from "../../components/ds/Button";
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

// Real Applications tracking is being built after auto-apply ships — until
// then this stays an honest empty state rather than mock data.
const WORKING: WorkingItem[] = [];

const APPLICATIONS: ApplicationRecord[] = [];

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

function SkeletonRow() {
  return (
    <div
      className="flex items-center gap-3.5 animate-pulse"
      style={{
        padding: "16px 18px",
        background: "var(--ds-surface-card)",
        border: "1px solid var(--ds-border-default)",
        borderRadius: "var(--ds-radius-lg)",
      }}
    >
      <div
        className="flex-shrink-0"
        style={{ width: 38, height: 38, borderRadius: 10, background: "var(--ds-surface-tint)" }}
      />
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <div
          style={{
            height: 12,
            width: "50%",
            borderRadius: 4,
            background: "var(--ds-surface-tint)",
          }}
        />
        <div
          style={{
            height: 10,
            width: "70%",
            borderRadius: 4,
            background: "var(--ds-surface-tint)",
          }}
        />
      </div>
    </div>
  );
}

function ApplicationsPage() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const queryClient = useQueryClient();

  const { data: needsReview = [] } = useQuery({
    queryKey: ["needs-review"],
    queryFn: () => ServiceRegistry.getJobService().getNeedsReview(),
    refetchInterval: 10000,
  });

  const { data: referralDrafts = [] } = useQuery({
    queryKey: ["referral-drafts"],
    queryFn: () => ServiceRegistry.getReferralService().list(),
    refetchInterval: 10000,
  });
  const pendingReferrals = referralDrafts.filter((r) => r.status === "PENDING_REVIEW");
  const [referralActionState, setReferralActionState] = useState<Record<string, "working" | "error">>({});
  const [expandedReferralId, setExpandedReferralId] = useState<string | null>(null);

  const handleApproveReferral = async (id: string) => {
    setReferralActionState((s) => ({ ...s, [id]: "working" }));
    try {
      await ServiceRegistry.getReferralService().approve(id);
      queryClient.invalidateQueries({ queryKey: ["referral-drafts"] });
    } catch (e) {
      console.error("Failed to approve referral:", e);
      setReferralActionState((s) => ({ ...s, [id]: "error" }));
    }
  };

  const handleRejectReferral = async (id: string) => {
    setReferralActionState((s) => ({ ...s, [id]: "working" }));
    try {
      await ServiceRegistry.getReferralService().reject(id);
      queryClient.invalidateQueries({ queryKey: ["referral-drafts"] });
    } catch (e) {
      console.error("Failed to reject referral:", e);
      setReferralActionState((s) => ({ ...s, [id]: "error" }));
    }
  };

  // Opens the real job page and tells the CareerAutomated extension (via a
  // query param its content scripts check for) to fill the form
  // automatically instead of waiting for a manual click on its own
  // "Autofill" button -- by the time the tab finishes loading, all that's
  // left for a REVIEW_REQUIRED application is the CAPTCHA and Submit.
  // Requires the extension to be installed; if it isn't, this just opens
  // the plain job page.
  const handleOpenAndAutofill = (applyUrl: string) => {
    if (!applyUrl) return;
    const sep = applyUrl.includes("?") ? "&" : "?";
    window.open(`${applyUrl}${sep}_careerautomated_autofill=1`, "_blank", "noopener");
  };

  useEffect(() => {
    const t = setTimeout(() => setLoaded(true), 300);
    return () => clearTimeout(t);
  }, []);

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
        {APPLICATIONS.length === 0 ? "No applications yet." : "Everything is moving."}
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
        {APPLICATIONS.length === 0
          ? "Applications you send — or we send for you — will show up here."
          : "You don't need to check in on any of this — we'll tell you the moment something needs you."}
      </p>

      {needsReview.length > 0 && (
        <div
          style={{
            background: "var(--ds-brand-orange-tint-08)",
            border: "1px solid rgba(255,255,255,0.6)",
            borderRadius: "var(--ds-radius-xl)",
            padding: "24px 26px",
            marginBottom: 28,
            maxWidth: 860,
          }}
        >
          <div
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: 16, marginBottom: 16 }}
          >
            Needs your attention ({needsReview.length})
          </div>
          <div className="flex flex-col" style={{ gap: 12 }}>
            {needsReview.slice(0, 8).map((item) => (
              <div
                key={item.job_id}
                style={{
                  background: "rgba(255,255,255,0.7)",
                  borderRadius: "var(--ds-radius-lg)",
                  padding: "16px 18px",
                }}
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div style={{ minWidth: 0, flex: "1 1 320px" }}>
                    <div style={{ fontSize: 14.5, fontWeight: 600, lineHeight: 1.4 }}>
                      {item.title || "Untitled role"}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)", marginTop: 3 }}>
                      {item.provider}
                      {item.job_score != null ? ` · ${item.job_score}% match` : ""}
                    </div>
                  </div>
                  <span
                    className="font-semibold uppercase flex-shrink-0"
                    style={{
                      fontSize: 10.5,
                      letterSpacing: 0.4,
                      color: "var(--ds-brand-orange-text)",
                      background: "var(--ds-cream-300)",
                      padding: "5px 10px",
                      borderRadius: "var(--ds-radius-pill)",
                    }}
                  >
                    {item.status.replace(/_/g, " ")}
                  </span>
                </div>

                {item.reason && (
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--ds-ink-500)",
                      lineHeight: 1.5,
                      marginTop: 10,
                      paddingTop: 10,
                      borderTop: "1px solid rgba(0,0,0,0.06)",
                    }}
                  >
                    {item.reason}
                  </div>
                )}

                {item.apply_url && (
                  <div style={{ marginTop: 14 }}>
                    <DsButton variant="primary" size="md" onClick={() => handleOpenAndAutofill(item.apply_url)}>
                      Open & Autofill
                    </DsButton>
                  </div>
                )}
              </div>
            ))}
          </div>
          <p style={{ fontSize: 11.5, color: "var(--ds-ink-450)", lineHeight: 1.5, margin: "16px 0 0" }}>
            "Open & Autofill" needs the CareerAutomated browser extension installed — it fills the form in your
            own browser, so all that's usually left is the CAPTCHA and Submit.
          </p>
        </div>
      )}

      {pendingReferrals.length > 0 && (
        <div
          style={{
            background: "var(--ds-surface-tint)",
            border: "1px solid rgba(255,255,255,0.6)",
            borderRadius: "var(--ds-radius-xl)",
            padding: "24px 26px",
            marginBottom: 28,
            maxWidth: 860,
          }}
        >
          <div
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: 16, marginBottom: 6 }}
          >
            Referral emails to review ({pendingReferrals.length})
          </div>
          <p style={{ fontSize: 13, color: "var(--ds-ink-500)", lineHeight: 1.5, margin: "0 0 16px" }}>
            Drafted for people at companies you've applied to. Review and approve to send — nothing goes out
            without your OK yet.
          </p>
          <div className="flex flex-col" style={{ gap: 12 }}>
            {pendingReferrals.slice(0, 5).map((r) => {
              const isExpanded = expandedReferralId === r.id;
              return (
                <div
                  key={r.id}
                  style={{
                    background: "rgba(255,255,255,0.7)",
                    borderRadius: "var(--ds-radius-lg)",
                    padding: "16px 18px",
                  }}
                >
                  <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.4 }}>
                    {r.contact_name}
                    <span style={{ color: "var(--ds-ink-450)", fontWeight: 500 }}>
                      {" "}
                      · {r.company_name} — {r.job_title}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--ds-ink-450)", marginTop: 2 }}>{r.contact_email}</div>

                  <button
                    type="button"
                    onClick={() => setExpandedReferralId(isExpanded ? null : r.id)}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      background: "rgba(0,0,0,0.03)",
                      border: "none",
                      borderRadius: "var(--ds-radius-md)",
                      padding: "10px 12px",
                      marginTop: 12,
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: isExpanded ? 8 : 0 }}>
                      {r.subject}
                    </div>
                    <div
                      style={{
                        fontSize: 12.5,
                        color: "var(--ds-ink-600)",
                        lineHeight: 1.6,
                        whiteSpace: "pre-wrap",
                        display: isExpanded ? "block" : "-webkit-box",
                        WebkitLineClamp: isExpanded ? undefined : 2,
                        WebkitBoxOrient: isExpanded ? undefined : "vertical",
                        overflow: isExpanded ? "visible" : "hidden",
                      }}
                    >
                      {r.body}
                    </div>
                    <span
                      style={{
                        fontSize: 11.5,
                        color: "var(--ds-ink-400)",
                        fontWeight: 600,
                        display: "inline-block",
                        marginTop: 6,
                      }}
                    >
                      {isExpanded ? "Show less ↑" : "Show full email ↓"}
                    </span>
                  </button>

                  <div className="flex items-center gap-2.5" style={{ marginTop: 14 }}>
                    <DsButton
                      variant="primary"
                      size="md"
                      disabled={referralActionState[r.id] === "working"}
                      onClick={() => handleApproveReferral(r.id)}
                    >
                      {referralActionState[r.id] === "working" ? "Sending…" : "Approve & send"}
                    </DsButton>
                    <DsButton
                      variant="outline"
                      size="md"
                      disabled={referralActionState[r.id] === "working"}
                      onClick={() => handleRejectReferral(r.id)}
                    >
                      Reject
                    </DsButton>
                    {referralActionState[r.id] === "error" && (
                      <span style={{ fontSize: 12, color: "#B4392C" }}>Failed — try again</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div style={{ maxWidth: 340, marginBottom: 32 }}>
        <DsInput
          placeholder="Search company or role…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {!loaded ? (
        <div className="flex flex-col gap-2.5">
          {[0, 1, 2].map((i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      ) : APPLICATIONS.length === 0 ? (
        <div style={{ textAlign: "center", padding: "70px 24px" }}>
          <div
            className="font-[var(--ds-font-display)] font-semibold"
            style={{ fontSize: 16.5, marginBottom: 8 }}
          >
            Your applications will show up here.
          </div>
          <p style={{ fontSize: 13.5, color: "var(--ds-ink-500)", margin: "0 0 12px" }}>
            Once you apply or we apply for you, you'll be able to track everything from here.
          </p>
          <Link
            to="/dashboard"
            style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ds-accent-primary)" }}
          >
            See matching jobs →
          </Link>
        </div>
      ) : waitingItems.length === 0 && finishedItems.length === 0 ? (
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
