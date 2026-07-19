import { createFileRoute, Outlet } from "@tanstack/react-router";
import { Sidebar } from "../components/dashboard/Sidebar";
import { TopBar } from "../components/dashboard/TopBar";
import { DashboardProvider } from "../components/dashboard/DashboardContext";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — CareerAutomated" },
    ],
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
      <div className="flex bg-slate-50 min-h-screen text-slate-800 font-sans">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto bg-slate-50/50">
            <Outlet />
          </main>
        </div>
      </div>
    </DashboardProvider>
  );
}
