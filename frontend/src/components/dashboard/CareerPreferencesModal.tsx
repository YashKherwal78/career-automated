import { useState } from "react";
import { DsModal, DsModalCloseButton } from "../ds/Modal";
import { DsChip } from "../ds/Chip";

const WORK_MODES = ["Any", "Remote", "Hybrid", "Onsite"];
const EMPLOYMENT_TYPES = ["Full-time", "Contract", "Internship", "Part-time"];
const COMPANY_SIZES = ["Startup", "Mid-size", "Large", "Any"];
const VISA_OPTIONS = ["Required", "Not required", "No preference"];

export interface CareerPreferences {
  minSalaryLakh: number;
  locations: string;
  workMode: string;
  employmentType: string;
  companySize: string;
  industries: string;
  visaSponsorship: string;
  openToRelocation: boolean;
}

export function CareerPreferencesModal({
  onSave,
  onSkip,
}: {
  onSave: (prefs: CareerPreferences) => void;
  onSkip: () => void;
}) {
  const [minSalaryLakh, setMinSalaryLakh] = useState(10);
  const [locations, setLocations] = useState("");
  const [workMode, setWorkMode] = useState("Remote");
  const [employmentType, setEmploymentType] = useState("Full-time");
  const [companySize, setCompanySize] = useState("Any");
  const [industries, setIndustries] = useState("");
  const [visaSponsorship, setVisaSponsorship] = useState("No preference");
  const [openToRelocation, setOpenToRelocation] = useState(false);

  const inputStyle: React.CSSProperties = {
    width: "100%",
    boxSizing: "border-box",
    padding: "11px 14px",
    borderRadius: "var(--ds-radius-md)",
    border: "1px solid var(--ds-border-medium)",
    fontSize: 13.5,
    fontFamily: "var(--ds-font-body)",
    background: "var(--ds-surface-card)",
    color: "var(--ds-text-primary)",
  };

  return (
    <DsModal onClose={onSkip}>
      <div style={{ padding: 28, position: "relative" }}>
        <DsModalCloseButton onClose={onSkip} />
        <h2
          className="font-[var(--ds-font-display)] font-semibold"
          style={{ fontSize: 21, margin: "0 0 8px", maxWidth: 400 }}
        >
          What opportunities are worth your time?
        </h2>
        <p
          style={{
            fontSize: 13.5,
            color: "var(--ds-ink-500)",
            lineHeight: 1.6,
            margin: "0 0 26px",
            maxWidth: 420,
          }}
        >
          These preferences help CareerAutomated decide which jobs to apply for automatically. You
          can change them anytime from Career Profile.
        </p>

        <div className="flex flex-col gap-5.5">
          <div>
            <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-ink-700)" }}>
                Minimum salary
              </label>
              <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ds-accent-primary)" }}>
                ₹{minSalaryLakh}L
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={80}
              step={5}
              value={minSalaryLakh}
              onChange={(e) => setMinSalaryLakh(Number(e.target.value))}
              style={{ width: "100%", accentColor: "#E27448" }}
            />
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ds-ink-700)",
                marginBottom: 8,
              }}
            >
              Preferred locations
            </label>
            <input
              type="text"
              value={locations}
              onChange={(e) => setLocations(e.target.value)}
              placeholder="Search or type a city…"
              style={inputStyle}
            />
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ds-ink-700)",
                marginBottom: 8,
              }}
            >
              Work mode
            </label>
            <div className="flex flex-wrap gap-2">
              {WORK_MODES.map((m) => (
                <DsChip key={m} label={m} active={workMode === m} onClick={() => setWorkMode(m)} />
              ))}
            </div>
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ds-ink-700)",
                marginBottom: 8,
              }}
            >
              Employment type
            </label>
            <div className="flex flex-wrap gap-2">
              {EMPLOYMENT_TYPES.map((t) => (
                <DsChip
                  key={t}
                  label={t}
                  active={employmentType === t}
                  onClick={() => setEmploymentType(t)}
                />
              ))}
            </div>
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ds-ink-700)",
                marginBottom: 8,
              }}
            >
              Company size
            </label>
            <div className="flex flex-wrap gap-2">
              {COMPANY_SIZES.map((s) => (
                <DsChip
                  key={s}
                  label={s}
                  active={companySize === s}
                  onClick={() => setCompanySize(s)}
                />
              ))}
            </div>
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ds-ink-700)",
                marginBottom: 8,
              }}
            >
              Preferred industries{" "}
              <span style={{ color: "var(--ds-ink-400)", fontWeight: 500 }}>(optional)</span>
            </label>
            <input
              type="text"
              value={industries}
              onChange={(e) => setIndustries(e.target.value)}
              placeholder="e.g. Fintech, Healthcare, SaaS"
              style={inputStyle}
            />
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--ds-ink-700)",
                marginBottom: 8,
              }}
            >
              Visa sponsorship
            </label>
            <div className="flex flex-wrap gap-2">
              {VISA_OPTIONS.map((v) => (
                <DsChip
                  key={v}
                  label={v}
                  active={visaSponsorship === v}
                  onClick={() => setVisaSponsorship(v)}
                />
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-ink-700)" }}>
              Open to relocation
            </label>
            <button
              type="button"
              onClick={() => setOpenToRelocation((v) => !v)}
              style={{
                width: 40,
                height: 22,
                borderRadius: 11,
                background: openToRelocation
                  ? "var(--ds-accent-primary)"
                  : "var(--ds-border-medium)",
                position: "relative",
                transition: "background 160ms linear",
                border: "none",
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 2,
                  left: openToRelocation ? 20 : 2,
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  background: "#fff",
                  transition: "left 160ms linear",
                }}
              />
            </button>
          </div>
        </div>

        <div className="flex gap-2.5" style={{ marginTop: 30 }}>
          <button
            type="button"
            onClick={onSkip}
            className="flex-shrink-0 font-semibold"
            style={{
              padding: "13px 20px",
              borderRadius: "var(--ds-radius-md)",
              border: "1px solid var(--ds-border-medium)",
              background: "transparent",
              color: "var(--ds-ink-600)",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Skip for now
          </button>
          <button
            type="button"
            onClick={() =>
              onSave({
                minSalaryLakh,
                locations,
                workMode,
                employmentType,
                companySize,
                industries,
                visaSponsorship,
                openToRelocation,
              })
            }
            className="flex-1 font-bold"
            style={{
              padding: 13,
              borderRadius: "var(--ds-radius-md)",
              border: "none",
              background: "var(--ds-accent-primary)",
              color: "var(--ds-text-on-brand)",
              fontSize: 14,
              cursor: "pointer",
              boxShadow: "0 10px 22px -8px rgba(226,116,72,0.45)",
            }}
          >
            Enable Auto Apply
          </button>
        </div>
      </div>
    </DsModal>
  );
}
