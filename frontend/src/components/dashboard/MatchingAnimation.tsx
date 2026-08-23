import { useEffect, useState } from "react";

/**
 * Loading state for the dashboard's top-jobs strip while /jobs is still
 * computing matches. Replaces a plain "Loading your matches..." text line.
 *
 * Signature idea: three skeleton cards, shaped exactly like the real job
 * cards they're about to become, each swept by a soft highlight -- the
 * same "scanning" language the empty-state copy right below this already
 * uses ("CareerAutomated is watching company career pages and job boards
 * right now"). A status line above cycles through the real stages of what
 * the backend is actually doing, not invented flavor text.
 */
const STAGES = [
  "Reading your resume…",
  "Scanning open roles…",
  "Scoring your fit…",
  "Almost there…",
];

const STAGE_INTERVAL_MS = 1800;

function SkeletonJobCard({ delayMs }: { delayMs: number }) {
  return (
    <div
      className="flex-shrink-0"
      style={{
        width: 220,
        boxSizing: "border-box",
        background: "rgba(255,255,255,0.55)",
        border: "1px solid rgba(255,255,255,0.6)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        boxShadow: "0 10px 26px -14px rgba(60,40,20,0.22)",
        borderRadius: "var(--ds-radius-xl)",
        padding: 18,
        overflow: "hidden",
        position: "relative",
      }}
    >
      <div
        className="animate-shimmer-sweep"
        style={{
          position: "absolute",
          inset: 0,
          animationDelay: `${delayMs}ms`,
          background:
            "linear-gradient(100deg, transparent 30%, rgba(226,116,72,0.14) 48%, rgba(226,116,72,0.22) 50%, rgba(226,116,72,0.14) 52%, transparent 70%)",
          backgroundSize: "250% 100%",
        }}
      />
      <div className="flex items-center gap-2" style={{ marginBottom: 14, position: "relative" }}>
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: 6,
            background: "var(--ds-cream-300)",
            flexShrink: 0,
          }}
        />
        <div style={{ width: "60%", height: 10, borderRadius: 4, background: "var(--ds-cream-300)" }} />
      </div>
      <div style={{ position: "relative", minHeight: 44, marginBottom: 14 }}>
        <div style={{ width: "90%", height: 13, borderRadius: 4, background: "var(--ds-cream-300)", marginBottom: 8 }} />
        <div style={{ width: "65%", height: 13, borderRadius: 4, background: "var(--ds-cream-300)" }} />
      </div>
      <div
        style={{
          position: "relative",
          width: 72,
          height: 20,
          borderRadius: "var(--ds-radius-pill)",
          background: "var(--ds-cream-300)",
        }}
      />
    </div>
  );
}

export function MatchingAnimation() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStageIndex((i) => (i + 1) % STAGES.length);
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <div className="flex items-center gap-2" style={{ marginBottom: 16, paddingLeft: 2 }}>
        <span
          className="animate-pulse-dot"
          style={{
            width: 6,
            height: 6,
            borderRadius: "var(--ds-radius-circle)",
            background: "var(--ds-accent-primary)",
            flexShrink: 0,
          }}
        />
        <span
          key={stageIndex}
          className="animate-status-in"
          style={{
            fontSize: 13.5,
            color: "var(--ds-ink-500)",
            fontWeight: 500,
          }}
        >
          {STAGES[stageIndex]}
        </span>
      </div>
      <div
        className="flex overflow-x-auto pb-2 no-scrollbar"
        style={{ WebkitOverflowScrolling: "touch", gap: 20 }}
      >
        <SkeletonJobCard delayMs={0} />
        <SkeletonJobCard delayMs={150} />
        <SkeletonJobCard delayMs={300} />
      </div>
    </div>
  );
}
