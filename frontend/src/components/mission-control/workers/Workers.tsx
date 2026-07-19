import React from 'react';
import { Cpu, CheckCircle } from 'lucide-react';

interface Props {
  data: any[];
}

export const Workers: React.FC<Props> = ({ data }) => {
  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="grid grid-cols-3 gap-4">
        {data.map((worker) => (
          <div key={worker.id} className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-sm font-semibold text-white">{worker.name}</h4>
                <span className="text-[10px] text-zinc-500 font-mono">PID {worker.pid}</span>
              </div>
              <Cpu className="w-5 h-5 text-emerald-400" />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Task</span>
                <span className="font-mono text-zinc-300 truncate max-w-[150px]">{worker.current_task || 'IDLE'}</span>
              </div>
              <div className="flex justify-between">
                <span>CPU Load</span>
                <span className="font-mono text-zinc-300">{worker.cpu}%</span>
              </div>
              <div className="flex justify-between">
                <span>Memory</span>
                <span className="font-mono text-zinc-300">{worker.ram} MB</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
