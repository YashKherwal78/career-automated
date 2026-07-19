import React from 'react';
import { LayoutDashboard, Cable, Cpu, Layers, Activity, FileText, Settings, ShieldAlert, GitCommit, Search, RefreshCw, BarChart2 } from 'lucide-react';

interface Props {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  systemStatus: string;
}

export const Sidebar: React.FC<Props> = ({ activeTab, setActiveTab, systemStatus }) => {
  const menuItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'connectors', label: 'Connectors', icon: Cable },
    { id: 'workers', label: 'Workers', icon: Cpu },
    { id: 'queues', label: 'Queues', icon: Layers },
    { id: 'pipeline', label: 'Pipeline Flow', icon: Activity },
    { id: 'tracing', label: 'Trace Explorer', icon: Search },
    { id: 'infrastructure', label: 'Infrastructure', icon: BarChart2 },
    { id: 'ai', label: 'AI Operations', icon: Settings },
    { id: 'alerts', label: 'Alerts Center', icon: ShieldAlert },
    { id: 'deployments', label: 'Deployments', icon: GitCommit },
    { id: 'logs', label: 'Live Logs', icon: FileText },
  ];

  return (
    <div className="w-64 border-r border-zinc-800 bg-zinc-950/70 backdrop-blur-md flex flex-col h-screen select-none font-sans text-xs text-zinc-400">
      {/* Header logo */}
      <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="font-bold text-sm tracking-tight text-white uppercase">Mission Control</span>
        </div>
        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-zinc-900 border border-zinc-800 text-zinc-500">v3.0</span>
      </div>

      {/* Tabs */}
      <div className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md font-medium transition-all ${
                isActive
                  ? 'bg-zinc-800 text-white border-l-2 border-emerald-500'
                  : 'hover:bg-zinc-900/60 hover:text-zinc-200'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-zinc-800 bg-zinc-900/20">
        <div className="flex justify-between items-center">
          <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">System State</span>
          <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${
            systemStatus === 'ONLINE' ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'
          }`}>
            {systemStatus}
          </span>
        </div>
      </div>
    </div>
  );
};
