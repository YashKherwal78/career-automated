import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useAuth } from "../../lib/auth";
import { DsModal } from "../../components/ds/Modal";
import { DsDropzone } from "../../components/ds/Dropzone";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: 40,
        height: 22,
        borderRadius: 11,
        background: on ? "var(--ds-accent-primary)" : "var(--ds-border-medium)",
        position: "relative",
        border: "none",
        cursor: "pointer",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 2,
          left: on ? 20 : 2,
          width: 18,
          height: 18,
          borderRadius: "50%",
          background: "#fff",
          transition: "left 160ms linear",
        }}
      />
    </button>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="flex items-center"
      style={{ padding: "16px 20px", borderBottom: "1px solid var(--ds-border-default)" }}
    >
      {children}
    </div>
  );
}

function RowLabel({ label, sub }: { label: string; sub?: string }) {
  return (
    <div style={{ flex: 1, minWidth: 0, paddingRight: 16 }}>
      <div style={{ fontSize: 14.5, fontWeight: 600, color: "var(--ds-text-primary)" }}>
        {label}
      </div>
      {sub && <div style={{ fontSize: 12.5, color: "var(--ds-ink-450)", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function CycleValue({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  const cycle = () => {
    const idx = options.indexOf(value);
    onChange(options[(idx + 1) % options.length]);
  };
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={cycle}
      onKeyDown={(e) => e.key === "Enter" && cycle()}
      className="flex items-center gap-2 flex-shrink-0 cursor-pointer"
    >
      <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>{value}</span>
      <span style={{ fontSize: 12, color: "var(--ds-ink-300)" }}>›</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 36 }}>
      <div
        className="uppercase font-bold"
        style={{
          fontSize: 12.5,
          letterSpacing: "var(--ds-tracking-wide)",
          color: "var(--ds-ink-400)",
          marginBottom: 12,
        }}
      >
        {title}
      </div>
      <div
        style={{
          background: "var(--ds-surface-card)",
          border: "1px solid var(--ds-border-default)",
          borderRadius: "var(--ds-radius-lg)",
          overflow: "hidden",
        }}
      >
        {children}
      </div>
    </div>
  );
}

function SettingsPage() {
  const { profile, logout } = useAuth();

  const [preferredRole, setPreferredRole] = useState("Software Engineer");
  const [experienceLevel, setExperienceLevel] = useState("Mid-level");
  const [location, setLocation] = useState("Remote");
  const [salary, setSalary] = useState("₹15L+");
  const [workAuth, setWorkAuth] = useState("Indian citizen");

  const [resumeStyle, setResumeStyle] = useState("Modern");
  const [tailoringAggro, setTailoringAggro] = useState("Balanced");
  const [writingTone, setWritingTone] = useState("Professional");
  const [autoFill, setAutoFill] = useState(false);

  const [emailNotif, setEmailNotif] = useState(true);
  const [weeklySummary, setWeeklySummary] = useState(true);
  const [interviewReminders, setInterviewReminders] = useState(true);

  const [showReplaceModal, setShowReplaceModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTyped, setDeleteTyped] = useState("");

  return (
    <div style={{ padding: "40px clamp(24px,4vw,56px)", maxWidth: 720 }}>
      <h1
        className="font-[var(--ds-font-display)] font-semibold"
        style={{ fontSize: 28, margin: "0 0 8px" }}
      >
        Settings
      </h1>
      <p style={{ fontSize: 14, color: "var(--ds-ink-500)", margin: "0 0 32px" }}>
        Manage your account, preferences, and how CareerAutomated works for you.
      </p>

      <Section title="Account">
        <Row>
          <RowLabel label="Name" />
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
              {profile?.full_name || "—"}
            </span>
            <span
              className="font-bold"
              style={{ fontSize: 11, color: "var(--ds-ink-300)", letterSpacing: 0.5 }}
            >
              LOCKED
            </span>
          </div>
        </Row>
        <Row>
          <RowLabel label="Email" />
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
              {profile?.email || "—"}
            </span>
            <span
              className="font-bold"
              style={{ fontSize: 11, color: "var(--ds-ink-300)", letterSpacing: 0.5 }}
            >
              LOCKED
            </span>
          </div>
        </Row>
        <Row>
          <RowLabel label="Password" sub="Change your account password" />
          <button
            type="button"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--ds-accent-primary)",
              background: "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            Change password
          </button>
        </Row>
      </Section>

      <Section title="Career">
        <Row>
          <RowLabel label="Preferred role" />
          <CycleValue
            value={preferredRole}
            options={["Software Engineer", "Product Manager", "Designer", "Data Scientist"]}
            onChange={setPreferredRole}
          />
        </Row>
        <Row>
          <RowLabel label="Experience level" />
          <CycleValue
            value={experienceLevel}
            options={["Entry-level", "Mid-level", "Senior", "Lead"]}
            onChange={setExperienceLevel}
          />
        </Row>
        <Row>
          <RowLabel label="Location" />
          <CycleValue
            value={location}
            options={["Remote", "Bangalore", "Hyderabad", "Mumbai"]}
            onChange={setLocation}
          />
        </Row>
        <Row>
          <RowLabel label="Salary expectation" />
          <CycleValue
            value={salary}
            options={["₹5L+", "₹10L+", "₹15L+", "₹25L+"]}
            onChange={setSalary}
          />
        </Row>
        <Row>
          <RowLabel label="Work authorization" />
          <CycleValue
            value={workAuth}
            options={["Indian citizen", "Need sponsorship", "No preference"]}
            onChange={setWorkAuth}
          />
        </Row>
      </Section>

      <Section title="Resume">
        <Row>
          <RowLabel label="View resume" sub="Your most recently uploaded resume" />
          <Link to="/dashboard/resume" style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>
            View ›
          </Link>
        </Row>
        <Row>
          <RowLabel label="Replace resume" />
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
            Replace
          </button>
        </Row>
        <Row>
          <RowLabel label="Version history" />
          <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>—</span>
        </Row>
      </Section>

      <Section title="AI Preferences">
        <Row>
          <RowLabel label="Default resume style" />
          <CycleValue
            value={resumeStyle}
            options={["Modern", "Classic", "Minimal"]}
            onChange={setResumeStyle}
          />
        </Row>
        <Row>
          <RowLabel label="Tailoring aggressiveness" />
          <CycleValue
            value={tailoringAggro}
            options={["Conservative", "Balanced", "Bold"]}
            onChange={setTailoringAggro}
          />
        </Row>
        <Row>
          <RowLabel label="AI writing tone" />
          <CycleValue
            value={writingTone}
            options={["Professional", "Confident", "Warm"]}
            onChange={setWritingTone}
          />
        </Row>
        <Row>
          <RowLabel label="Auto-fill applications" sub="Fill forms automatically when matched" />
          <Toggle on={autoFill} onClick={() => setAutoFill((v) => !v)} />
        </Row>
      </Section>

      <Section title="Notifications">
        <Row>
          <RowLabel label="Email notifications" />
          <Toggle on={emailNotif} onClick={() => setEmailNotif((v) => !v)} />
        </Row>
        <Row>
          <RowLabel label="Weekly summary" />
          <Toggle on={weeklySummary} onClick={() => setWeeklySummary((v) => !v)} />
        </Row>
        <Row>
          <RowLabel label="Interview reminders" />
          <Toggle on={interviewReminders} onClick={() => setInterviewReminders((v) => !v)} />
        </Row>
      </Section>

      <Section title="Appearance">
        <Row>
          <RowLabel label="Dark mode" sub="We're still polishing it" />
          <span
            className="font-bold flex-shrink-0"
            style={{
              fontSize: 11.5,
              color: "var(--ds-ink-400)",
              background: "var(--ds-surface-tint)",
              padding: "5px 11px",
              borderRadius: "var(--ds-radius-pill)",
            }}
          >
            Coming soon
          </span>
        </Row>
      </Section>

      <Section title="Billing">
        <Row>
          <RowLabel label="Current plan" />
          <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>Free tier</span>
        </Row>
        <Row>
          <RowLabel label="Upgrade" />
          <Link
            to="/pricing"
            style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-accent-primary)" }}
          >
            View plans
          </Link>
        </Row>
        <Row>
          <RowLabel label="Usage this month" />
          <span style={{ fontSize: 13.5, color: "var(--ds-ink-450)" }}>—</span>
        </Row>
      </Section>

      <Section title="Danger Zone">
        <Row>
          <RowLabel
            label="Delete account"
            sub="Permanently remove your data. This cannot be undone."
          />
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="font-semibold flex-shrink-0"
            style={{
              fontSize: 13,
              color: "#B4392C",
              background: "rgba(180,57,44,0.08)",
              border: "none",
              padding: "8px 14px",
              borderRadius: "var(--ds-radius-md)",
              cursor: "pointer",
            }}
          >
            Delete account
          </button>
        </Row>
      </Section>

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
            <DsDropzone onFile={() => setShowReplaceModal(false)} />
          </div>
        </DsModal>
      )}

      {showDeleteModal && (
        <DsModal onClose={() => setShowDeleteModal(false)} maxWidth={400}>
          <div style={{ padding: 28 }}>
            <div
              className="flex items-center justify-center"
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: "rgba(180,57,44,0.1)",
                marginBottom: 16,
                fontSize: 18,
              }}
            >
              ⚠
            </div>
            <h2
              className="font-[var(--ds-font-display)] font-semibold"
              style={{ fontSize: 18, margin: "0 0 8px" }}
            >
              Delete your account?
            </h2>
            <p
              style={{
                fontSize: 13.5,
                color: "var(--ds-ink-500)",
                lineHeight: 1.6,
                margin: "0 0 18px",
              }}
            >
              This permanently deletes your profile, resumes, and application history. This cannot
              be undone.
            </p>
            <label
              style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "var(--ds-ink-600)",
                marginBottom: 6,
              }}
            >
              Type DELETE to confirm
            </label>
            <input
              type="text"
              value={deleteTyped}
              onChange={(e) => setDeleteTyped(e.target.value)}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                borderRadius: "var(--ds-radius-md)",
                border: "1px solid var(--ds-border-medium)",
                fontSize: 13.5,
              }}
            />
            <div className="flex gap-2.5" style={{ marginTop: 16 }}>
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 font-semibold"
                style={{
                  padding: 12,
                  borderRadius: "var(--ds-radius-md)",
                  border: "1px solid var(--ds-border-medium)",
                  background: "transparent",
                  color: "var(--ds-ink-700)",
                  fontSize: 13.5,
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteTyped !== "DELETE"}
                onClick={() => logout()}
                className="flex-1 font-semibold"
                style={{
                  padding: 12,
                  borderRadius: "var(--ds-radius-md)",
                  border: "none",
                  background: deleteTyped === "DELETE" ? "#B4392C" : "var(--ds-cream-300)",
                  color: deleteTyped === "DELETE" ? "#fff" : "var(--ds-ink-400)",
                  fontSize: 13.5,
                  cursor: deleteTyped === "DELETE" ? "pointer" : "default",
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </DsModal>
      )}
    </div>
  );
}
