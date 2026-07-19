import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import { useAuth } from '../lib/auth';
import { Sidebar } from '../components/mission-control/layout/Sidebar';
import { Overview } from '../components/mission-control/overview/Overview';
import { Connectors } from '../components/mission-control/connectors/Connectors';
import { Workers } from '../components/mission-control/workers/Workers';
import { Queues } from '../components/mission-control/queues/Queues';
import { Pipeline } from '../components/mission-control/pipeline/Pipeline';
import { Tracing } from '../components/mission-control/tracing/Tracing';
import { Infrastructure } from '../components/mission-control/infrastructure/Infrastructure';
import { AiOps } from '../components/mission-control/ai/AiOps';
import { Alerts } from '../components/mission-control/alerts/Alerts';
import { Deployments } from '../components/mission-control/deployments/Deployments';
import { LogViewer } from '../components/mission-control/log-viewer/LogViewer';
import { ShieldAlert } from 'lucide-react';

export const Route = createFileRoute('/mission-control')({
  component: MissionControlWorkspace,
});

const API = (import.meta.env.VITE_API_BASE_URL || "https://api.careerautomated.in/api/v1").replace(/\/$/, "");

// Configurable Operator Allowlist
const ALLOWED_OPERATORS = ["yash.kherwal78@gmail.com"];

function MissionControlWorkspace() {
  const { user, profile, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [telemetry, setTelemetry] = useState<any>({
    overview: null,
    connectors: [],
    workers: [],
    queues: {},
    pipeline: null,
    infrastructure: null,
    alerts: [],
    deployments: null,
  });
  const [systemStatus, setSystemStatus] = useState('ONLINE');

  // Load telemetry data from backend endpoints
  useEffect(() => {
    if (!user || (profile && !ALLOWED_OPERATORS.includes(profile.email || user.email || ''))) return;

    let active = true;
    const fetchTelemetry = async () => {
      try {
        const headers = { 'Content-Type': 'application/json' };
        
        // Dynamic requests
        const [overviewRes, connectorsRes, workersRes, queuesRes, pipelineRes, dbRes, alertsRes, deployRes] = await Promise.all([
          fetch(`${API}/mission-control/overview`, { headers }),
          fetch(`${API}/mission-control/connectors`, { headers }),
          fetch(`${API}/mission-control/workers`, { headers }),
          fetch(`${API}/mission-control/queues`, { headers }),
          fetch(`${API}/mission-control/pipeline`, { headers }),
          fetch(`${API}/mission-control/database`, { headers }),
          fetch(`${API}/mission-control/alerts`, { headers }),
          fetch(`${API}/mission-control/deployments`, { headers }),
        ]);

        if (!active) return;

        const data: any = {};
        if (overviewRes.ok) data.overview = await overviewRes.json();
        if (connectorsRes.ok) data.connectors = await connectorsRes.json();
        if (workersRes.ok) data.workers = await workersRes.json();
        if (queuesRes.ok) data.queues = await queuesRes.json();
        if (pipelineRes.ok) data.pipeline = await pipelineRes.json();
        if (dbRes.ok) data.infrastructure = await dbRes.json();
        if (alertsRes.ok) data.alerts = await alertsRes.json();
        if (deployRes.ok) data.deployments = await deployRes.json();

        setTelemetry(data);
        setSystemStatus('ONLINE');
      } catch (err) {
        console.error('Failed to stream telemetry metrics:', err);
        if (active) setSystemStatus('DISCONNECTED');
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 8000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [user, profile]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-400 font-mono text-xs">
        <span className="animate-pulse">Loading telemetry secure key validation...</span>
      </div>
    );
  }

  // Enforce Server-Side Allowed Operators Allowlist
  const operatorEmail = profile?.email || user?.email || '';
  const isAuthorized = ALLOWED_OPERATORS.includes(operatorEmail);

  if (!user || !isAuthorized) {
    return (
      <div className="flex flex-col min-h-screen items-center justify-center bg-zinc-950 text-zinc-400 font-sans p-6 text-center select-none">
        <ShieldAlert className="w-12 h-12 text-red-500 mb-4 animate-bounce" />
        <h1 className="text-lg font-bold text-white mb-2">403 Forbidden</h1>
        <p className="text-xs text-zinc-500 max-w-sm">
          You are not authorized to view the telemetry control panel. Operator permission is required.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950 text-zinc-300 font-sans">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
      />

      {/* Main Panel Workspace */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-14 border-b border-zinc-800 flex items-center px-8 justify-between bg-zinc-950/40 backdrop-blur-sm z-10 select-none">
          <div className="flex items-center gap-3">
            <h1 className="text-white font-semibold uppercase tracking-wider text-xs">
              System Ingestion Control
            </h1>
            <span className="text-zinc-600 text-[10px] uppercase font-bold">
              / {activeTab.replace('_', ' ')}
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-zinc-500 font-mono text-[10px]">Environment:</span>
              <span className="text-zinc-300 font-semibold text-[10px] uppercase px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800">
                {telemetry.deployments?.environment || 'Production'}
              </span>
            </div>
          </div>
        </header>

        {/* Workspace Panels */}
        <main className="flex-1 overflow-y-auto p-8 bg-zinc-950">
          {activeTab === 'overview' && (
            <Overview data={telemetry.overview} />
          )}
          {activeTab === 'connectors' && (
            <Connectors data={telemetry.connectors} />
          )}
          {activeTab === 'workers' && (
            <Workers data={telemetry.workers} />
          )}
          {activeTab === 'queues' && (
            <Queues data={telemetry.queues} />
          )}
          {activeTab === 'pipeline' && (
            <Pipeline data={telemetry.pipeline} />
          )}
          {activeTab === 'tracing' && (
            <Tracing />
          )}
          {activeTab === 'infrastructure' && (
            <Infrastructure data={telemetry.infrastructure} />
          )}
          {activeTab === 'ai' && (
            <AiOps />
          )}
          {activeTab === 'alerts' && (
            <Alerts data={telemetry.alerts} />
          )}
          {activeTab === 'deployments' && (
            <Deployments data={telemetry.deployments} />
          )}
          {activeTab === 'logs' && (
            <LogViewer />
          )}
        </main>
      </div>
    </div>
  );
}
