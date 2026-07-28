import { Link } from "@tanstack/react-router";
import { DsModal, DsModalCloseButton } from "../ds/Modal";

export function UpgradeModal({ onClose }: { onClose: () => void }) {
  return (
    <DsModal onClose={onClose} maxWidth={380}>
      <div style={{ padding: 28, position: "relative", textAlign: "center" }}>
        <DsModalCloseButton onClose={onClose} />
        <div
          className="mx-auto flex items-center justify-center"
          style={{
            width: 48,
            height: 48,
            borderRadius: "var(--ds-radius-lg)",
            background: "var(--ds-brand-orange-tint-10)",
            marginBottom: 18,
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
          style={{ fontSize: 18, marginBottom: 8 }}
        >
          Auto-apply is a Pro feature
        </div>
        <p
          style={{
            fontSize: 13.5,
            color: "var(--ds-ink-500)",
            lineHeight: 1.6,
            margin: "0 0 18px",
          }}
        >
          Upgrade to let CareerAutomated tailor and submit applications for you automatically, so
          the right roles never slip by.
        </p>
        <Link
          to="/checkout"
          className="block w-full box-border font-bold text-center"
          style={{
            padding: 13,
            borderRadius: "var(--ds-radius-md)",
            background: "var(--ds-accent-primary)",
            color: "var(--ds-text-on-brand)",
            fontSize: 14,
            boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
            marginBottom: 10,
          }}
        >
          Upgrade to Pro
        </Link>
        <button
          type="button"
          onClick={onClose}
          style={{
            fontSize: 13,
            color: "var(--ds-ink-450)",
            cursor: "pointer",
            background: "none",
            border: "none",
          }}
        >
          Maybe later
        </button>
      </div>
    </DsModal>
  );
}
