import { useState } from "react";
import { Link } from "@tanstack/react-router";
import type { Job } from "../../lib/services";
import { DsModal, DsModalCloseButton } from "../ds/Modal";
import { CompanyLogo } from "./CompanyLogo";

interface AccordionSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function AccordionSection({ title, children, defaultOpen = false }: AccordionSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => e.key === "Enter" && setOpen((o) => !o)}
        className="flex items-center justify-between cursor-pointer"
        style={{ padding: "14px 28px" }}
      >
        <div style={{ fontSize: 14.5, fontWeight: 600 }}>{title}</div>
        <div
          style={{
            transform: open ? "rotate(90deg)" : "none",
            transition: "transform 160ms linear",
            color: "var(--ds-ink-400)",
          }}
        >
          ›
        </div>
      </div>
      {open && (
        <div
          style={{
            padding: "0 28px 20px",
            borderTop: "1px solid var(--ds-border-default)",
            paddingTop: 14,
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

function formatSalary(job: Job): string | null {
  if (!job.salary_min && !job.salary_max) return null;
  const fmt = (n: number) => `₹${(n / 100000).toFixed(1)}L`;
  if (job.salary_min && job.salary_max)
    return `${fmt(job.salary_min)} – ${fmt(job.salary_max)} / year`;
  return fmt(job.salary_min || job.salary_max || 0) + " / year";
}

type ApplyStatus = {
  state: "applying" | "applied" | "review_required" | "failed";
  message?: string;
};

export function JobDetailModal({
  job,
  queued,
  applyStatus,
  onToggleQueue,
  onClose,
  showMatch = true,
}: {
  job: Job;
  queued: boolean;
  applyStatus?: ApplyStatus;
  onToggleQueue: () => void;
  onClose: () => void;
  showMatch?: boolean;
}) {
  const salary = formatSalary(job);
  const breakdown = job.score_breakdown || [];
  const structured = breakdown.length > 0 && typeof breakdown[0] === "object";
  const matched = structured
    ? (breakdown as { keyword: string; matched: boolean }[])
        .filter((b) => b.matched)
        .map((b) => b.keyword)
    : (breakdown as string[]);
  const missing = structured
    ? (breakdown as { keyword: string; matched: boolean }[])
        .filter((b) => !b.matched)
        .map((b) => b.keyword)
    : [];

  return (
    <DsModal onClose={onClose} maxWidth={560}>
      <div style={{ padding: "26px 28px 22px", position: "relative" }}>
        <DsModalCloseButton onClose={onClose} />
        <div
          className="uppercase font-bold"
          style={{
            fontSize: 11,
            letterSpacing: 0.6,
            color: "var(--ds-brand-orange-text)",
            marginBottom: 10,
          }}
        >
          Mission
        </div>
        <div className="flex items-center gap-3.5" style={{ marginBottom: 20 }}>
          <CompanyLogo name={job.canonical_name} domain={job.company_domain} size={48} radius={12} fontSize={18} />
          <div className="min-w-0">
            <div
              className="font-[var(--ds-font-display)] font-bold"
              style={{ fontSize: 21, lineHeight: 1.2 }}
            >
              {job.canonical_name}
            </div>
            <div style={{ fontSize: 14, color: "var(--ds-ink-500)" }}>
              {job.title} · {job.location}
            </div>
          </div>
        </div>
        <div className="flex gap-6 flex-wrap">
          <div>
            <div
              className="uppercase font-bold"
              style={{ fontSize: 11, color: "var(--ds-ink-400)", marginBottom: 4 }}
            >
              Status
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ds-ink-800)" }}>Ready</div>
          </div>
          {showMatch && (
            <div>
              <div
                className="uppercase font-bold"
                style={{ fontSize: 11, color: "var(--ds-ink-400)", marginBottom: 4 }}
              >
                Match
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ds-ink-800)" }}>
                {job.job_score}%
              </div>
            </div>
          )}
          {salary && (
            <div>
              <div
                className="uppercase font-bold"
                style={{ fontSize: 11, color: "var(--ds-ink-400)", marginBottom: 4 }}
              >
                Salary
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--ds-ink-800)" }}>
                {salary}
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-col gap-1.5" style={{ marginTop: 20 }}>
        <div className="flex gap-2.5">
          <button
            type="button"
            onClick={onToggleQueue}
            disabled={queued}
            className="font-semibold transition-transform active:scale-[0.98]"
            style={{
              padding: "13px 20px",
              borderRadius: "var(--ds-radius-md)",
              border: "none",
              background: queued ? "var(--ds-cream-300)" : "var(--ds-accent-primary)",
              color: queued ? "var(--ds-ink-700)" : "var(--ds-text-on-brand)",
              fontSize: 14,
              cursor: queued ? "default" : "pointer",
              opacity: applyStatus?.state === "applying" ? 0.7 : 1,
            }}
          >
            {applyStatus?.state === "applying" && "Applying…"}
            {applyStatus?.state === "applied" && "Applied ✓"}
            {applyStatus?.state === "review_required" && "Submitted — review needed"}
            {applyStatus?.state === "failed" && "Failed — try again"}
            {!applyStatus && (queued ? "Queued" : "Add to auto-apply queue")}
          </button>
          <a
            href={job.apply_url}
            target="_blank"
            rel="noreferrer"
            className="flex-shrink-0 font-semibold text-center"
            style={{
              padding: "13px 20px",
              borderRadius: "var(--ds-radius-md)",
              border: "1px solid var(--ds-border-medium)",
              color: "var(--ds-ink-700)",
              fontSize: 14,
            }}
          >
            Apply ↗
          </a>
          <Link
            to="/dashboard/resume-tailor"
            search={{ jobId: job.job_id }}
            className="flex-shrink-0 font-semibold text-center"
            style={{
              padding: "13px 20px",
              borderRadius: "var(--ds-radius-md)",
              border: "1px solid var(--ds-border-medium)",
              color: "var(--ds-ink-700)",
              fontSize: 14,
            }}
          >
            Tailor for this role
          </Link>
        </div>
        {applyStatus?.message && (
          <div style={{ fontSize: 12.5, color: "var(--ds-ink-500)" }}>{applyStatus.message}</div>
        )}
        </div>
      </div>

      {job.description && (
        <AccordionSection title="About" defaultOpen>
          <p style={{ fontSize: 13.5, color: "var(--ds-ink-600)", lineHeight: 1.6, margin: 0 }}>
            {job.description}
          </p>
        </AccordionSection>
      )}

      {matched.length > 0 && (
        <AccordionSection title="Why you're a match ⭐" defaultOpen>
          <div className="flex flex-col gap-2">
            {matched.map((k) => (
              <div
                key={k}
                className="flex items-start gap-2"
                style={{ fontSize: 13.5, color: "var(--ds-ink-700)" }}
              >
                <span style={{ color: "#6B8F5E", fontWeight: 700, flexShrink: 0 }}>✓</span>
                {k}
              </div>
            ))}
          </div>
        </AccordionSection>
      )}

      {(matched.length > 0 || missing.length > 0) && (
        <AccordionSection title="Skills match">
          {matched.length > 0 && (
            <>
              <div
                className="uppercase font-bold"
                style={{ fontSize: 11.5, color: "var(--ds-ink-400)", marginBottom: 8 }}
              >
                Matched
              </div>
              <div className="flex flex-wrap gap-1.5" style={{ marginBottom: 14 }}>
                {matched.map((s) => (
                  <span
                    key={s}
                    className="font-semibold"
                    style={{
                      fontSize: 12.5,
                      color: "#4A6B3E",
                      background: "rgba(107,143,94,0.14)",
                      padding: "5px 11px",
                      borderRadius: "var(--ds-radius-pill)",
                    }}
                  >
                    ✓ {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {missing.length > 0 && (
            <>
              <div
                className="uppercase font-bold"
                style={{ fontSize: 11.5, color: "var(--ds-ink-400)", marginBottom: 8 }}
              >
                Missing
              </div>
              <div className="flex flex-wrap gap-1.5">
                {missing.map((s) => (
                  <span
                    key={s}
                    className="font-semibold"
                    style={{
                      fontSize: 12.5,
                      color: "#9E7A2E",
                      background: "rgba(217,164,65,0.14)",
                      padding: "5px 11px",
                      borderRadius: "var(--ds-radius-pill)",
                    }}
                  >
                    ⚠ {s}
                  </span>
                ))}
              </div>
            </>
          )}
        </AccordionSection>
      )}

      {salary && (
        <AccordionSection title="Salary & benefits">
          <div
            className="font-bold"
            style={{ fontSize: 16, color: "var(--ds-ink-800)", marginBottom: 6 }}
          >
            {salary}
          </div>
          <div style={{ fontSize: 13.5, color: "var(--ds-ink-500)" }}>
            Full benefits details available once you apply on {job.provider}.
          </div>
        </AccordionSection>
      )}

      <div style={{ height: 8 }} />
    </DsModal>
  );
}
