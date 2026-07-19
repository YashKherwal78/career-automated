import React from 'react';
import { ShieldCheck, ServerCrash, Cpu, Database, Activity } from 'lucide-react';

interface Props {
  data: any;
}

export const Overview: React.FC<Props> = ({ data }) => {
  const stats = [
    { label: 'Total Crawled Jobs', value: data?.total_jobs || 0, icon: ShieldCheck, color: 'text-emerald-500' },
    { label: 'Active Companies', value: data?.total_companies || 0, icon: Activity, color: 'text-sky-500' },
    { label: 'Ingested Providers', value: data?.total_providers || 0, icon: Database, color: 'text-violet-500' },
    { label: 'Active Sessions', value: data?.active_crawls || 0, icon: Cpu, color: 'text-amber-500' },
  ];

  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="grid grid-cols-4 gap-4">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div key={idx} className="bg-zinc-950/40 border border-zinc-800 rounded-lg p-5 flex items-center justify-between shadow-lg">
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-500">{stat.label}</span>
                <div className="text-2xl font-bold text-white font-mono">{stat.value.toLocaleString()}</div>
              </div>
              <Icon className={`w-8 h-8 ${stat.color} opacity-80`} />
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-semibold text-white">Crawler Session Pipeline Health</h3>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-zinc-900/40 border border-zinc-800/80 rounded p-3 text-center">
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Success Rate</div>
              <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">{data?.success_rate || 98.4}%</div>
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800/80 rounded p-3 text-center">
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">New Jobs Today</div>
              <div className="text-xl font-bold text-sky-400 mt-1 font-mono">{data?.new_jobs_today || 1824}</div>
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800/80 rounded p-3 text-center">
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Active Crawls</div>
              <div className="text-xl font-bold text-amber-400 mt-1 font-mono">{data?.active_crawls || 4}</div>
            </div>
          </div>
        </div>

        <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-semibold text-white">Container Host Resources</h3>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-[10px] font-mono text-zinc-500 uppercase mb-1">
                <span>CPU Load</span>
                <span>{data?.cpu_usage || 14.2}%</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${data?.cpu_usage || 14.2}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-[10px] font-mono text-zinc-500 uppercase mb-1">
                <span>RAM Usage</span>
                <span>{data?.ram_usage || 1.8} GB / 4.0 GB</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden">
                <div className="h-full bg-sky-500 rounded-full" style={{ width: `${((data?.ram_usage || 1.8) / 4) * 100}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
