import { useState, type CSSProperties } from "react";
import { Link, useLocation } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { ServiceRegistry } from "../../lib/services";
import { API_BASE } from "../../lib/api";
import { getDisplayName, getInitial } from "../../lib/displayName";

const NAV_ITEMS = [
  { name: "Dashboard", to: "/dashboard" as const },
  { name: "Jobs", to: "/dashboard/jobs" as const },
  { name: "Tailoring", to: "/dashboard/resume-tailor" as const },
  { name: "Resume", to: "/dashboard/resume" as const },
  { name: "Applications", to: "/dashboard/applications" as const },
  { name: "Outreach", to: "/dashboard/outreach" as const },
  { name: "Settings", to: "/dashboard/settings" as const },
];

function NavIcon({ name, active, pressed }: { name: string; active: boolean; pressed: boolean }) {
  const color = active ? "var(--ds-accent-primary)" : "var(--ds-ink-700)";
  const pressTransition = "transform 160ms cubic-bezier(0.4,0,0.2,1)";
  if (name === "Dashboard") {
    return (
      <div
        className="grid gap-0.5"
        style={{ gridTemplateColumns: "6px 6px", gridTemplateRows: "6px 6px" }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="rounded-[1.5px]"
            style={{
              background: color,
              transform: pressed ? "scale(1.3)" : "scale(1)",
              transition: `${pressTransition} ${i * 30}ms`,
            }}
          />
        ))}
      </div>
    );
  }
  if (name === "Tailoring") {
    // Two equalizer-style slider tracks, each with a round handle that
    // slides along the track on press — matches the design's two sliders,
    // not a plain double-line icon.
    const handleLeft = [pressed ? 6 : 9, pressed ? 5 : 2];
    return (
      <div className="flex flex-col gap-[5px]" style={{ width: 16 }}>
        {[0, 1].map((i) => (
          <div key={i} className="relative rounded-[1px]" style={{ height: 2, background: color }}>
            <div
              className="absolute rounded-full"
              style={{
                top: -3,
                width: 8,
                height: 8,
                background: color,
                left: handleLeft[i],
                transition: `left 220ms cubic-bezier(0.4,0,0.2,1) ${i * 20}ms`,
              }}
            />
          </div>
        ))}
      </div>
    );
  }
  if (name === "Resume") {
    // Document outline with two text lines + a short trailing line, not a
    // blank rectangle.
    return (
      <div
        className="relative rounded-[2px]"
        style={{
          width: 14,
          height: 16,
          border: `2px solid ${color}`,
          transition: "width 160ms cubic-bezier(0.4,0,0.2,1)",
        }}
      >
        <div
          className="absolute rounded-[1px]"
          style={{
            top: 3,
            left: 2,
            height: 1.4,
            background: color,
            width: pressed ? 9.5 : 8,
            transition: "width 200ms cubic-bezier(0.4,0,0.2,1)",
          }}
        />
        <div
          className="absolute rounded-[1px]"
          style={{
            top: 6.5,
            left: 2,
            height: 1.4,
            background: color,
            width: pressed ? 9.5 : 8,
            transition: "width 200ms cubic-bezier(0.4,0,0.2,1) 40ms",
          }}
        />
        <div
          className="absolute rounded-[1px]"
          style={{ top: 10, left: 2, width: 5, height: 1.4, background: color }}
        />
      </div>
    );
  }
  if (name === "Jobs") {
    return (
      <div
        className="relative rounded-[2px]"
        style={{
          width: 16,
          height: 12,
          border: `2px solid ${color}`,
          transform: pressed ? "translateY(-1px)" : "translateY(0)",
          transition: "transform 160ms cubic-bezier(0.4,0,0.2,1)",
        }}
      >
        <div
          className="absolute rounded-t-[1px]"
          style={{
            top: -5,
            left: "50%",
            marginLeft: -3,
            width: 6,
            height: 4,
            border: `2px solid ${color}`,
            borderBottom: "none",
          }}
        />
        <div
          className="absolute"
          style={{ top: -1, left: 0, right: 0, height: 2, background: color }}
        />
      </div>
    );
  }
  if (name === "Applications") {
    const widths = pressed ? [11, 16, 10] : [16, 12, 14];
    return (
      <div className="flex flex-col gap-[3px]" style={{ width: 16 }}>
        {widths.map((w, i) => (
          <div
            key={i}
            className="rounded-[1px]"
            style={{
              height: 2,
              background: color,
              width: w,
              transition: `width 200ms cubic-bezier(0.4,0,0.2,1) ${i * 40}ms`,
            }}
          />
        ))}
      </div>
    );
  }
  if (name === "Outreach") {
    // Simple envelope: rectangle + a "V" fold line, flap lifts slightly on press.
    return (
      <div
        className="relative rounded-[2px]"
        style={{
          width: 16,
          height: 12,
          border: `2px solid ${color}`,
          transition: "transform 160ms cubic-bezier(0.4,0,0.2,1)",
          transform: pressed ? "translateY(-1px)" : "translateY(0)",
        }}
      >
        <div
          className="absolute"
          style={{
            top: pressed ? -1 : 0,
            left: 0,
            width: 0,
            height: 0,
            borderLeft: "8px solid transparent",
            borderRight: "8px solid transparent",
            borderTop: `6px solid ${color}`,
            transition: "top 160ms cubic-bezier(0.4,0,0.2,1)",
          }}
        />
      </div>
    );
  }
  // Settings gear
  return (
    <div
      className="relative"
      style={{
        width: 20,
        height: 20,
        transform: pressed ? "rotate(35deg)" : "rotate(0deg)",
        transition: "transform 220ms cubic-bezier(0.4,0,0.2,1)",
      }}
    >
      {[0, 60, 120, 180, 240, 300].map((deg) => (
        <div
          key={deg}
          className="absolute rounded-[1px]"
          style={{
            top: "50%",
            left: "50%",
            width: 3.5,
            height: 5,
            background: color,
            transform: `translate(-50%,-50%) rotate(${deg}deg) translateY(-9px)`,
          }}
        />
      ))}
      <div
        className="absolute rounded-full box-border"
        style={{
          top: "50%",
          left: "50%",
          width: 12,
          height: 12,
          margin: "-6px 0 0 -6px",
          border: `2.5px solid ${color}`,
        }}
      />
      <div
        className="absolute rounded-full"
        style={{
          top: "50%",
          left: "50%",
          width: 3,
          height: 3,
          margin: "-1.5px 0 0 -1.5px",
          background: color,
        }}
      />
    </div>
  );
}

