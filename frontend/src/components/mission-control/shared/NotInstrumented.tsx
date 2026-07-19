import React from 'react';
import { ShieldAlert } from 'lucide-react';

interface Props {
  title: string;
  description: string;
}

export const NotInstrumented: React.FC<Props> = ({ title, description }) => {
  return (
    <div className="flex flex-col items-center justify-center p-6 border border-dashed border-zinc-800 rounded-lg bg-zinc-950/40 text-center select-none min-h-[160px]">
      <ShieldAlert className="w-8 h-8 text-amber-500/80 mb-2 animate-pulse" />
      <h4 className="text-sm font-semibold text-zinc-300 mb-1">{title}</h4>
      <p className="text-xs text-zinc-500 max-w-sm">{description} (Not Yet Instrumented)</p>
    </div>
  );
};
