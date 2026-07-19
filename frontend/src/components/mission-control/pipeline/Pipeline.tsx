import React from 'react';
import { ArrowDown } from 'lucide-react';

interface Props {
  data: any;
}

export const Pipeline: React.FC<Props> = ({ data }) => {
  const stages = [
    { name: 'Seed Discovered', val: data?.raw_jobs_rate || 0, label: 'Raw Ingestion Rate' },
    { name: 'Normalized Jobs', val: data?.normalized_jobs_rate || 0, label: 'Standardization Rate' },
    { name: 'Canonical Jobs', val: data?.canonical_jobs_rate || 0, label: 'Merge & Deduplicate' },
    { name: 'Indexed Database', val: data?.indexed_jobs_rate || 0, label: 'Total Search Indexed' },
  ];

  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-6 shadow-lg space-y-8 flex flex-col items-center">
        <h3 className="text-sm font-semibold text-white self-start">Visual Ingestion Flow Engine</h3>
        {stages.map((stage, idx) => (
          <React.Fragment key={idx}>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 w-72 text-center shadow-lg space-y-1">
              <div className="font-bold text-white text-sm">{stage.name}</div>
              <div className="text-emerald-400 font-mono text-xs">{stage.val} jobs/sec</div>
              <div className="text-[10px] text-zinc-500">{stage.label}</div>
            </div>
            {idx < stages.length - 1 && (
              <ArrowDown className="w-5 h-5 text-zinc-700 animate-bounce" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
