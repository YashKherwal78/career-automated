import { createFileRoute } from "@tanstack/react-router";
import { useDashboard } from "../../components/dashboard/DashboardContext";
import { LoadingSkeleton, StatCard } from "../../components/dashboard/CommonComponents";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend
} from "recharts";
import { Building2, Award, ArrowUpRight } from "lucide-react";

export const Route = createFileRoute("/dashboard/analytics")({
  component: AnalyticsPage,
});

function AnalyticsPage() {
  const { overview, loading } = useDashboard();

  if (loading) {
    return (
      <div className="p-8 space-y-8">
        <LoadingSkeleton type="stats" />
        <LoadingSkeleton type="cards" count={3} />
      </div>
    );
  }

  // Mock data for Recharts
  const jobsOverTime = [
    { date: "Jul 01", count: 420 },
    { date: "Jul 02", count: 750 },
    { date: "Jul 03", count: 910 },
    { date: "Jul 04", count: 1200 },
    { date: "Jul 05", count: 1850 },
    { date: "Jul 06", count: 2100 },
    { date: "Jul 07", count: 2443 }
  ];

  const atsDistribution = [
    { name: "Greenhouse", value: 598, color: "#f97316" }, // Peach orange
    { name: "Lever", value: 289, color: "#0ea5e9" }, // Sky blue
    { name: "Workday", value: 7, color: "#10b981" }, // Emerald green
    { name: "Ashby", value: 115, color: "#8b5cf6" } // Purple
  ];

  const locationsData = [
    { name: "Bangalore", jobs: 120 },
    { name: "Remote", jobs: 94 },
    { name: "Hyderabad", jobs: 62 },
    { name: "Delhi NCR", jobs: 48 },
    { name: "Pune", jobs: 32 }
  ];

  const topHiring = [
    { name: "Stripe", jobs: 14 },
    { name: "Nvidia", jobs: 12 },
    { name: "Razorpay", jobs: 8 },
    { name: "Groww", jobs: 6 }
  ];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Analytical Overview</h1>
        <p className="mt-1 text-xs text-ink-soft">
          Aggregated discovery and crawler metrics across all pipelines.
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <StatCard
          title="Today's Discoveries"
          value="102"
          detail="Verified endpoints"
          icon={Building2}
        />
        <StatCard
          title="Today's Jobs Indexed"
          value="2,443"
          detail="Crawler throughput"
          icon={ArrowUpRight}
        />
        <StatCard
          title="Avg Crawl Latency"
          value="1.2s"
          detail="Response duration"
          icon={Award}
        />
        <StatCard
          title="ATS Distribution"
          value="4 active"
          detail="Greenhouse, Lever, etc."
          icon={Award}
        />
      </div>

      {/* Recharts Plots */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Jobs Discovered Over Time */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
          <h3 className="font-display text-base font-semibold text-ink">Jobs Crawled Over Time (July)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={jobsOverTime} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--peach-deep)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--peach-deep)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} />
                <YAxis stroke="#94a3b8" fontSize={10} />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="var(--peach-deep)" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ATS Distribution */}
        <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
          <h3 className="font-display text-base font-semibold text-ink">ATS Platforms Breakdown</h3>
          <div className="h-56 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={atsDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {atsDistribution.map((entry, idx) => (
                    <Cell key={`cell-${idx}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 text-[10px] uppercase font-bold text-ink-soft">
            {atsDistribution.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                <span>{item.name} ({item.value})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Location Breakdown */}
        <div className="glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
          <h3 className="font-display text-base font-semibold text-ink">Jobs by Location</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={locationsData} layout="vertical" margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" stroke="#94a3b8" fontSize={9} />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={9} />
                <Tooltip />
                <Bar dataKey="jobs" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Hiring Partners */}
        <div className="lg:col-span-2 glass-card rounded-3xl p-6 border border-white/50 bg-white/40 shadow-sm space-y-4">
          <h3 className="font-display text-base font-semibold text-ink">Top Hiring Companies</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topHiring} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} />
                <YAxis stroke="#94a3b8" fontSize={10} />
                <Tooltip />
                <Bar dataKey="jobs" fill="var(--peach-deep)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
