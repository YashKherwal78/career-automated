import React from 'react';
import { AlertCircle, ShieldAlert } from 'lucide-react';

interface Props {
  data: any[];
}

export const Alerts: React.FC<Props> = ({ data }) => {
  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-emerald-400" />
          Active Platform Alerts
        </h3>
        <div className="space-y-3">
          {data.length > 0 ? (
            data.map((alert) => (
              <div key={alert.id} className="flex items-center gap-3 p-3 bg-red-950/20 border border-red-900/30 rounded text-red-400">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <div className="flex-1 font-semibold">{alert.title}</div>
                <span className="text-[10px] text-red-500 font-mono">{alert.time}</span>
              </div>
            ))
          ) : (
            <div className="text-center p-6 text-zinc-500">No active system alerts detected.</div>
          )}
        </div>
      </div>
    </div>
  );
};
