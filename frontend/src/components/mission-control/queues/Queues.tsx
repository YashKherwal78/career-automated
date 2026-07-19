import React from 'react';

interface Props {
  data: any;
}

export const Queues: React.FC<Props> = ({ data }) => {
  const getQueueBlocks = (depth: number) => {
    const total = 8;
    const filled = Math.min(Math.ceil((depth / 100) * total), total);
    return '■'.repeat(filled) + '□'.repeat(total - filled);
  };

  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-5 shadow-lg space-y-6">
        <h3 className="text-sm font-semibold text-white">Live Queue Visualization</h3>
        <div className="space-y-4">
          {Object.entries(data || {}).map(([key, val]: [string, any]) => (
            <div key={key} className="flex items-center justify-between border-b border-zinc-900 pb-3">
              <div>
                <h4 className="font-semibold text-white capitalize">{key.replace('_', ' ')}</h4>
                <span className="text-[10px] text-zinc-500">Status: {val.status}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-mono font-bold text-emerald-400">{getQueueBlocks(val.depth)}</span>
                <span className="font-mono text-zinc-300 text-sm">{val.depth} msg</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
