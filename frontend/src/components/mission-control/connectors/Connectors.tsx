import React, { useState } from 'react';
import { Cable, TrendingUp, AlertTriangle } from 'lucide-react';

interface Props {
  data: any[];
}

export const Connectors: React.FC<Props> = ({ data }) => {
  const [sortField, setSortField] = useState('jobs');
  const [selectedConnector, setSelectedConnector] = useState<any>(null);

  const sortedData = [...data].sort((a, b) => {
    if (sortField === 'jobs') return b.jobs - a.jobs;
    return a.id.localeCompare(b.id);
  });

  return (
    <div className="space-y-6 font-sans text-xs text-zinc-400">
      {selectedConnector ? (
        <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Cable className="w-4 h-4 text-emerald-400" />
              {selectedConnector.name} Registry Telemetry
            </h3>
            <button onClick={() => setSelectedConnector(null)} className="text-zinc-500 hover:text-white transition-colors">
              Back to Overview
            </button>
          </div>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-zinc-900/40 p-4 border border-zinc-800 rounded">
              <span className="text-[10px] text-zinc-500 uppercase font-bold">Health Score</span>
              <div className="text-xl font-bold text-emerald-400 font-mono mt-1">{selectedConnector.health_score || 98}%</div>
            </div>
            <div className="bg-zinc-900/40 p-4 border border-zinc-800 rounded">
              <span className="text-[10px] text-zinc-500 uppercase font-bold">Jobs Ingested</span>
              <div className="text-xl font-bold text-white font-mono mt-1">{selectedConnector.jobs?.toLocaleString() || 0}</div>
            </div>
            <div className="bg-zinc-900/40 p-4 border border-zinc-800 rounded">
              <span className="text-[10px] text-zinc-500 uppercase font-bold">Status</span>
              <div className="text-xl font-bold text-emerald-400 mt-1 uppercase text-xs tracking-wider">{selectedConnector.status}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="border border-zinc-800 bg-zinc-950/40 rounded-lg shadow-lg">
          <div className="p-4 border-b border-zinc-800 flex justify-between items-center">
            <h3 className="text-sm font-semibold text-white">Dynamic Connector Registry</h3>
            <div className="flex items-center gap-3">
              <span className="text-zinc-500">Sort:</span>
              <button
                onClick={() => setSortField('jobs')}
                className={`px-2.5 py-1 rounded transition-colors ${sortField === 'jobs' ? 'bg-zinc-800 text-white' : 'hover:bg-zinc-900'}`}
              >
                Ingested Jobs
              </button>
              <button
                onClick={() => setSortField('name')}
                className={`px-2.5 py-1 rounded transition-colors ${sortField === 'name' ? 'bg-zinc-800 text-white' : 'hover:bg-zinc-900'}`}
              >
                Alpha Name
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-800 text-[10px] uppercase font-bold text-zinc-500">
                  <th className="p-4">Name</th>
                  <th className="p-4">Provider ID</th>
                  <th className="p-4">Jobs Found</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Details</th>
                </tr>
              </thead>
              <tbody>
                {sortedData.map((connector) => (
                  <tr key={connector.id} className="border-b border-zinc-900 hover:bg-zinc-900/10 transition-colors">
                    <td className="p-4 font-semibold text-white">{connector.name}</td>
                    <td className="p-4 font-mono">{connector.provider}</td>
                    <td className="p-4 font-mono">{connector.jobs?.toLocaleString() || 0}</td>
                    <td className="p-4">
                      <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold uppercase text-[10px]">
                        {connector.status}
                      </span>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => setSelectedConnector(connector)}
                        className="text-emerald-400 hover:underline"
                      >
                        Drilldown
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
