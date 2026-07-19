import React from 'react';
import { GitCommit, Clock } from 'lucide-react';

interface Props {
  data: any;
}

export const Deployments: React.FC<Props> = ({ data }) => {
  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-emerald-400" />
          Active Build Deployments
        </h3>
        <div className="space-y-2 font-mono text-zinc-300">
          <div className="flex justify-between">
            <span>Commit Commit</span>
            <span className="text-emerald-400 font-bold">{data?.git_commit}</span>
          </div>
          <div className="flex justify-between">
            <span>Commit Branch</span>
            <span>{data?.branch}</span>
          </div>
          <div className="flex justify-between">
            <span>Target Environment</span>
            <span>{data?.environment}</span>
          </div>
          <div className="flex justify-between">
            <span>Gateway Uptime</span>
            <span>{data?.uptime_days} days</span>
          </div>
        </div>
      </div>
    </div>
  );
};
