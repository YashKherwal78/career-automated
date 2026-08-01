import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const [theme, setTheme] = useState("light");
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [crawlInterval, setCrawlInterval] = useState("daily");

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Settings</h1>
        <p className="mt-1 text-xs text-ink-soft">
          Configure account parameters and scraper preferences.
        </p>
      </div>

      <div className="max-w-xl glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-6 text-xs">
        
        {/* Theme Settings */}
        <div className="space-y-3">
          <h3 className="font-semibold text-ink uppercase tracking-wider text-[10px]">Theme Mode</h3>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer font-medium text-ink">
              <input
                type="radio"
                name="theme"
                value="light"
                checked={theme === "light"}
                onChange={() => setTheme("light")}
                className="text-[color:var(--peach-deep)] focus:ring-[color:var(--peach-deep)] h-4 w-4"
              />
              Light Mode
            </label>
            <label className="flex items-center gap-2 cursor-pointer font-medium text-ink opacity-60">
              <input
                type="radio"
                name="theme"
                value="dark"
                checked={theme === "dark"}
                disabled
                className="text-[color:var(--peach-deep)] focus:ring-[color:var(--peach-deep)] h-4 w-4 cursor-not-allowed"
              />
              Dark Mode (Coming Soon)
            </label>
          </div>
        </div>

        {/* Email Alerts */}
        <div className="space-y-3 border-t border-white/20 pt-6">
          <h3 className="font-semibold text-ink uppercase tracking-wider text-[10px]">Notifications</h3>
          <label className="flex items-center gap-2 cursor-pointer font-medium text-ink">
            <input
              type="checkbox"
              checked={emailAlerts}
              onChange={() => setEmailAlerts(!emailAlerts)}
              className="text-[color:var(--peach-deep)] focus:ring-[color:var(--peach-deep)] rounded h-4 w-4"
            />
            Send email notifications when new matched jobs are indexed
          </label>
        </div>

        {/* Scraper preferences */}
        <div className="space-y-3 border-t border-white/20 pt-6">
          <h3 className="font-semibold text-ink uppercase tracking-wider text-[10px]">Pipeline Preferences</h3>
          <div className="space-y-2">
            <span className="block text-ink-soft">Scan Frequency</span>
            <select
              value={crawlInterval}
              onChange={(e) => setCrawlInterval(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-white/50 border border-white/60 focus:outline-none text-ink-soft focus:border-[color:var(--peach-deep)] cursor-pointer"
            >
              <option value="daily">Daily scan checks</option>
              <option value="weekly">Weekly scan checks</option>
              <option value="realtime">Continuous loop (high resource)</option>
            </select>
          </div>
        </div>

        {/* Action button */}
        <div className="border-t border-white/20 pt-6 flex justify-end">
          <button className="btn-peach px-4 py-2 rounded-xl text-xs font-semibold">
            Save Preferences
          </button>
        </div>

      </div>
    </div>
  );
}
