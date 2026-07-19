import React, { useState } from "react";
import { Link, useLocation } from "@tanstack/react-router";
import { 
  LayoutDashboard, 
  Briefcase, 
  Building2, 
  GitFork, 
  FileText, 
  Send, 
  BarChart3, 
  Settings, 
  ShieldAlert,
  LogOut,
  User
} from "lucide-react";

export function Sidebar() {
  const location = useLocation();
  const [isAdminMode, setIsAdminMode] = useState(false);

  const userNavigation = [
    { name: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
    { name: "Jobs", to: "/dashboard/jobs", icon: Briefcase },
    { name: "Resume", to: "/dashboard/resume", icon: FileText },
    { name: "Resume Tailor", to: "/dashboard/resume-tailor", icon: GitFork },
    { name: "Applications", to: "/dashboard/applications", icon: Send },
    { name: "Settings", to: "/dashboard/settings", icon: Settings },
  ];

  const adminNavigation = [
    { name: "Mission Control", to: "/mission-control", icon: ShieldAlert },
    { name: "Admin Console", to: "/dashboard/admin", icon: ShieldAlert },
    ...userNavigation
  ];

  const navigation = isAdminMode ? adminNavigation : userNavigation;

  return (
    <aside className="w-64 border-r border-white/40 bg-white/40 backdrop-blur min-h-screen flex flex-col justify-between p-6">
      <div className="space-y-8">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg peach-gradient flex items-center justify-center font-display text-white text-lg font-bold">
            CA
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-ink">CareerAutomated</span>
        </div>

        {/* View mode toggle for Operator */}
        <div className="rounded-lg bg-white/50 border border-white p-1 flex">
          <button
            onClick={() => setIsAdminMode(false)}
            className={`flex-1 text-center py-1 text-xs font-medium rounded ${!isAdminMode ? 'bg-[color:var(--peach-deep)] text-white' : 'text-ink-soft hover:text-ink'}`}
          >
            User Mode
          </button>
          <button
            onClick={() => setIsAdminMode(true)}
            className={`flex-1 text-center py-1 text-xs font-medium rounded ${isAdminMode ? 'bg-ink text-white' : 'text-ink-soft hover:text-ink'}`}
          >
            Operator
          </button>
        </div>

        {/* Navigation links */}
        <nav className="space-y-1">
          {navigation.map((item) => {
            const active = location.pathname === item.to;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200 ${
                  active
                    ? "bg-[color:var(--peach-soft)] text-[color:var(--peach-deep)]"
                    : "text-ink-soft hover:bg-white/50 hover:text-ink"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User profile section */}
      <div className="border-t border-white/20 pt-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-white/80 border border-white flex items-center justify-center">
            <User className="h-4 w-4 text-ink-soft" />
          </div>
          <div className="space-y-0.5">
            <h4 className="text-xs font-semibold text-ink">Yash Kherwal</h4>
            <span className="text-[10px] text-ink-soft">Student (IIT-R)</span>
          </div>
        </div>
        <button className="text-ink-soft hover:text-ink transition-colors">
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
}
