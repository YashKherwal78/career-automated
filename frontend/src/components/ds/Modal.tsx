import * as React from "react";

export interface DsModalProps {
  onClose: () => void;
  children: React.ReactNode;
  maxWidth?: number;
}

/** Shared modal shell: dimmed overlay, centered card, click-outside-to-close, no header/close-button baked in (callers place their own ✕). */
export function DsModal({ onClose, children, maxWidth = 460 }: DsModalProps) {
  return (
    <div
      onClick={onClose}
      className="fixed inset-0 flex items-center justify-center overflow-y-auto"
      style={{ background: "rgba(30,20,12,0.4)", zIndex: 100, padding: 24 }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth,
          background: "var(--ds-surface-card)",
          borderRadius: "var(--ds-radius-2xl)",
          boxShadow: "var(--ds-shadow-modal)",
          maxHeight: "88vh",
          overflowY: "auto",
        }}
      >
        {children}
      </div>
    </div>
  );
}

export function DsModalCloseButton({ onClose }: { onClose: () => void }) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClose}
      onKeyDown={(e) => e.key === "Enter" && onClose()}
      className="absolute flex items-center justify-center cursor-pointer hover:bg-[var(--ds-surface-tint)]"
      style={{
        top: 20,
        right: 20,
        width: 28,
        height: 28,
        borderRadius: 8,
        color: "var(--ds-ink-400)",
        fontSize: 16,
      }}
    >
      ✕
    </div>
  );
}
