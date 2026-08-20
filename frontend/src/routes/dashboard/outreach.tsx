import { createFileRoute } from "@tanstack/react-router";
import { useState, type CSSProperties, type ChangeEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ServiceRegistry, type ReferralDraft, type HrPitchDraft, type ManualLeadInput } from "../../lib/services";
import { DsButton } from "../../components/ds/Button";
import { DsModal, DsModalCloseButton } from "../../components/ds/Modal";
import { UserPlus } from "lucide-react";

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
type Draft = ReferralDraft | HrPitchDraft;

const SOURCES = [
  {
    key: "referral" as const,
    label: "Referral requests",
    description:
      "For every real application, we look for a hiring manager, recruiter, or someone else at the company and draft a short referral-request email.",
  },
  {
    key: "hr_pitch" as const,
    label: "Direct pitch & referral ask",
    description:
      "A second, separate system: a direct fit-pitch email to the recruiter or hiring manager for the specific job, or a low-effort referral ask to a peer if no HR contact is found.",
  },
];

function statusBadgeColor(status: Draft["status"]) {
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

function mailTypeLabel(mailType: HrPitchDraft["mail_type"]) {
  return mailType === "hr_pitch" ? "Direct pitch" : "Referral ask";
}

// ---------------------------------------------------------------------
// Add lead — manual counterpart to the Jobs page's "Upload job" screenshot
// flow: for a job/contact the automated discovery pipeline wouldn't catch
// (a LinkedIn job with a broken Apply button, a recruiter found some other
// way), fill in the facts by hand and get a drafted email back immediately.
// Same shape as UploadJobModal in jobs.tsx -- own local state, opened from
// a promo-style button, closes itself on success.
// ---------------------------------------------------------------------
const EMPTY_LEAD: ManualLeadInput = {
  company_name: "",
  job_title: "",
  contact_email: "",
  contact_name: "",
  contact_role: "",
  contact_type: "Recruiter",
  apply_url: "",
};

function fieldStyle(): CSSProperties {
  return {
    width: "100%",
    fontSize: 13.5,
    padding: "9px 11px",
    borderRadius: "var(--ds-radius-md)",
    border: "1px solid var(--ds-border-medium)",
    background: "var(--ds-surface-card)",
    color: "var(--ds-ink-900)",
  };
}

function AddLeadModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<ManualLeadInput>(EMPTY_LEAD);
  const [state, setState] = useState<"idle" | "working" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof ManualLeadInput) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const canSubmit = form.company_name.trim() && form.job_title.trim() && form.contact_email.trim().includes("@");

  const handleSubmit = async () => {
    if (!canSubmit || state === "working") return;
    setState("working");
    setError(null);
    try {
      await ServiceRegistry.getHrPitchService().addManualLead(form);
      onCreated();
      onClose();
    } catch (e) {
      setState("error");
      setError(e instanceof Error ? e.message : "Couldn't draft this one — try again.");
    }
  };

  return (
    <DsModal onClose={onClose} maxWidth={520}>
      <div className="p-5 md:p-6 space-y-4" style={{ position: "relative" }}>
        <DsModalCloseButton onClose={onClose} />
        <div className="flex items-start gap-3 md:gap-4" style={{ paddingRight: 28 }}>
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{ width: 40, height: 40, borderRadius: "var(--ds-radius-lg)", background: "var(--ds-brand-orange-tint-08)", color: "var(--ds-brand-orange-text)" }}
          >
            <UserPlus size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <div
              className="uppercase font-bold"
              style={{ fontSize: 11, letterSpacing: 0.6, color: "var(--ds-brand-orange-text)", marginBottom: 3 }}
            >
              Add lead
            </div>
            <h2 className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: 16, marginBottom: 3 }}>
              Found a role and a contact yourself?
            </h2>
            <p style={{ margin: 0, fontSize: 13, color: "var(--ds-ink-500)" }}>
              Fill in the company, role, and a real contact email — we'll draft the pitch right away and drop it
              into Pending review, same as anything the automated pipeline finds.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>
            Company *
            <input style={fieldStyle()} value={form.company_name} onChange={set("company_name")} placeholder="Questhiring" />
          </label>
          <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>
            Role *
            <input style={fieldStyle()} value={form.job_title} onChange={set("job_title")} placeholder="AI Engineer" />
          </label>
        </div>

        <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)", display: "block" }}>
          Contact email *
          <input style={fieldStyle()} value={form.contact_email} onChange={set("contact_email")} placeholder="recruiter@company.com" />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>
            Contact name
            <input style={fieldStyle()} value={form.contact_name} onChange={set("contact_name")} placeholder="Optional" />
          </label>
          <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>
            Their role
            <input style={fieldStyle()} value={form.contact_role} onChange={set("contact_role")} placeholder="e.g. Talent Acquisition" />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>
            Contact type
            <select style={fieldStyle()} value={form.contact_type} onChange={set("contact_type")}>
              <option value="Recruiter">Recruiter</option>
              <option value="Hiring Manager">Hiring Manager</option>
              <option value="Technical IC">Technical IC / peer</option>
            </select>
          </label>
          <label style={{ fontSize: 12.5, color: "var(--ds-ink-600)" }}>
            Job posting link
            <input style={fieldStyle()} value={form.apply_url} onChange={set("apply_url")} placeholder="Optional" />
          </label>
        </div>

        {error && (
          <div style={{ fontSize: 12.5, color: "#B4392C", background: "rgba(180,57,44,0.08)", borderRadius: "var(--ds-radius-md)", padding: "8px 10px" }}>
            {error}
          </div>
        )}

        <DsButton onClick={handleSubmit} disabled={!canSubmit || state === "working"} style={{ width: "100%" }}>
          {state === "working" ? "Drafting…" : "Draft this email"}
        </DsButton>
      </div>
    </DsModal>
  );
}