export interface SidebarProps {
  isOpen: boolean;
  isNarrow: boolean;
}

export function Sidebar({ isOpen, isNarrow }: SidebarProps) {
  const location = useLocation();
  const { profile, session } = useAuth();
  const [pressedItem, setPressedItem] = useState<string | null>(null);
  const displayName = getDisplayName(profile?.full_name, profile?.email, "You");
  const initial = getInitial(profile?.full_name, profile?.email, "?");
  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => ServiceRegistry.getBillingService().getSubscription(),
    staleTime: 60_000,
  });
  const tierLabel = subscription?.tier === "pro" ? "Premium" : "Free";

  const { data: resumeAttached } = useQuery({
    queryKey: ["candidate-profile-completeness"],
    meta: { persist: true },
    queryFn: async (): Promise<boolean> => {
      const res = await fetch(`${API_BASE}/candidate/profile`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (!res.ok) return false;
      const data = await res.json();
      const p = data.profile_data || {};
      const hasSkills = Object.values(p.skills || {}).some(
        (arr: unknown) => Array.isArray(arr) && arr.length > 0,
      );
      return (p.experience || []).length > 0 || hasSkills || !!p.resume_url;
    },
    enabled: !!session,
  });

  const { data: needsReview = [] } = useQuery({
    queryKey: ["needs-review"],
    queryFn: () => ServiceRegistry.getJobService().getNeedsReview(),
    enabled: !!session,
    refetchInterval: 15000,
  });
  const { data: referralDrafts = [] } = useQuery({
    queryKey: ["referral-drafts"],
    queryFn: () => ServiceRegistry.getReferralService().list(),
    enabled: !!session,
    refetchInterval: 15000,
  });
  const applicationsBadgeCount = needsReview.length;
  const outreachBadgeCount = referralDrafts.filter((r) => r.status === "PENDING_REVIEW").length;

  const narrowStyle: CSSProperties = {
    position: "fixed",
    top: 0,
    left: 0,
    bottom: 0,
    width: "min(248px, 78vw)",
    zIndex: 80,
    background: "var(--ds-surface-card, #ffffff)",
    boxShadow: "4px 0 24px rgba(0,0,0,0.12)",
    transform: isOpen ? "translateX(0)" : "translateX(-100%)",
    transition: "transform 0.35s cubic-bezier(0.4,0,0.2,1)",
    overflow: "hidden",
    padding: "74px 18px 26px",
  };
  const wideStyle: CSSProperties = {
    position: "sticky",
    top: 0,
    alignSelf: "flex-start",
    width: isOpen ? 248 : 0,
    minHeight: "100vh",
    background: "var(--ds-glass-65, rgba(255,255,255,0.5))",
    backdropFilter: "blur(20px) saturate(160%)",
    WebkitBackdropFilter: "blur(20px) saturate(160%)",
    borderRight: "1px solid rgba(255,255,255,0.6)",
    overflow: "hidden",
    transition: "width 0.4s cubic-bezier(0.4,0,0.2,1), padding 0.4s cubic-bezier(0.4,0,0.2,1)",
    padding: isOpen ? "74px 18px 26px" : "74px 0 26px",
  };

  return (
    <div
      className="flex flex-col"
      style={{
        ...(isNarrow ? narrowStyle : wideStyle),
        flexShrink: 0,
      }}
    >
      <Link to="/" className="whitespace-nowrap" style={{ padding: "0 10px", marginBottom: 40 }}>
        <div className="flex items-center gap-1.5">
          <div
            className="relative flex-shrink-0"
            style={{ width: 30, height: 30, borderRadius: 8.14, background: "var(--ds-ink-900)" }}
          >
            <div
              className="absolute rounded-full"
              style={{
                top: 6.47,
                left: 6.47,
                width: 18.86,
                height: 18.86,
                background: "var(--ds-accent-primary)",
              }}
            >
              <div
                className="absolute rounded-full"
                style={{
                  top: 5.29,
                  left: 5.29,
                  width: 7.71,
                  height: 7.71,
                  background: "var(--ds-ink-900)",
                }}
              />
            </div>
          </div>
          <span
            className="font-[var(--ds-font-display)] font-bold"
            style={{
              fontSize: 16,
              letterSpacing: "var(--ds-tracking-snug)",
              color: "var(--ds-text-primary)",
            }}
          >
            CareerAutomated
          </span>
        </div>
      </Link>

      <nav className="flex flex-col gap-1.5 whitespace-nowrap">
        {NAV_ITEMS.map((item) => {
          const active = location.pathname === item.to;
          const isPressed = pressedItem === item.name;
          return (
            <Link
              key={item.name}
              to={item.to}
              className="flex items-center gap-3 transition-colors"
              style={{
                padding: "10px 14px",
                borderRadius: 12,
                color: active ? "var(--ds-brand-orange-text)" : "var(--ds-ink-600)",
                fontWeight: 600,
                fontSize: 15,
                background: active ? "var(--ds-brand-orange-tint-08)" : "transparent",
              }}
              onMouseDown={() => setPressedItem(item.name)}
              onMouseUp={() => setPressedItem(null)}
              onMouseLeave={() => setPressedItem(null)}
            >
              <div
                className="relative flex items-center justify-center flex-shrink-0"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.5)",
                  border: "1px solid rgba(255,255,255,0.6)",
                }}
              >
                <NavIcon name={item.name} active={active} pressed={isPressed} />
                {item.name === "Resume" && (
                  <span
                    title={resumeAttached ? "Resume attached" : "No resume attached yet"}
                    className="absolute rounded-full"
                    style={{
                      width: 8,
                      height: 8,
                      top: -1,
                      right: -1,
                      background: resumeAttached ? "var(--ds-accent-success, #6B8F5E)" : "var(--ds-ink-300)",
                      border: "1.5px solid var(--ds-surface-card, #fff)",
                    }}
                  />
                )}
                {item.name === "Applications" && applicationsBadgeCount > 0 && (
                  <span
                    title={`${applicationsBadgeCount} need your attention`}
                    className="absolute flex items-center justify-center font-bold"
                    style={{
                      minWidth: 16,
                      height: 16,
                      padding: "0 4px",
                      top: -4,
                      right: -4,
                      borderRadius: 8,
                      background: "#B4392C",
                      color: "#fff",
                      fontSize: 10,
                      border: "1.5px solid var(--ds-surface-card, #fff)",
                    }}
                  >
                    {applicationsBadgeCount > 9 ? "9+" : applicationsBadgeCount}
                  </span>
                )}
                {item.name === "Outreach" && outreachBadgeCount > 0 && (
                  <span
                    title={`${outreachBadgeCount} referral drafts waiting on you`}
                    className="absolute flex items-center justify-center font-bold"
                    style={{
                      minWidth: 16,
                      height: 16,
                      padding: "0 4px",
                      top: -4,
                      right: -4,
                      borderRadius: 8,
                      background: "#B4392C",
                      color: "#fff",
                      fontSize: 10,
                      border: "1.5px solid var(--ds-surface-card, #fff)",
                    }}
                  >
                    {outreachBadgeCount > 9 ? "9+" : outreachBadgeCount}
                  </span>
                )}
              </div>
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Profile Card */}
      <Link
        to="/dashboard/career-profile"
        className="mt-auto flex items-center gap-2.5 min-w-0 group"
        style={{
          padding: "10px 12px",
          background: "rgba(255,255,255,0.75)",
          backdropFilter: "blur(16px) saturate(180%)",
          borderRadius: 16,
          border: "1px solid rgba(226, 232, 240, 0.8)",
          boxShadow: "0 2px 10px rgba(0,0,0,0.03)",
        }}
      >
        {profile?.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={displayName}
            className="w-9 h-9 rounded-full object-cover flex-shrink-0 ring-2 ring-slate-200/80 group-hover:ring-orange-400 transition-all duration-150"
          />
        ) : (
          <div
            className="flex items-center justify-center flex-shrink-0 font-bold rounded-full group-hover:scale-105 transition-transform duration-150"
            style={{
              width: 36,
              height: 36,
              background: "linear-gradient(135deg, var(--ds-ink-800), var(--ds-ink-950))",
              color: "var(--ds-text-on-dark)",
              fontSize: 13.5,
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.15)",
            }}
          >
            {initial}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div
            className="font-semibold text-slate-900 truncate group-hover:text-orange-600 transition-colors"
            style={{ fontSize: 13.5, lineHeight: "1.25" }}
            title={displayName}
          >
            {displayName}
          </div>
          <div
            className="mt-0.5"
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: subscription?.tier === "pro" ? "var(--ds-accent-success, #6B8F5E)" : "var(--ds-ink-500)",
            }}
          >
            {tierLabel}
          </div>
        </div>
      </Link>
    </div>
  );
}
