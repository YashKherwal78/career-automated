import { Link, useLocation } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../lib/auth";
import { ServiceRegistry } from "../../lib/services";

const NAV_ITEMS = [
  { name: "Dashboard", to: "/dashboard" as const },
  { name: "Tailoring", to: "/dashboard/resume-tailor" as const },
  { name: "Resume", to: "/dashboard/resume" as const },
  { name: "Applications", to: "/dashboard/applications" as const },
  { name: "Settings", to: "/dashboard/settings" as const },
];

function NavIcon({ name, active }: { name: string; active: boolean }) {
  const color = active ? "var(--ds-accent-primary)" : "var(--ds-ink-700)";
  if (name === "Dashboard") {
    return (
      <div
        className="grid gap-0.5"
        style={{ gridTemplateColumns: "6px 6px", gridTemplateRows: "6px 6px" }}
      >
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-[1px]" style={{ background: color }} />
        ))}
      </div>
    );
  }
  if (name === "Tailoring") {
    return (
      <div className="flex flex-col gap-1.5" style={{ width: 16 }}>
        <div className="rounded-full" style={{ height: 2, background: color }} />
        <div className="rounded-full" style={{ height: 2, background: color }} />
      </div>
    );
  }
  if (name === "Resume") {
    return (
      <div
        className="relative rounded-[2px]"
        style={{ width: 14, height: 16, border: `2px solid ${color}` }}
      />
    );
  }
  if (name === "Applications") {
    return (
      <div className="flex flex-col gap-[3px]" style={{ width: 16 }}>
        <div className="rounded-[1px]" style={{ height: 3, background: color }} />
        <div className="rounded-[1px]" style={{ height: 3, background: color, width: "70%" }} />
        <div className="rounded-[1px]" style={{ height: 3, background: color, width: "40%" }} />
      </div>
    );
  }
  // Settings gear
  return (
    <div className="relative" style={{ width: 20, height: 20 }}>
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

export function Sidebar() {
  const location = useLocation();
  const { profile, logout } = useAuth();
  const initial = (profile?.full_name || "?").charAt(0).toUpperCase();
  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => ServiceRegistry.getBillingService().getSubscription(),
    staleTime: 60_000,
  });
  const tierLabel = subscription?.tier === "pro" ? "Pro" : "Free tier";

  return (
    <div
      className="flex flex-col"
      style={{ width: 232, flexShrink: 0, padding: "24px 16px", minHeight: "100vh" }}
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
          return (
            <Link
              key={item.name}
              to={item.to}
              className="flex items-center gap-3 transition-colors"
              style={{
                padding: "9px 12px",
                borderRadius: 12,
                color: active ? "var(--ds-brand-orange-text)" : "var(--ds-ink-600)",
                fontWeight: 600,
                fontSize: 15,
                background: active ? "var(--ds-brand-orange-tint-08)" : "transparent",
              }}
            >
              <div
                className="flex items-center justify-center flex-shrink-0"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.5)",
                  border: "1px solid rgba(255,255,255,0.6)",
                }}
              >
                <NavIcon name={item.name} active={active} />
              </div>
              {item.name}
            </Link>
          );
        })}
      </nav>

      <Link
        to="/dashboard/career-profile"
        className="flex items-center gap-3 whitespace-nowrap"
        style={{
          marginTop: "auto",
          padding: "14px 12px",
          background: "rgba(255,255,255,0.45)",
          backdropFilter: "blur(14px) saturate(160%)",
          borderRadius: "var(--ds-radius-lg)",
          border: "1px solid rgba(255,255,255,0.55)",
        }}
      >
        <div
          className="flex items-center justify-center flex-shrink-0 font-semibold"
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "var(--ds-ink-800)",
            color: "var(--ds-text-on-dark)",
            fontSize: 13,
          }}
        >
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-semibold" style={{ fontSize: 14, color: "var(--ds-ink-900)" }}>
            {profile?.full_name || "You"}
          </div>
          <div
            className="flex items-center gap-1"
            style={{ fontSize: 11.5, color: "var(--ds-ink-450)" }}
          >
            <span
              className="rounded-full flex-shrink-0"
              style={{ width: 4, height: 4, background: "var(--ds-ink-400)" }}
            />
            {tierLabel}
          </div>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            logout();
          }}
          className="flex-shrink-0"
          style={{ fontSize: 11, color: "var(--ds-ink-450)", fontWeight: 600 }}
        >
          Log out
        </button>
      </Link>
    </div>
  );
}
