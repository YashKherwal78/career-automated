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

function DashboardLayout() {
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
