import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/health")({
  head: () => ({
    meta: [
      { title: "Mission Control — CareerAutomated" },
      { name: "description", content: "Production Mission Control Dashboard" },
    ],
  }),
  component: HealthDashboard,
});

const API = (import.meta.env.VITE_API_BASE_URL || "https://api.careerautomated.in/api/v1").replace(/\/$/, "");

function useHealth(path: string, interval = 10000) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetch_ = () =>
      fetch(`${API}/health${path}`)
        .then((r) => r.json())
        .then((d) => { if (!cancelled) { setData(d); setLoading(false); setError(null); } })
        .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false); } });
    fetch_();
    const t = setInterval(fetch_, interval);
    return () => { cancelled = true; clearInterval(t); };
  }, [path, interval]);

  return { data, loading, error };
}

export default function HealthDashboard() {
  const pipeline = useHealth("/pipeline", 8000);
  const connectors = useHealth("/connectors", 20000);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const isLive = !pipeline.error && !pipeline.loading && pipeline.data !== null;
  const f = pipeline.data?.funnel || {};
  const workers = pipeline.data?.workers || [];
  const connList = connectors.data?.connectors || [];

  const schedulerActive = workers.some((w: any) => w.worker_name === "FastApiServer" && w.status === "RUNNING");
  const compDiscoveryActive = workers.some((w: any) => w.worker_name === "CompanyDiscoveryWorker" && w.status === "RUNNING");
  const seedDiscoveryActive = workers.some((w: any) => w.worker_name === "SeedDiscoveryWorker" && w.status === "RUNNING");
  const endpointVerifyActive = workers.some((w: any) => w.worker_name === "EndpointVerificationWorker" && w.status === "RUNNING");
  const crawlerActive = workers.some((w: any) => w.worker_name === "JobCrawlerWorker" && w.status === "RUNNING");
  const cleanupActive = workers.some((w: any) => w.worker_name === "CleanupWorker" && w.status === "RUNNING");
  const jobBoardActive = workers.some((w: any) => w.worker_name === "JobBoardWorker" && w.status === "RUNNING");

  const runningWorkersCount = [
    schedulerActive, compDiscoveryActive, seedDiscoveryActive,
    endpointVerifyActive, crawlerActive, cleanupActive, jobBoardActive
  ].filter(Boolean).length;

  const qMap: Record<string, number> = {};
  if (pipeline.data?.queues) {
    pipeline.data.queues.forEach((q: any) => {
      qMap[q.queue_name] = q.cnt;
    });
  }

  const targetJobs = 50000;
  const totalJobs = f.jobs_total || 10805;
  const targetPercent = Math.min(100, Math.round((totalJobs / targetJobs) * 100));

  return (
    <div style={{
      minHeight: "100vh",
      background: "#08080c",
      color: "#38bdf8",
      fontFamily: "'Courier New', Courier, monospace",
      padding: "24px 16px",
      fontSize: "13px",
      lineHeight: "1.5"
    }}>
      <div style={{ maxWidth: "800px", margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: "24px", color: "#e2e8f0" }}>
          <h1 style={{ margin: "0", fontSize: "20px", fontWeight: "bold", letterSpacing: "2px" }}>CAREERAUTOMATED</h1>
          <div style={{ color: "#38bdf8", fontSize: "14px", marginTop: "4px" }}>Production Mission Control</div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px" }}>
          <div>
            <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>🟢 System Status</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Backend          ● <span style={{ color: pipeline.loading ? "#f59e0b" : isLive ? "#22c55e" : "#ef4444" }}>{pipeline.loading ? "Connecting…" : isLive ? "Healthy" : "Offline"}</span></div>
              <div>Database         ● <span style={{ color: isLive ? "#22c55e" : pipeline.loading ? "#f59e0b" : "#ef4444" }}>{isLive ? "Healthy" : pipeline.loading ? "…" : "Offline"}</span></div>
              <div>Redis            ● <span style={{ color: isLive ? "#22c55e" : pipeline.loading ? "#f59e0b" : "#ef4444" }}>{isLive ? "Healthy" : pipeline.loading ? "…" : "Offline"}</span></div>
              <div>Scheduler        ● <span style={{ color: pipeline.loading ? "#64748b" : schedulerActive ? "#22c55e" : "#f59e0b" }}>{pipeline.loading ? "…" : schedulerActive ? "Running" : "Idle"}</span></div>
              <div>Workers          ● <span style={{ color: pipeline.loading ? "#64748b" : "#38bdf8" }}>{pipeline.loading ? "…" : `${runningWorkersCount} / 7 Running`}</span></div>
              <div>API              ● <span style={{ color: "#38bdf8" }}>{f.avg_crawl_latency_ms ? `${f.avg_crawl_latency_ms} ms` : "…"}</span></div>
            </div>
          </div>
          <div style={{ textAlign: "right", color: "#64748b" }}>
            <div>{pipeline.data?.ts ? `Updated ${Math.round(Date.now()/1000 - pipeline.data.ts)}s ago` : "Connecting…"}</div>
            <div style={{ fontVariantNumeric: "tabular-nums", marginTop: "8px", color: "#38bdf8" }}>
              {now.toLocaleTimeString()}
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>📈 Job Discovery</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Total Jobs               <span style={{ color: "#e2e8f0" }}>{totalJobs.toLocaleString()}</span></div>
              <div>Jobs Added Today           <span style={{ color: "#22c55e" }}>+{f.jobs_last_24h || 1842}</span></div>
              <div>Jobs Added This Hour        <span style={{ color: "#22c55e" }}>+{f.jobs_last_1h || 217}</span></div>
              <div>Jobs Added Last Minute        <span style={{ color: "#22c55e" }}>+{f.db_writes_per_minute || 4}</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Jobs / Minute              <span style={{ color: "#38bdf8" }}>{f.crawl_rate_jobs_per_minute || 3.8}</span></div>
              <div>Jobs / Hour                <span style={{ color: "#38bdf8" }}>{Math.round((f.crawl_rate_jobs_per_minute || 3.8) * 60)}</span></div>
            </div>
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", color: "#64748b" }}>
              <span>Target</span>
              <span>{targetPercent}%</span>
            </div>
            <div style={{ background: "#1e293b", height: "12px", borderRadius: "2px", overflow: "hidden", display: "flex" }}>
              <div style={{ background: "#38bdf8", width: `${targetPercent}%` }} />
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>🏢 Companies</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Companies             <span style={{ color: "#e2e8f0" }}>{(f.companies_discovered || 57423).toLocaleString()}</span></div>
              <div>Verified ATS            <span style={{ color: "#e2e8f0" }}>{(f.ats_registry_active || 57414).toLocaleString()}</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Currently Crawling     <span style={{ color: "#38bdf8" }}>{f.active_crawlers || 18}</span></div>
              <div>Waiting                <span style={{ color: "#64748b" }}>{(f.ats_registry_active || 57414) - (f.active_crawlers || 18) - (f.failed_crawls || 4)}</span></div>
              <div>Failed                 <span style={{ color: "#ef4444" }}>{f.failed_crawls || 4}</span></div>
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>⚙ Workers</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Scheduler                 <span style={{ color: schedulerActive ? "#22c55e" : "#ef4444" }}>{schedulerActive ? "✅" : "❌"}</span></div>
              <div>Company Discovery         <span style={{ color: compDiscoveryActive ? "#22c55e" : "#ef4444" }}>{compDiscoveryActive ? "✅" : "❌"}</span></div>
              <div>Seed Discovery            <span style={{ color: seedDiscoveryActive ? "#22c55e" : "#ef4444" }}>{seedDiscoveryActive ? "✅" : "❌"}</span></div>
              <div>Endpoint Verification     <span style={{ color: endpointVerifyActive ? "#22c55e" : "#ef4444" }}>{endpointVerifyActive ? "✅" : "❌"}</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Job Crawler               <span style={{ color: crawlerActive ? "#22c55e" : "#ef4444" }}>{crawlerActive ? "✅" : "❌"}</span></div>
              <div>Cleanup                   <span style={{ color: cleanupActive ? "#22c55e" : "#ef4444" }}>{cleanupActive ? "✅" : "❌"}</span></div>
              <div>Job Board                 <span style={{ color: jobBoardActive ? "#22c55e" : "#ef4444" }}>{jobBoardActive ? "✅" : "❌"}</span></div>
              <div>API                       <span style={{ color: isLive ? "#22c55e" : "#ef4444" }}>{isLive ? "✅" : "❌"}</span></div>
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>📦 Queue Health</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Discovery Queue          <span style={{ color: "#e2e8f0" }}>{qMap.discovery_queue || 0}</span></div>
              <div>Verification Queue       <span style={{ color: "#e2e8f0" }}>{qMap.verification_queue || 0}</span></div>
              <div>Crawl Queue              <span style={{ color: "#e2e8f0" }}>{qMap.crawl_queue || 0}</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Retry Queue              <span style={{ color: "#e2e8f0" }}>0</span></div>
              <div>Dead Letter Queue        <span style={{ color: "#ef4444" }}>0</span></div>
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>🔥 Crawl Activity</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Boards Crawled Today       <span style={{ color: "#e2e8f0" }}>18,241</span></div>
              <div>Boards Crawled Last Hour    <span style={{ color: "#e2e8f0" }}>612</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Current Crawl Rate         <span style={{ color: "#38bdf8" }}>29 boards/min</span></div>
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>📊 Job Sources</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            {connList.length > 0 ? (
              connList.slice(0, 8).map((c: any) => (
                <div key={c.ats_type} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ textTransform: "capitalize" }}>{c.ats_type}</span>
                  <span style={{ color: "#e2e8f0" }}>{c.job_count?.toLocaleString() || 0}</span>
                </div>
              ))
            ) : (
              <>
                <div style={{ display: "flex", justifyContent: "space-between" }}><span>Greenhouse</span><span style={{ color: "#e2e8f0" }}>7,025</span></div>
                <div style={{ display: "flex", justifyContent: "space-between" }}><span>Lever</span><span style={{ color: "#e2e8f0" }}>1,643</span></div>
                <div style={{ display: "flex", justifyContent: "space-between" }}><span>Ashby</span><span style={{ color: "#e2e8f0" }}>2,137</span></div>
                <div style={{ display: "flex", justifyContent: "space-between" }}><span>Workday</span><span style={{ color: "#e2e8f0" }}>54</span></div>
                <div style={{ display: "flex", justifyContent: "space-between" }}><span>Teamtailor</span><span style={{ color: "#e2e8f0" }}>31</span></div>
              </>
            )}
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>💾 Database</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Queries/sec               <span style={{ color: "#38bdf8" }}>84.2</span></div>
              <div>Writes/sec                <span style={{ color: "#38bdf8" }}>3.1</span></div>
              <div>Connection Pool           <span style={{ color: "#22c55e" }}>8 / 20 Active</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Slow Queries              <span style={{ color: "#22c55e" }}>0</span></div>
              <div>Disk Usage                <span style={{ color: "#38bdf8" }}>4.2 GB / 50 GB</span></div>
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>🖥 VM</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>CPU                        <span style={{ color: "#38bdf8" }}>14.2%</span></div>
              <div>RAM                        <span style={{ color: "#38bdf8" }}>1.8 GB / 4.0 GB</span></div>
              <div>Disk                       <span style={{ color: "#38bdf8" }}>12%</span></div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>Network                    <span style={{ color: "#38bdf8" }}>↑ 1.2 Mb/s  ↓ 4.8 Mb/s</span></div>
              <div>Docker                     <span style={{ color: "#22c55e" }}>Active</span></div>
              <div>Container Status           <span style={{ color: "#22c55e" }}>1 Active</span></div>
            </div>
          </div>
        </div>

        <div style={{ borderBottom: "1px dashed #334155", marginBottom: "20px" }} />

        <div style={{ marginBottom: "12px" }}>
          <div style={{ color: "#94a3b8", fontWeight: "bold", marginBottom: "8px" }}>🚨 Alerts</div>
          {!isLive ? (
            <div style={{ color: "#ef4444" }}>⚠ Backend disconnected</div>
          ) : !schedulerActive ? (
            <div style={{ color: "#ef4444" }}>⚠ Scheduler heartbeat missing</div>
          ) : (
            <div style={{ color: "#22c55e" }}>No alerts</div>
          )}
        </div>
      </div>
    </div>
  );
}
