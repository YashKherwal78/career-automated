import { createFileRoute, Outlet, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/mission-control')({
  component: MissionControlLayout,
})

import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "../lib/auth";

function MissionControlLayout() {
  const { user, profile, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        navigate({ to: "/signup" });
      } else if (profile && !profile.onboarding_complete) {
        navigate({ to: "/onboarding" });
      }
    }
  }, [user, profile, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-300">
        <div className="text-sm font-medium">Loading session...</div>
      </div>
    );
  }

  if (!user) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="dark min-h-screen bg-zinc-950 text-zinc-300 font-sans text-sm selection:bg-zinc-800">
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 border-r border-zinc-800 bg-zinc-900/50 flex flex-col">
          <div className="h-14 border-b border-zinc-800 flex items-center px-4">
            <span className="font-bold text-zinc-100 tracking-tight flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              MISSION CONTROL
            </span>
          </div>
          <nav className="flex-1 overflow-y-auto p-4 space-y-1">
            <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 mt-4">Observability</div>
            <Link to="/mission-control/decision-engine" activeProps={{ className: 'bg-zinc-800/50 text-emerald-400 font-medium' }} inactiveProps={{ className: 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-colors' }} className="flex items-center gap-2 px-2 py-1.5 rounded">
              Decision Engine
            </Link>
            <Link to="/mission-control" activeOptions={{ exact: true }} activeProps={{ className: 'bg-zinc-800/50 text-emerald-400 font-medium' }} inactiveProps={{ className: 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-colors' }} className="flex items-center gap-2 px-2 py-1.5 rounded">
              Pipeline Map
            </Link>
            <Link to="/mission-control/leakage-explorer" activeProps={{ className: 'bg-zinc-800/50 text-emerald-400 font-medium' }} inactiveProps={{ className: 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-colors' }} className="flex items-center gap-2 px-2 py-1.5 rounded">
              Leakage Explorer
            </Link>
            
            <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 mt-6">Workflows</div>
            <Link to="/mission-control/telemetry" activeProps={{ className: 'bg-zinc-800/50 text-emerald-400 font-medium' }} inactiveProps={{ className: 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-colors' }} className="flex items-center gap-2 px-2 py-1.5 rounded">
              Telemetry Coverage
            </Link>
            <Link to="/mission-control/unknown" activeProps={{ className: 'bg-zinc-800/50 text-emerald-400 font-medium' }} inactiveProps={{ className: 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-colors' }} className="flex items-center gap-2 px-2 py-1.5 rounded justify-between">
              Unknown Pipeline
              <span className="bg-amber-500/10 text-amber-500 text-[10px] px-1.5 py-0.5 rounded">1432</span>
            </Link>

            <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 mt-6">Tools</div>
            <Link to="/mission-control/company-replay" activeProps={{ className: 'bg-zinc-800/50 text-emerald-400 font-medium' }} inactiveProps={{ className: 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-colors' }} className="flex items-center gap-2 px-2 py-1.5 rounded">
              Company Replay
            </Link>
          </nav>
          
          <div className="p-4 border-t border-zinc-800 text-xs text-zinc-500 flex justify-between items-center">
            <span>v3.0.0-rc</span>
            <span className="flex items-center gap-1"><kbd className="bg-zinc-800 px-1 py-0.5 rounded border border-zinc-700">⌘K</kbd></span>
          </div>
        </aside>

        {/* Main Content Pane */}
        <main className="flex-1 flex flex-col relative overflow-hidden bg-zinc-950">
          <header className="h-14 border-b border-zinc-800 flex items-center px-6 justify-between bg-zinc-900/30 backdrop-blur-sm z-10">
            <div className="flex items-center gap-3">
              <h1 className="text-zinc-200 font-semibold tracking-wide">Engineering Operations</h1>
              <span className="text-zinc-600 text-xs">/ Live data flow & leakage</span>
            </div>
            
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Pipeline Status:</span>
                <span className="text-emerald-400 font-medium flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div> Healthy
                </span>
              </div>
              <div className="h-4 w-px bg-zinc-800"></div>
              <div className="text-zinc-400">Last run: 2m ago</div>
            </div>
          </header>
          
          <div className="flex-1 overflow-auto p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
