import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/health")({
  head: () => ({
    meta: [
      { title: "System Health — CareerAutomated" },
      { name: "description", content: "Real-time pipeline observability dashboard." },
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

function Metric({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16,
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: 4,
    }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || "#fff", letterSpacing: -1 }}>{value}</div>
      <div style={{ fontSize: 13, color: "#9ca3af", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "#6b7280" }}>{sub}</div>}
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: ok ? "#22c55e" : "#ef4444",
      boxShadow: ok ? "0 0 8px #22c55e" : "0 0 8px #ef4444",
      marginRight: 8,
      flexShrink: 0,
    }} />
  );
}

function PipelineFunnel({ data }: { data: any }) {
  const f = data?.funnel || {};
  const steps = [
    { label: "Companies Discovered", value: f.companies_discovered, color: "#818cf8" },
    { label: "In ATS Registry", value: f.ats_registry_total, color: "#a78bfa" },
    { label: "Active (Verified)", value: f.ats_registry_active, color: "#34d399" },
    { label: "Successfully Crawled", value: f.companies_crawled, color: "#60a5fa" },
    { label: "Total Jobs", value: f.jobs_total, color: "#f59e0b" },
    { label: "Active Jobs", value: f.jobs_active, color: "#22c55e" },
    { label: "Jobs (24h)", value: f.jobs_last_24h, color: "#fb7185" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
      {steps.map((s) => (
        <Metric key={s.label} label={s.label} value={s.value ?? "—"} color={s.color} />
      ))}
    </div>
  );
}

function ConnectorTable({ data }: { data: any }) {
  const connectors = data?.connectors || [];
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
            {["ATS", "Companies", "Active", "Crawled", "Success %", "Avg Failures", "Jobs", "Avg Jobs/Co", "Last Crawl"].map((h) => (
              <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: "#9ca3af", fontWeight: 500, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {connectors.map((c: any) => {
            const pct = c.crawl_success_rate_pct;
            const color = pct >= 90 ? "#22c55e" : pct >= 60 ? "#f59e0b" : "#ef4444";
            return (
              <tr key={c.ats_type} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={{ padding: "10px 12px", fontWeight: 600, color: "#e2e8f0" }}>{c.ats_type}</td>
                <td style={{ padding: "10px 12px", color: "#cbd5e1" }}>{c.total_companies}</td>
                <td style={{ padding: "10px 12px", color: "#cbd5e1" }}>{c.active}</td>
                <td style={{ padding: "10px 12px", color: "#cbd5e1" }}>{c.crawled}</td>
                <td style={{ padding: "10px 12px", fontWeight: 700, color }}>{pct}%</td>
                <td style={{ padding: "10px 12px", color: c.avg_failures > 0 ? "#f87171" : "#6b7280" }}>{c.avg_failures}</td>
                <td style={{ padding: "10px 12px", color: "#cbd5e1" }}>{c.job_count?.toLocaleString()}</td>
                <td style={{ padding: "10px 12px", color: "#cbd5e1" }}>{c.avg_jobs_per_company}</td>
                <td style={{ padding: "10px 12px", color: "#6b7280", fontSize: 11 }}>
                  {c.most_recent_crawl ? new Date(c.most_recent_crawl * 1000).toLocaleString() : "Never"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CoverageTable({ data }: { data: any }) {
  const companies = data?.companies || [];
  const summary = data?.summary || {};
  return (
    <div>
      <div style={{ display: "flex", gap: 24, marginBottom: 20, flexWrap: "wrap" }}>
        <Metric label="Checked" value={summary.total_checked} />
        <Metric label="In Registry" value={summary.in_registry} color="#60a5fa" />
        <Metric label="Has Jobs" value={summary.has_jobs} color="#22c55e" />
        <Metric label="Coverage" value={`${summary.coverage_pct}%`} color={summary.coverage_pct >= 80 ? "#22c55e" : summary.coverage_pct >= 50 ? "#f59e0b" : "#ef4444"} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
        {companies.map((c: any) => (
          <div key={c.company} style={{
            display: "flex", alignItems: "center", gap: 10,
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10, padding: "10px 14px",
          }}>
            <span style={{ fontSize: 16 }}>{c.status}</span>
            <div>
              <div style={{ fontWeight: 600, color: "#e2e8f0", fontSize: 13, textTransform: "capitalize" }}>{c.company}</div>
              <div style={{ fontSize: 11, color: "#6b7280" }}>
                {c.ats_type ? `${c.ats_type} · ${c.job_count} jobs` : "Not tracked"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PerCompanyTable({ data }: { data: any }) {
  const companies = data?.per_company || [];
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
            {["Company", "ATS", "Jobs", "Last Crawl", "Failures", "Status"].map((h) => (
              <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: "#9ca3af", fontWeight: 500, fontSize: 11, textTransform: "uppercase" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {companies.map((c: any) => (
            <tr key={c.company_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
              <td style={{ padding: "10px 12px", fontWeight: 600, color: "#e2e8f0", textTransform: "capitalize" }}>{c.company_id}</td>
              <td style={{ padding: "10px 12px", color: "#a78bfa" }}>{c.ats_type || "—"}</td>
              <td style={{ padding: "10px 12px", color: "#34d399", fontWeight: 600 }}>{c.job_count?.toLocaleString()}</td>
              <td style={{ padding: "10px 12px", color: "#6b7280", fontSize: 11 }}>
                {c.last_successful_crawl ? new Date(c.last_successful_crawl * 1000).toLocaleString() : "Never"}
              </td>
              <td style={{ padding: "10px 12px", color: c.failure_count > 0 ? "#f87171" : "#6b7280" }}>{c.failure_count ?? 0}</td>
              <td style={{ padding: "10px 12px" }}>
                <span style={{
                  padding: "2px 8px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                  background: c.ats_status === "ACTIVE" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                  color: c.ats_status === "ACTIVE" ? "#22c55e" : "#ef4444",
                }}>
                  {c.ats_status || "—"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function HealthDashboard() {
  const pipeline = useHealth("/pipeline", 15000);
  const connectors = useHealth("/connectors", 30000);
  const coverage = useHealth("/coverage", 60000);
  const [now, setNow] = useState(new Date());
  const [tab, setTab] = useState<"pipeline" | "connectors" | "coverage" | "companies">("pipeline");

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const isLive = !pipeline.error;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0f",
      color: "#e2e8f0",
      fontFamily: "'Inter', -apple-system, sans-serif",
      padding: "0",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        padding: "16px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(255,255,255,0.02)",
        backdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <a href="/" style={{ color: "#9ca3af", textDecoration: "none", fontSize: 13 }}>← CareerAutomated</a>
          <span style={{ color: "#374151" }}>/</span>
          <span style={{ fontWeight: 700, fontSize: 15, color: "#f1f5f9" }}>System Health</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#9ca3af" }}>
            <StatusDot ok={isLive} />
            {isLive ? "Live" : "Error"}
          </div>
          <div style={{ fontSize: 12, color: "#4b5563", fontVariantNumeric: "tabular-nums" }}>
            {now.toLocaleTimeString()}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
        {/* Tab Navigation */}
        <div style={{ display: "flex", gap: 4, marginBottom: 32, borderBottom: "1px solid rgba(255,255,255,0.07)", paddingBottom: 0 }}>
          {(["pipeline", "connectors", "coverage", "companies"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "10px 20px",
                background: "transparent",
                border: "none",
                borderBottom: tab === t ? "2px solid #818cf8" : "2px solid transparent",
                color: tab === t ? "#818cf8" : "#6b7280",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                textTransform: "capitalize",
                transition: "all 0.2s",
                marginBottom: -1,
              }}
            >
              {t === "pipeline" ? "Pipeline Funnel" : t === "connectors" ? "ATS Connectors" : t === "coverage" ? "Coverage Report" : "Per Company"}
            </button>
          ))}
        </div>

        {/* Pipeline Tab */}
        {tab === "pipeline" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
            <div>
              <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>Pipeline Funnel</h2>
              {pipeline.loading ? <div style={{ color: "#6b7280" }}>Loading…</div> : <PipelineFunnel data={pipeline.data} />}
            </div>

            {/* Workers */}
            <div>
              <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>Workers</h2>
              {pipeline.data?.workers?.length > 0 ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
                  {pipeline.data.workers.map((w: any) => (
                    <div key={w.worker_id || w.name} style={{
                      background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
                      borderRadius: 12, padding: "14px 16px",
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                        <StatusDot ok={w.status === "RUNNING"} />
                        <span style={{ fontWeight: 600, fontSize: 13, color: "#e2e8f0" }}>{w.name || w.worker_id}</span>
                      </div>
                      <div style={{ fontSize: 11, color: "#6b7280" }}>
                        <div>Failures: {w.failures || 0}</div>
                        <div>Jobs: {w.jobs_processed || 0}</div>
                        {w.last_heartbeat && <div>Heartbeat: {new Date(w.last_heartbeat * 1000).toLocaleTimeString()}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#6b7280", fontSize: 13 }}>No worker state data available</div>
              )}
            </div>

            {/* Queues */}
            <div>
              <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>Queue Depths</h2>
              {pipeline.data?.queues?.length > 0 ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                  {pipeline.data.queues.map((q: any) => (
                    <div key={`${q.queue_name}-${q.status}`} style={{
                      background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
                      borderRadius: 12, padding: "14px 16px",
                    }}>
                      <div style={{ fontSize: 22, fontWeight: 700, color: "#818cf8" }}>{q.cnt}</div>
                      <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4 }}>{q.queue_name} · {q.status}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#6b7280", fontSize: 13 }}>No queue data available</div>
              )}
            </div>
          </div>
        )}

        {/* Connectors Tab */}
        {tab === "connectors" && (
          <div>
            <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>ATS Connector Reliability</h2>
            {connectors.loading ? <div style={{ color: "#6b7280" }}>Loading…</div> : <ConnectorTable data={connectors.data} />}
          </div>
        )}

        {/* Coverage Tab */}
        {tab === "coverage" && (
          <div>
            <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>Top Company Coverage</h2>
            {coverage.loading ? <div style={{ color: "#6b7280" }}>Loading…</div> : <CoverageTable data={coverage.data} />}
          </div>
        )}

        {/* Per Company Tab */}
        {tab === "companies" && (
          <div>
            <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#94a3b8" }}>Companies with Jobs</h2>
            {pipeline.loading ? <div style={{ color: "#6b7280" }}>Loading…</div> : <PerCompanyTable data={pipeline.data} />}
          </div>
        )}
      </div>
    </div>
  );
}
