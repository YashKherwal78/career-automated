import { createFileRoute, Outlet } from "@tanstack/react-router";
import { Sidebar } from "../components/dashboard/Sidebar";
import { DashboardProvider } from "../components/dashboard/DashboardContext";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [{ title: "Dashboard — CareerAutomated" }],
  }),
  component: DashboardLayout,
});

import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "../lib/auth";
import { useSidebarState } from "../lib/useSidebarState";

// Set VITE_DEV_AUTH_BYPASS=true in .env to skip auth redirect during development
const DEV_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true";

function DashboardLayout() {
  const { user, profile, isLoading } = useAuth();
  const navigate = useNavigate();
  const { sidebarOpen, isNarrow, toggleSidebar, closeSidebarOverlay } = useSidebarState();

  // Hard redirect: if auth is resolved and there's no user, go to signup.
  // This fires synchronously during render — no flash, no blank page.
  if (!DEV_BYPASS && !isLoading && !user) {
    return (
      <div style={{ display: "none" }}>
        {/* useEffect redirect as backup */}
        {(() => { navigate({ to: "/signup" }); return null; })()}
      </div>
    );
  }

  if (!DEV_BYPASS && isLoading) {
    return (
      <div
        className="flex min-h-screen flex-col items-center justify-center"
        style={{
          background: "var(--ds-surface-page)",
          fontFamily: "var(--ds-font-body)",
          color: "var(--ds-text-primary)",
        }}
      >
        <div
          className="animate-spin rounded-full"
          style={{
            width: 24,
            height: 24,
            border: "3px solid rgba(226,116,72,0.2)",
            borderTopColor: "var(--ds-accent-primary)",
            marginBottom: 16,
          }}
        />
        <div style={{ fontSize: 13, color: "var(--ds-ink-500)", fontWeight: 500 }}>
          Loading…
        </div>
      </div>
    );
  }

  return (
    <DashboardProvider>
      <div
        className="flex relative"
        style={{
          minHeight: "100vh",
          background: "var(--ds-surface-page)",
          fontFamily: "var(--ds-font-body)",
          color: "var(--ds-text-primary)",
        }}
      >
        <div
          className="pointer-events-none fixed"
          style={{
            top: -120,
            left: 120,
            width: 520,
            height: 520,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(232,93,44,0.18), transparent 70%)",
            filter: "blur(60px)",
            zIndex: 0,
          }}
        />
        <div
          className="pointer-events-none fixed"
          style={{
            top: 280,
            right: -140,
            width: 460,
            height: 460,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(139,123,192,0.14), transparent 70%)",
            filter: "blur(60px)",
            zIndex: 0,
          }}
        />
        <div
          className="pointer-events-none fixed"
          style={{
            bottom: -160,
            left: "40%",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(217,164,65,0.12), transparent 70%)",
            filter: "blur(70px)",
            zIndex: 0,
          }}
        />
        <div
          onClick={toggleSidebar}
          role="button"
          tabIndex={0}
          aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          style={{
            position: "fixed",
            top: 20,
            left: 20,
            width: 44,
            height: 44,
            borderRadius: 12,
            zIndex: 90,
            background: "rgba(255,255,255,0.65)",
            backdropFilter: "blur(16px) saturate(160%)",
            WebkitBackdropFilter: "blur(16px) saturate(160%)",
            border: "1px solid rgba(255,255,255,0.6)",
            cursor: "pointer",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 12,
              top: sidebarOpen ? 21 : 15,
              width: 20,
              height: 2,
              background: "var(--ds-ink-800)",
              borderRadius: 2,
              transform: sidebarOpen ? "rotate(45deg)" : "none",
              transition: "top 0.25s ease, transform 0.25s ease",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 12,
              top: 21,
              width: 20,
              height: 2,
              background: "var(--ds-ink-800)",
              borderRadius: 2,
              opacity: sidebarOpen ? 0 : 1,
              transition: "opacity 0.2s ease",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 12,
              top: sidebarOpen ? 21 : 27,
              width: 20,
              height: 2,
              background: "var(--ds-ink-800)",
              borderRadius: 2,
              transform: sidebarOpen ? "rotate(-45deg)" : "none",
              transition: "top 0.25s ease, transform 0.25s ease",
            }}
          />
        </div>
        {isNarrow && sidebarOpen && (
          <div
            onClick={closeSidebarOverlay}
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 75,
              background: "rgba(30,20,12,0.32)",
            }}
          />
        )}
        <div className="relative" style={{ zIndex: 1 }}>
          <Sidebar isOpen={sidebarOpen} isNarrow={isNarrow} />
        </div>
        <main
          className="flex-1 min-w-0 relative"
          style={{ zIndex: 1, paddingTop: isNarrow ? 76 : undefined }}
        >
          <Outlet />
        </main>
      </div>
    </DashboardProvider>
  );
}
