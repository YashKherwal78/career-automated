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

// Set VITE_DEV_AUTH_BYPASS=true in .env to skip auth redirect during development
const DEV_BYPASS = import.meta.env.VITE_DEV_AUTH_BYPASS === "true";

function DashboardLayout() {
  const { user, profile, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (DEV_BYPASS) return; // Skip auth check in dev bypass mode
    if (!isLoading) {
      if (!user) {
        navigate({ to: "/signup" });
      } else if (profile && !profile.onboarding_complete) {
        navigate({ to: "/onboarding" });
      }
    }
  }, [user, profile, isLoading, navigate]);

  if (!DEV_BYPASS) {
    if (isLoading) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <div className="text-sm font-medium text-slate-500">Loading your profile...</div>
        </div>
      );
    }

    if (!user) {
      return null; // Will redirect in useEffect
    }
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
            background: "radial-gradient(circle, rgba(232,93,44,0.12), transparent 70%)",
            filter: "blur(60px)",
            zIndex: 0,
          }}
        />
        <div className="relative" style={{ zIndex: 1 }}>
          <Sidebar />
        </div>
        <main className="flex-1 min-w-0 relative" style={{ zIndex: 1 }}>
          <Outlet />
        </main>
      </div>
    </DashboardProvider>
  );
}
