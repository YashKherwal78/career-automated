import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ServiceRegistry, type ReferralDraft } from "../../lib/services";
import { DsButton } from "../../components/ds/Button";

export const Route = createFileRoute("/dashboard/outreach")({
  head: () => ({ meta: [{ title: "Outreach — CareerAutomated" }] }),
  component: OutreachPage,
});

const TABS = [
  { key: "PENDING_REVIEW", label: "Pending review" },
  { key: "SENT", label: "Sent" },
  { key: "REJECTED", label: "Rejected" },
  { key: "FAILED", label: "Failed" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function statusBadgeColor(status: ReferralDraft["status"]) {
  switch (status) {
    case "SENT":
      return { bg: "rgba(60,150,90,0.12)", fg: "#2E7D4F" };
    case "REJECTED":
      return { bg: "rgba(150,150,150,0.14)", fg: "var(--ds-ink-500)" };
    case "FAILED":
      return { bg: "rgba(180,57,44,0.1)", fg: "#B4392C" };
    default:
      return { bg: "rgba(226,116,72,0.12)", fg: "var(--ds-accent-primary)" };
  }
}

function OutreachPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("PENDING_REVIEW");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionState, setActionState] = useState<Record<string, "working" | "error">>({});

  const { data: drafts = [], isLoading } = useQuery({
    queryKey: ["referral-drafts"],
    queryFn: () => ServiceRegistry.getReferralService().list(),
    refetchInterval: 30000,
  });

  const { data: autoSend } = useQuery({
    queryKey: ["referral-auto-send-policy"],
    queryFn: () => ServiceRegistry.getReferralService().getAutoSendPolicy(),
  });

  const [policyUpdating, setPolicyUpdating] = useState(false);

  const handleToggleAutoSend = async () => {
    setPolicyUpdating(true);
    try {
      await ServiceRegistry.getReferralService().setAutoSendPolicy(!autoSend);
      queryClient.invalidateQueries({ queryKey: ["referral-auto-send-policy"] });
    } catch (e) {
      console.error("Failed to update referral auto-send policy:", e);
    } finally {
      setPolicyUpdating(false);
    }
  };

  const handleApprove = async (id: string) => {
    setActionState((s) => ({ ...s, [id]: "working" }));
    try {
      await ServiceRegistry.getReferralService().approve(id);
      queryClient.invalidateQueries({ queryKey: ["referral-drafts"] });
    } catch (e) {
      console.error("Failed to approve referral:", e);
      setActionState((s) => ({ ...s, [id]: "error" }));
    }
  };

  const handleReject = async (id: string) => {
    setActionState((s) => ({ ...s, [id]: "working" }));
    try {
      await ServiceRegistry.getReferralService().reject(id);
      queryClient.invalidateQueries({ queryKey: ["referral-drafts"] });
    } catch (e) {
      console.error("Failed to reject referral:", e);
      setActionState((s) => ({ ...s, [id]: "error" }));
    }
  };

  const filtered = drafts.filter((d) => d.status === activeTab);
  const counts = TABS.reduce<Record<string, number>>((acc, t) => {
    acc[t.key] = drafts.filter((d) => d.status === t.key).length;
    return acc;
  }, {});

  return (
    <div style={{ padding: "clamp(24px,4vw,48px)", maxWidth: 900 }}>
      <div className="uppercase font-bold" style={{ fontSize: 12.5, letterSpacing: "var(--ds-tracking-wide)", color: "var(--ds-brand-orange-text)", marginBottom: 8 }}>
        Outreach
      </div>
      <h1 className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: "clamp(24px,3vw,30px)", margin: "0 0 8px" }}>
        Referral emails
      </h1>
      <p style={{ fontSize: 13.5, color: "var(--ds-ink-500)", lineHeight: 1.6, margin: "0 0 24px", maxWidth: 560 }}>
        For every real application, we look for a hiring manager, recruiter, or someone else at the
        company and draft a short referral-request email — real contacts, found automatically, never
        sent without your say-so unless you turn that on below.
      </p>

      <div
        className="flex items-center justify-between flex-wrap"
        style={{
          background: "var(--ds-surface-tint)",
          border: "1px solid rgba(255,255,255,0.6)",
          borderRadius: "var(--ds-radius-xl)",
          padding: "18px 22px",
          marginBottom: 24,
          gap: 14,
        }}
      >
        <div style={{ minWidth: 240 }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Auto-send approved drafts</div>
          <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)", marginTop: 2, maxWidth: 420 }}>
            {autoSend
              ? "On — new drafts send automatically as soon as a contact is found. Turn off anytime to go back to reviewing each one."
              : "Off — every draft waits here for you to approve before it sends. Flip this on once you trust the quality."}
          </div>
        </div>
        <button
          type="button"
          onClick={handleToggleAutoSend}
          disabled={policyUpdating || autoSend === undefined}
          style={{
            width: 44,
            height: 24,
            borderRadius: 12,
            background: autoSend ? "var(--ds-accent-primary)" : "var(--ds-border-medium)",
            position: "relative",
            transition: "background 160ms linear",
            border: "none",
            cursor: policyUpdating ? "default" : "pointer",
            opacity: policyUpdating ? 0.6 : 1,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 2,
              left: autoSend ? 22 : 2,
              width: 20,
              height: 20,
              borderRadius: "50%",
              background: "#fff",
              transition: "left 160ms linear",
            }}
          />
        </button>
      </div>

      <div className="flex items-center gap-1.5" style={{ marginBottom: 20, borderBottom: "1px solid var(--ds-border-default)" }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key)}
            style={{
              padding: "10px 14px",
              background: "none",
              border: "none",
              borderBottom: activeTab === t.key ? "2px solid var(--ds-accent-primary)" : "2px solid transparent",
              color: activeTab === t.key ? "var(--ds-ink-900)" : "var(--ds-ink-450)",
              fontWeight: activeTab === t.key ? 700 : 500,
              fontSize: 13.5,
              cursor: "pointer",
              marginBottom: -1,
            }}
          >
            {t.label} {counts[t.key] > 0 && `(${counts[t.key]})`}
          </button>
        ))}
      </div>

      {isLoading && (
        <div style={{ fontSize: 13, color: "var(--ds-ink-450)" }}>Loading…</div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div
          style={{
            background: "rgba(255,255,255,0.5)",
            border: "1px dashed var(--ds-border-medium)",
            borderRadius: "var(--ds-radius-xl)",
            padding: 32,
            textAlign: "center",
            color: "var(--ds-ink-450)",
            fontSize: 13.5,
          }}
        >
          {activeTab === "PENDING_REVIEW"
            ? "Nothing waiting on you right now — drafts show up here as we find contacts for jobs you've applied to."
            : `No ${TABS.find((t) => t.key === activeTab)?.label.toLowerCase()} referrals yet.`}
        </div>
      )}

      <div className="flex flex-col" style={{ gap: 12 }}>
        {filtered.map((r) => {
          const isExpanded = expandedId === r.id;
          const badge = statusBadgeColor(r.status);
          return (
            <div
              key={r.id}
              style={{
                background: "rgba(255,255,255,0.7)",
                border: "1px solid rgba(255,255,255,0.6)",
                borderRadius: "var(--ds-radius-lg)",
                padding: "16px 18px",
              }}
            >
              <div className="flex items-start justify-between gap-2">
                <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.4 }}>
                  {r.contact_name}
                  <span style={{ color: "var(--ds-ink-450)", fontWeight: 500 }}>
                    {" "}
                    · {r.company_name} — {r.job_title}
                  </span>
                </div>
                <span
                  className="flex-shrink-0"
                  style={{
                    fontSize: 10.5,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: 0.4,
                    padding: "3px 8px",
                    borderRadius: 999,
                    background: badge.bg,
                    color: badge.fg,
                  }}
                >
                  {r.status.replace("_", " ")}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--ds-ink-450)", marginTop: 2 }}>
                {r.contact_email}
                {r.sent_at && ` · sent ${new Date(r.sent_at).toLocaleString()}`}
                {r.status === "FAILED" && r.error && ` · ${r.error}`}
              </div>

              <button
                type="button"
                onClick={() => setExpandedId(isExpanded ? null : r.id)}
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
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: isExpanded ? 8 : 0 }}>{r.subject}</div>
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
                <span style={{ fontSize: 11.5, color: "var(--ds-ink-400)", fontWeight: 600, display: "inline-block", marginTop: 6 }}>
                  {isExpanded ? "Show less ↑" : "Show full email ↓"}
                </span>
              </button>

              {r.status === "PENDING_REVIEW" && (
                <div className="flex items-center gap-2.5" style={{ marginTop: 14 }}>
                  <DsButton variant="primary" size="md" disabled={actionState[r.id] === "working"} onClick={() => handleApprove(r.id)}>
                    {actionState[r.id] === "working" ? "Sending…" : "Approve & send"}
                  </DsButton>
                  <DsButton variant="outline" size="md" disabled={actionState[r.id] === "working"} onClick={() => handleReject(r.id)}>
                    Reject
                  </DsButton>
                  {actionState[r.id] === "error" && (
                    <span style={{ fontSize: 12, color: "#B4392C" }}>Failed — try again</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
