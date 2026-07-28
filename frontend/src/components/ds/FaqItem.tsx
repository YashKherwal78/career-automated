import * as React from "react";

export interface DsFaqItemProps {
  question: React.ReactNode;
  answer: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
}

export function DsFaqItem({ question, answer, isOpen, onToggle }: DsFaqItemProps) {
  return (
    <div className="bg-[var(--ds-surface-card)] border border-[var(--ds-border-default)] rounded-[var(--ds-radius-lg)] overflow-hidden">
      <div
        onClick={onToggle}
        className="px-[22px] py-[18px] flex items-center justify-between cursor-pointer"
      >
        <span className="font-[var(--ds-font-display)] font-semibold" style={{ fontSize: 15 }}>
          {question}
        </span>
        <span
          className="flex-shrink-0 ml-3 text-[var(--ds-accent-primary)] font-light"
          style={{ fontSize: 20 }}
        >
          {isOpen ? "−" : "+"}
        </span>
      </div>
      {isOpen && (
        <div className="px-[22px] pb-5 text-[length:var(--ds-text-base)] text-[var(--ds-ink-500)] leading-[var(--ds-leading-relaxed)]">
          {answer}
        </div>
      )}
    </div>
  );
}
