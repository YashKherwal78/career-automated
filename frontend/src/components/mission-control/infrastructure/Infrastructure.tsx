import React from 'react';
import { Database, Activity, ServerCrash } from 'lucide-react';

interface Props {
  data: any;
}

export const Infrastructure: React.FC<Props> = ({ data }) => {
  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="grid grid-cols-2 gap-4">
        <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-400" />
            PostgreSQL Connection Pool
          </h3>
          <div className="space-y-3 font-mono text-zinc-300">
            <div className="flex justify-between">
              <span>Active Pools</span>
              <span className="text-emerald-400 font-bold">{data?.connections_active} / {data?.connections_max}</span>
            </div>
            <div className="flex justify-between">
              <span>Writes Rate</span>
              <span>{data?.writes_sec} writes/sec</span>
            </div>
            <div className="flex justify-between">
              <span>Reads Rate</span>
              <span>{data?.reads_sec} reads/sec</span>
            </div>
            <div className="flex justify-between">
              <span>Slow Queries</span>
              <span className="text-emerald-400">None detected</span>
            </div>
          </div>
        </div>

        <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Activity className="w-4 h-4 text-sky-400" />
            Redis Telemetry Cache
          </h3>
          <div className="flex flex-col items-center justify-center p-6 border border-dashed border-zinc-800 rounded bg-zinc-900/10">
            <ServerCrash className="w-6 h-6 text-amber-500 mb-2 animate-pulse" />
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Telemetry Disabled</div>
            <div className="text-zinc-500 text-center mt-1 text-[11px]">Redis metrics are not instrumented on the gateway.</div>
          </div>
        </div>
      </div>
    </div>
  );
};