function OutreachPage() {
  const queryClient = useQueryClient();
  const [activeSource, setActiveSource] = useState<"referral" | "hr_pitch">("referral");
  const [activeTab, setActiveTab] = useState<TabKey>("PENDING_REVIEW");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [actionState, setActionState] = useState<Record<string, "working" | "error">>({});

  const { data: referralDrafts = [] } = useQuery({
    queryKey: ["referral-drafts"],
    queryFn: () => ServiceRegistry.getReferralService().list(),
    refetchInterval: 30000,
  });
  const { data: hrPitchDrafts = [] } = useQuery({
    queryKey: ["hr-pitch-drafts"],
    queryFn: () => ServiceRegistry.getHrPitchService().list(),
    refetchInterval: 30000,
  });
  const drafts: Draft[] = activeSource === "referral" ? referralDrafts : hrPitchDrafts;
  const isLoading = false;

  const { data: autoSend } = useQuery({
    queryKey: ["referral-auto-send-policy"],
    queryFn: () => ServiceRegistry.getReferralService().getAutoSendPolicy(),
  });

  const [policyUpdating, setPolicyUpdating] = useState(false);
  const [showAddLeadModal, setShowAddLeadModal] = useState(false);

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

  const activeService = () =>
    activeSource === "referral" ? ServiceRegistry.getReferralService() : ServiceRegistry.getHrPitchService();
  const activeDraftsKey = activeSource === "referral" ? "referral-drafts" : "hr-pitch-drafts";

  const handleApprove = async (id: string) => {
    setActionState((s) => ({ ...s, [id]: "working" }));
    try {
      await activeService().approve(id);
      queryClient.invalidateQueries({ queryKey: [activeDraftsKey] });
    } catch (e) {
      console.error("Failed to approve draft:", e);
      setActionState((s) => ({ ...s, [id]: "error" }));
    }
  };

  const handleReject = async (id: string) => {
    setActionState((s) => ({ ...s, [id]: "working" }));
    try {
      await activeService().reject(id);
      queryClient.invalidateQueries({ queryKey: [activeDraftsKey] });
    } catch (e) {
      console.error("Failed to reject draft:", e);
      setActionState((s) => ({ ...s, [id]: "error" }));
    }
  };

  const filtered = drafts.filter((d) => d.status === activeTab);
  const counts = TABS.reduce<Record<string, number>>((acc, t) => {
    acc[t.key] = drafts.filter((d) => d.status === t.key).length;
    return acc;
  }, {});
  const activeSourceMeta = SOURCES.find((s) => s.key === activeSource)!;

  return (
    <div style={{ padding: "clamp(24px,4vw,48px)", maxWidth: 900 }}>
      <div className="uppercase font-bold" style={{ fontSize: 12.5, letterSpacing: "var(--ds-tracking-wide)", color: "var(--ds-brand-orange-text)", marginBottom: 8 }}>
        Outreach
      </div>
      <h1 className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: "clamp(24px,3vw,30px)", margin: "0 0 8px" }}>
        {activeSourceMeta.label}
      </h1>
      <p style={{ fontSize: 13.5, color: "var(--ds-ink-500)", lineHeight: 1.6, margin: "0 0 20px", maxWidth: 600 }}>
        {activeSourceMeta.description} Real contacts, found automatically, never sent without your say-so unless
        you turn that on below.
      </p>

      <div className="flex gap-2" style={{ marginBottom: 20 }}>
        {SOURCES.map((s) => (
          <button
            key={s.key}
            type="button"
            onClick={() => {
              setActiveSource(s.key);
              setExpandedId(null);
            }}
            style={{
              padding: "9px 16px",
              borderRadius: "var(--ds-radius-md)",
              border: activeSource === s.key ? "1px solid var(--ds-accent-primary)" : "1px solid var(--ds-border-medium)",
              background: activeSource === s.key ? "rgba(226,116,72,0.1)" : "transparent",
              color: activeSource === s.key ? "var(--ds-accent-primary)" : "var(--ds-ink-600)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {s.label}
          </button>
        ))}
      </div>

      {activeSource === "hr_pitch" && (
        <button
          type="button"
          onClick={() => setShowAddLeadModal(true)}
          className="w-full flex items-center gap-3 text-left glass-card rounded-2xl border border-white/50 bg-white/40 shadow-sm hover:bg-white/60 active:scale-[0.995] transition-all"
          style={{ padding: "13px 14px", marginBottom: 20 }}
        >
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{ width: 38, height: 38, borderRadius: "var(--ds-radius-lg)", background: "var(--ds-brand-orange-tint-08)", color: "var(--ds-brand-orange-text)" }}
          >
            <UserPlus size={17} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold" style={{ fontSize: 13.5, color: "var(--ds-ink-900)" }}>
              Found a role and a contact yourself?
            </div>
            <div className="truncate" style={{ fontSize: 12, color: "var(--ds-ink-500)" }}>
              Add the lead by hand — we'll draft the pitch right away, same as an automated find.
            </div>
          </div>
          <span className="flex-shrink-0 font-semibold" style={{ fontSize: 12.5, color: "var(--ds-accent-primary)" }}>
            Add lead →
          </span>
        </button>
      )}

      {showAddLeadModal && (
        <AddLeadModal
          onClose={() => setShowAddLeadModal(false)}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ["hr-pitch-drafts"] })}
        />
      )}

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
              ? "On — new drafts from both outreach systems send automatically as soon as a contact is found. Turn off anytime to go back to reviewing each one."
              : "Off — every draft from both outreach systems waits here for you to approve before it sends. Flip this on once you trust the quality."}
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
            : `No ${TABS.find((t) => t.key === activeTab)?.label.toLowerCase()} drafts yet.`}
        </div>
      )}

      <div className="flex flex-col" style={{ gap: 12 }}>
        {filtered.map((r) => {
          const isExpanded = expandedId === r.id;
          const badge = statusBadgeColor(r.status);
          const mailType = "mail_type" in r ? r.mail_type : null;
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
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {mailType && (
                    <span
                      style={{
                        fontSize: 10.5,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: 0.4,
                        padding: "3px 8px",
                        borderRadius: 999,
                        background: "rgba(139,123,192,0.14)",
                        color: "#6C5CA8",
                      }}
                    >
                      {mailTypeLabel(mailType)}
                    </span>
                  )}
                  <span
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
