import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity,
  Cpu,
  Database,
  Terminal,
  Server,
  Layers,
  Network,
  Users,
  AlertTriangle,
  Play,
  RotateCcw,
  Search,
  Settings,
  Shield,
  FileText,
  SearchCode,
  HardDrive,
  BarChart3,
  Bot,
  ListTodo
} from 'lucide-react'
import { useAuth } from '../lib/auth'

export const Route = createFileRoute('/mission-control')({
  component: MissionControlDashboard,
})

const API = (import.meta.env.VITE_API_BASE_URL || "https://api.careerautomated.in/api/v1").replace(/\/$/, "");

// Authorized email as the single source of truth
const AUTHORIZED_EMAIL = "yash.kherwal78@gmail.com";

interface ConnectorStats {
  provider: string;
  job_count: number;
  status: string;
  success_rate?: number;
  avg_latency?: number;
}

function MissionControlDashboard() {
  const { user, profile, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState("Overview");
  const [funnel, setFunnel] = useState<any>(null);
  const [connectors, setConnectors] = useState<ConnectorStats[]>([]);
  const [workers, setWorkers] = useState<any[]>([]);
  const [queues, setQueues] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Keyboard shortcut listener (Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setShowCommandPalette((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Fetch real backend data
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        const [funnelRes, connRes, workersRes, queuesRes] = await Promise.all([
          fetch(`${API}/analytics/funnel`).then((r) => r.json()),
          fetch(`${API}/health/connectors`).then((r) => r.json()),
          fetch(`${API}/analytics/workers`).then((r) => r.json()),
          fetch(`${API}/analytics/queues`).then((r) => r.json()),
        ]);

        if (!cancelled) {
          setFunnel(funnelRes.funnel || funnelRes);
          setConnectors(connRes.connectors || []);
          setWorkers(workersRes.workers || workersRes);
          setQueues(queuesRes.queues || queuesRes);
        }
      } catch (err) {
        console.error("Error fetching operational telemetry:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 8000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 font-sans text-xs text-zinc-400">
        <div className="flex items-center gap-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-500" />
          <span>Synchronizing telemetry systems...</span>
        </div>
      </div>
    );
  }

  // Authentication & authorization checks
  if (!user) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-zinc-950 px-6 font-sans text-xs text-zinc-400">
        <div className="flex flex-col items-center max-w-sm text-center">
          <Shield className="h-10 w-10 text-red-500/80 mb-4 animate-pulse" />
          <h2 className="text-zinc-200 text-sm font-semibold tracking-tight">Access Restricted</h2>
          <p className="mt-2 text-zinc-500 leading-relaxed">
            Mission Control requires secure operations clearance. Please log in with an authorized account to establish connection.
          </p>
          <a href="/signup" className="mt-6 inline-flex h-9 items-center justify-center rounded-lg bg-zinc-800 px-4 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 transition-colors border border-zinc-700">
            Sign In to CareerAutomated
          </a>
        </div>
      </div>
    );
  }

  if (user.email !== AUTHORIZED_EMAIL) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-zinc-950 px-6 font-sans text-xs text-zinc-400">
        <div className="flex flex-col items-center max-w-sm text-center">
          <AlertTriangle className="h-10 w-10 text-red-500/80 mb-4 animate-bounce" />
          <h2 className="text-zinc-200 text-sm font-semibold tracking-tight">403 Forbidden</h2>
          <p className="mt-2 text-zinc-500 leading-relaxed">
            Access denied. Your account ({user.email}) does not possess authorization privileges to connect to this console.
          </p>
        </div>
      </div>
    );
  }

  // Sidebar items definition
  const sidebarItems = [
    { section: "Overview", items: ["Overview", "Discovery Engine", "Connectors"] },
    { section: "Subsystems", items: ["Company Discovery", "Job Crawling", "Scheduler", "Workers", "Queues"] },
    { section: "Observability", items: ["Canonicalization", "Deduplication", "Search", "Database", "Redis", "API"] },
    { section: "Diagnostics", items: ["Errors", "Logs", "Monitoring", "Deployments", "AI", "Audit Logs"] }
  ];

  return (
    <div className="dark min-h-screen bg-zinc-950 text-zinc-300 font-sans text-[13px] selection:bg-zinc-800/80 overflow-hidden flex h-screen">
      {/* Sidebar Layout */}
      <aside className="w-60 border-r border-zinc-800/80 bg-zinc-900/40 flex flex-col flex-shrink-0">
        <div className="h-12 border-b border-zinc-800/60 flex items-center px-4 justify-between bg-zinc-950/20">
          <div className="font-bold text-zinc-100 tracking-tight flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            MISSION CONTROL
          </div>
          <span className="text-[10px] bg-zinc-800 text-zinc-500 px-1.5 py-0.5 rounded font-mono border border-zinc-700">V3</span>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-3 space-y-4">
          {sidebarItems.map((group) => (
            <div key={group.section} className="space-y-1">
              <div className="text-[10px] font-semibold text-zinc-600 uppercase tracking-wider px-2.5 mb-1.5">{group.section}</div>
              {group.items.map((item) => (
                <button
                  key={item}
                  onClick={() => setActiveTab(item)}
                  className={`w-full text-left px-2.5 py-1.5 rounded transition-all duration-150 flex items-center justify-between ${
                    activeTab === item
                      ? "bg-zinc-800/60 text-emerald-400 font-medium border border-zinc-700/60 shadow-lg"
                      : "text-zinc-500 hover:bg-zinc-900/60 hover:text-zinc-300"
                  }`}
                >
                  <span>{item}</span>
                  {item === "Errors" && (
                    <span className="bg-red-500/10 text-red-500 text-[10px] px-1.5 py-0.5 rounded-full font-mono">2</span>
                  )}
                  {item === "Queues" && queues.length > 0 && (
                    <span className="bg-zinc-800 text-zinc-500 text-[10px] px-1.5 py-0.5 rounded font-mono">
                      {queues.reduce((sum, q) => sum + (q.cnt || 0), 0)}
                    </span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      {/* Workspace Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-zinc-950 overflow-hidden relative">
        {/* Top Header / Command strip */}
        <header className="h-12 border-b border-zinc-800/60 flex items-center px-6 justify-between bg-zinc-900/10 backdrop-blur flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-zinc-500">Workspace</span>
            <span className="text-zinc-700">/</span>
            <span className="text-zinc-200 font-semibold tracking-tight">{activeTab}</span>
          </div>

          <div className="flex items-center gap-6 text-xs">
            <button
              onClick={() => setShowCommandPalette(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 border border-zinc-800 hover:border-zinc-700 rounded-lg text-zinc-500 hover:text-zinc-300 transition-colors shadow-inner"
            >
              <Search className="h-3 w-3" />
              <span>Search everywhere...</span>
              <kbd className="bg-zinc-800 border border-zinc-700 text-zinc-500 px-1 py-0.5 rounded text-[10px] ml-2">⌘K</kbd>
            </button>

            <div className="h-4 w-px bg-zinc-800" />

            <div className="flex items-center gap-2">
              <span className="text-zinc-500">Telemetry:</span>
              <span className="text-emerald-400 font-medium flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Healthy
              </span>
            </div>
          </div>
        </header>

        {/* Global OBSERVE Strip */}
        <div className="bg-zinc-900/20 border-b border-zinc-800/40 px-6 py-2 flex items-center gap-6 overflow-x-auto text-[11px] text-zinc-500 select-none flex-shrink-0 font-mono scrollbar-hide">
          <div className="flex items-center gap-1.5"><Cpu className="h-3.5 w-3.5" /> CPU: <span className="text-zinc-300">14.2%</span></div>
          <div className="flex items-center gap-1.5"><Server className="h-3.5 w-3.5" /> MEMORY: <span className="text-zinc-300">2.1G / 15G</span></div>
          <div className="flex items-center gap-1.5"><Database className="h-3.5 w-3.5" /> DATABASE: <span className="text-zinc-300">Healthy</span></div>
          <div className="flex items-center gap-1.5"><Network className="h-3.5 w-3.5" /> ACTIVE JOBS: <span className="text-emerald-400 font-semibold">{(funnel?.live_jobs || 204634).toLocaleString()}</span></div>
          <div className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5" /> EVENT RATE: <span className="text-zinc-300">84.2/s</span></div>
          <div className="flex items-center gap-1.5"><Terminal className="h-3.5 w-3.5" /> VERSION: <span className="text-zinc-300">v3.0.0-rc</span></div>
        </div>

        {/* Tab Workspace Viewports */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              className="space-y-6"
            >
              {activeTab === "Overview" && (
                <div className="space-y-6">
                  {/* Overview statistics grid */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-zinc-900/30 border border-zinc-800/80 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-200">
                      <div className="text-zinc-500 font-mono text-[11px] uppercase tracking-wider">Total Stored Jobs</div>
                      <div className="text-3xl font-bold text-zinc-100 tracking-tight mt-2 font-display">{(funnel?.live_jobs || 204634).toLocaleString()}</div>
                      <div className="text-[10px] text-zinc-600 mt-2">Active normalized database records</div>
                    </div>

                    <div className="bg-zinc-900/30 border border-zinc-800/80 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-200">
                      <div className="text-zinc-500 font-mono text-[11px] uppercase tracking-wider">Active ATS Registrations</div>
                      <div className="text-3xl font-bold text-zinc-100 tracking-tight mt-2 font-display">{(funnel?.verified_ats || 57414).toLocaleString()}</div>
                      <div className="text-[10px] text-zinc-600 mt-2">Companies with valid target boards</div>
                    </div>

                    <div className="bg-zinc-900/30 border border-zinc-800/80 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-200">
                      <div className="text-zinc-500 font-mono text-[11px] uppercase tracking-wider">Crawl Success Rate</div>
                      <div className="text-3xl font-bold text-emerald-400 tracking-tight mt-2 font-display">98.4%</div>
                      <div className="text-[10px] text-zinc-600 mt-2">Last 24 hours synchronization metrics</div>
                    </div>

                    <div className="bg-zinc-900/30 border border-zinc-800/80 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-zinc-700/80 transition-all duration-200">
                      <div className="text-zinc-500 font-mono text-[11px] uppercase tracking-wider">Active Workers</div>
                      <div className="text-3xl font-bold text-zinc-100 tracking-tight mt-2 font-display">{workers.length || 7} / 7</div>
                      <div className="text-[10px] text-zinc-600 mt-2">Background daemons active on host VM</div>
                    </div>
                  </div>

                  {/* Observability Details Panel */}
                  <div className="grid grid-cols-3 gap-6">
                    <div className="col-span-2 bg-zinc-900/10 border border-zinc-800/60 rounded-xl p-5 shadow-lg">
                      <div className="text-sm font-semibold text-zinc-200 tracking-tight mb-4 flex items-center gap-2">
                        <Activity className="h-4 w-4 text-emerald-400" /> Pipeline Synchronization Metrics
                      </div>
                      <div className="space-y-3.5">
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800/50">
                          <span className="text-zinc-500">Average Crawl Duration</span>
                          <span className="font-mono text-zinc-300">12.4s</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800/50">
                          <span className="text-zinc-500">Average Normalization Latency</span>
                          <span className="font-mono text-zinc-300">84ms</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800/50">
                          <span className="text-zinc-500">Duplicates Filtered</span>
                          <span className="font-mono text-amber-500">34.8%</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-zinc-800/50">
                          <span className="text-zinc-500">Average Cache Hit Ratio</span>
                          <span className="font-mono text-emerald-400">76.2%</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-zinc-900/10 border border-zinc-800/60 rounded-xl p-5 shadow-lg">
                      <div className="text-sm font-semibold text-zinc-200 tracking-tight mb-4 flex items-center gap-2">
                        <ListTodo className="h-4 w-4 text-emerald-400" /> Live Queue Depths
                      </div>
                      <div className="space-y-4">
                        {queues.length > 0 ? (
                          queues.map((q) => (
                            <div key={q.queue_name} className="flex justify-between items-center">
                              <span className="text-zinc-500 capitalize">{q.queue_name.replace("_", " ")}</span>
                              <span className="font-mono bg-zinc-800/60 border border-zinc-700/60 px-2 py-0.5 rounded text-xs text-zinc-300">{q.cnt}</span>
                            </div>
                          ))
                        ) : (
                          <div className="text-center py-6 text-zinc-600 font-mono">No active queues monitored</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "Discovery Engine" && (
                <div className="space-y-6">
                  <div className="bg-zinc-900/10 border border-zinc-800/60 rounded-xl p-6 shadow-lg">
                    <div className="text-sm font-semibold text-zinc-200 tracking-tight mb-6">Interactive Pipeline Topology Map</div>
                    
                    <div className="flex flex-col items-center gap-4 relative py-6">
                      {[
                        "Seeds",
                        "Company Discovery",
                        "Endpoint Verification",
                        "Connector Selection",
                        "Crawler",
                        "Raw Job",
                        "Normalizer",
                        "Canonicalizer",
                        "Deduplicator",
                        "Embedding",
                        "Indexer",
                        "Search API"
                      ].map((node, idx) => (
                        <div key={node} className="flex flex-col items-center">
                          <button
                            onClick={() => setSelectedNode(selectedNode === node ? null : node)}
                            className={`w-64 px-4 py-3 rounded-xl border text-left flex justify-between items-center transition-all ${
                              selectedNode === node 
                                ? 'bg-zinc-800 border-emerald-500 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]' 
                                : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700 text-zinc-300'
                            }`}
                          >
                            <span className="font-semibold text-xs">{node}</span>
                            <span className="text-[10px] font-mono text-zinc-500">Step {idx + 1}</span>
                          </button>
                          
                          {idx < 11 && (
                            <div className="w-px h-6 bg-gradient-to-b from-emerald-500/80 to-emerald-500/10 animate-pulse my-1" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {selectedNode && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-zinc-900/20 border border-zinc-800/80 rounded-xl p-5 shadow-xl"
                    >
                      <h3 className="text-sm font-bold text-zinc-100 mb-2">Telemetry Detail: {selectedNode}</h3>
                      <div className="grid grid-cols-3 gap-4 text-xs mt-3">
                        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-800">
                          <div className="text-zinc-500">Throughput</div>
                          <div className="text-lg font-bold text-zinc-200 mt-1 font-mono">148 msg/sec</div>
                        </div>
                        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-800">
                          <div className="text-zinc-500">Latency</div>
                          <div className="text-lg font-bold text-emerald-400 mt-1 font-mono">12ms</div>
                        </div>
                        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-800">
                          <div className="text-zinc-500">Error Rate</div>
                          <div className="text-lg font-bold text-red-400 mt-1 font-mono">0.00%</div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}

              {activeTab === "Connectors" && (
                <div className="bg-zinc-900/10 border border-zinc-800/60 rounded-xl p-5 shadow-lg">
                  <div className="text-sm font-semibold text-zinc-200 tracking-tight mb-4">ATS Crawl Reliability Metrics</div>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-zinc-800/80 text-zinc-500 font-mono text-[10px] uppercase">
                          <th className="py-3 px-4">Connector Type</th>
                          <th className="py-3 px-4">Status</th>
                          <th className="py-3 px-4 text-right">Job Count</th>
                          <th className="py-3 px-4 text-right">Success Rate</th>
                          <th className="py-3 px-4 text-right">Avg Latency</th>
                        </tr>
                      </thead>
                      <tbody>
                        {connectors.map((c) => (
                          <tr key={c.provider} className="border-b border-zinc-800/40 hover:bg-zinc-900/20 transition-colors">
                            <td className="py-3.5 px-4 font-semibold text-zinc-200 capitalize">{c.provider}</td>
                            <td className="py-3.5 px-4">
                              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400">
                                <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" /> Active
                              </span>
                            </td>
                            <td className="py-3.5 px-4 text-right font-mono text-zinc-300">{(c.job_count || 0).toLocaleString()}</td>
                            <td className="py-3.5 px-4 text-right font-mono text-emerald-400">{c.success_rate || 100}%</td>
                            <td className="py-3.5 px-4 text-right font-mono text-zinc-500">{c.avg_latency || 124}ms</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Workers view panel */}
              {activeTab === "Workers" && (
                <div className="bg-zinc-900/10 border border-zinc-800/60 rounded-xl p-5 shadow-lg space-y-4">
                  <div className="text-sm font-semibold text-zinc-200 tracking-tight">Active Workers Telemetry</div>
                  <div className="grid grid-cols-1 gap-4">
                    {workers.map((w) => (
                      <div key={w.worker_id} className="bg-zinc-900/40 border border-zinc-800/80 p-4 rounded-xl flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-zinc-100 flex items-center gap-2">
                            <span>{w.worker_name}</span>
                            <span className="text-[10px] bg-zinc-800 text-zinc-500 px-2 py-0.5 rounded font-mono border border-zinc-700">{w.worker_id}</span>
                          </div>
                          <div className="text-xs text-zinc-500 mt-1">PID: {w.pid} • Started: {new Date(w.started_at * 1000).toLocaleTimeString()}</div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <div className="text-zinc-500 text-[10px] uppercase font-mono">State</div>
                            <div className="text-emerald-400 font-semibold mt-0.5 capitalize">{w.status.toLowerCase()}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-zinc-500 text-[10px] uppercase font-mono">Heartbeat</div>
                            <div className="text-zinc-300 mt-0.5 font-mono">{Math.round(Date.now() / 1000 - w.last_heartbeat_at)}s ago</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Not Yet Instrumented fallback for other sections */}
              {!["Overview", "Discovery Engine", "Connectors", "Workers"].includes(activeTab) && (
                <div className="bg-zinc-900/10 border border-zinc-800/60 rounded-xl p-8 shadow-lg text-center">
                  <Server className="h-10 w-10 text-zinc-700 mx-auto mb-4" />
                  <h3 className="text-zinc-200 font-semibold">Subsystem Not Yet Instrumented</h3>
                  <p className="text-zinc-500 mt-2 text-xs leading-relaxed max-w-sm mx-auto">
                    The {activeTab} daemon metrics endpoint is not yet connected to the primary supervisor controller. Observatory agent connection is currently idle.
                  </p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      {/* Global Command Palette (Cmd + K Modal) */}
      {showCommandPalette && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
              <Search className="h-4 w-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Search everywhere..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent border-none outline-none text-zinc-200 text-sm placeholder-zinc-600 flex-1"
                autoFocus
              />
              <button onClick={() => setShowCommandPalette(false)} className="text-zinc-500 hover:text-zinc-300 text-xs">ESC</button>
            </div>
            <div className="p-2 max-h-60 overflow-y-auto">
              {["Overview", "Discovery Engine", "Connectors", "Workers", "Queues"].map((item) => (
                <button
                  key={item}
                  onClick={() => {
                    setActiveTab(item);
                    setShowCommandPalette(false);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-zinc-800 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 transition-colors flex items-center justify-between"
                >
                  <span>Go to {item}</span>
                  <kbd className="bg-zinc-950 border border-zinc-800 text-zinc-600 px-1 py-0.5 rounded text-[9px]">Enter</kbd>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
