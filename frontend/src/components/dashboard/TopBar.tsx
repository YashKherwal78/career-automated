import React from "react";
import { Search, Bell, CheckCircle } from "lucide-react";

export function TopBar() {
  return (
    <header className="h-16 border-b border-white/40 bg-white/30 backdrop-blur px-8 flex items-center justify-between">
      {/* Search jobs input placeholder */}
      <div className="relative w-80">
        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-4 w-4 text-ink-soft" />
        </span>
        <input
          type="text"
          placeholder="Search jobs, companies..."
          disabled
          className="w-full pl-9 pr-4 py-1.5 text-xs rounded-xl bg-white/50 border border-white/60 focus:outline-none focus:border-[color:var(--peach-deep)] transition-colors cursor-not-allowed opacity-60"
        />
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-4">
        {/* Sync Status */}
        <div className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg border border-emerald-100">
          <CheckCircle className="h-3.5 w-3.5" />
          <span>All systems synced</span>
        </div>

        {/* Notification bell (visual only) */}
        <button className="relative rounded-lg bg-white/50 border border-white/60 p-1.5 text-ink-soft hover:text-ink transition-colors">
          <Bell className="h-4 w-4" />
          <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-[color:var(--peach-deep)]" />
        </button>

        {/* User avatar */}
        <div className="h-8 w-8 rounded-full border border-white/80 overflow-hidden bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=256&auto=format&fit=crop')" }}>
        </div>
      </div>
    </header>
  );
}
