import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { MapPin, Briefcase, Sparkles, Filter, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardHome,
});

// Rotating secondary message list
const ROTATING_MESSAGES = [
  "Let's get you closer to your next opportunity.",
  "Everything is ready.",
  "Your AI is already working.",
  "Apply smarter. Stay application-ready.",
  "Built around modern hiring workflows."
];

// Mock Jobs
const INITIAL_TOP_MATCHES = [
  { id: 1, company: "Stripe", role: "Product Engineer", location: "San Francisco, CA", type: "Full-time", match: 96 },
  { id: 2, company: "Linear", role: "Frontend Engineer", location: "Remote", type: "Full-time", match: 94 },
  { id: 3, company: "Notion", role: "Full-stack Developer", location: "New York, NY", type: "Hybrid", match: 91 },
  { id: 4, company: "Ramp", role: "Software Engineer", location: "Miami, FL", type: "Full-time", match: 89 },
  { id: 5, company: "OpenAI", role: "Research Engineer", location: "San Francisco, CA", type: "Full-time", match: 88 }
];

const INITIAL_REMAINING_JOBS = [
  { id: 6, company: "Vercel", role: "Developer Relations Engineer", location: "Remote", type: "Full-time", match: 85 },
  { id: 7, company: "Figma", role: "Systems Engineer", location: "San Francisco, CA", type: "Hybrid", match: 84 },
  { id: 8, company: "Retool", role: "Backend Developer", location: "Remote", type: "Full-time", match: 82 },
  { id: 9, company: "Attio", role: "Product Designer", location: "London, UK", type: "Full-time", match: 80 },
  { id: 10, company: "Superhuman", role: "Growth Engineer", location: "New York, NY", type: "Remote", match: 79 },
  { id: 11, company: "Raycast", role: "macOS Developer", location: "Remote", type: "Full-time", match: 78 }
];

function DashboardHome() {
  const [rotatingIndex, setRotatingIndex] = useState(0);
  const [locationFilter, setLocationFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  
  // Rotating header message interval
  useEffect(() => {
    const interval = setInterval(() => {
      setRotatingIndex((prev) => (prev + 1) % ROTATING_MESSAGES.length);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  // Filter logic
  const filterJobs = (jobs: typeof INITIAL_TOP_MATCHES) => {
    return jobs.filter(job => {
      const matchLoc = locationFilter === "All" || 
        (locationFilter === "Remote" && job.location.toLowerCase().includes("remote")) ||
        (locationFilter === "Onsite/Hybrid" && !job.location.toLowerCase().includes("remote"));
      const matchType = typeFilter === "All" || job.type === typeFilter;
      return matchLoc && matchType;
    });
  };

  const filteredTopMatches = filterJobs(INITIAL_TOP_MATCHES);
  const filteredRemainingJobs = filterJobs(INITIAL_REMAINING_JOBS);

  return (
    <div className="max-w-6xl mx-auto px-8 py-12 space-y-12">
      {/* 1. Dynamic Greeting Header */}
      <div className="space-y-1.5">
        <h1 className="font-display text-4xl font-semibold tracking-tight text-ink">
          Hi, Yash
        </h1>
        <div className="h-5 overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.p
              key={rotatingIndex}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4 }}
              className="text-sm text-ink-soft font-medium"
            >
              {ROTATING_MESSAGES[rotatingIndex]}
            </motion.p>
          </AnimatePresence>
        </div>
      </div>

      {/* 2. Top Matches (Auto Apply Train Layout) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs uppercase font-bold tracking-widest text-ink-soft flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-[color:var(--peach-deep)]" /> Top Opportunities
          </h2>
          <span className="text-[10px] text-ink-soft">Slide view ready</span>
        </div>
        
        {/* Train track horizontal layout */}
        <div className="relative">
          <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-none snap-x snap-mandatory">
            {filteredTopMatches.length === 0 ? (
              <div className="w-full py-12 text-center border border-dashed border-white/60 bg-white/20 rounded-3xl">
                <span className="text-xs text-ink-soft">No matching opportunities found with current filters.</span>
              </div>
            ) : (
              filteredTopMatches.map((job) => (
                <div
                  key={job.id}
                  className="snap-start shrink-0 w-[240px] glass-card rounded-3xl p-6 border border-white/60 bg-white/40 shadow-sm flex flex-col justify-between hover:shadow-md hover:-translate-y-1 transition-all duration-300"
                >
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <span className="text-[10px] uppercase font-bold text-ink-soft tracking-wider">
                        {job.company}
                      </span>
                      <span className="inline-flex items-center text-xs font-semibold text-[color:var(--peach-deep)]">
                        {job.match}% Match
                      </span>
                    </div>
                    
                    <h3 className="font-display text-lg font-semibold leading-tight text-ink">
                      {job.role}
                    </h3>
                  </div>

                  <div className="mt-8 space-y-4">
                    <div className="space-y-1 text-[11px] text-ink-soft">
                      <div className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        <span>{job.location}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Briefcase className="h-3 w-3" />
                        <span>{job.type}</span>
                      </div>
                    </div>

                    <button className="btn-dark w-full py-2 text-xs rounded-xl flex items-center justify-center gap-1">
                      Apply Opportunity <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 3. Filters Section */}
      <div className="flex flex-wrap items-center justify-between border-t border-b border-white/20 py-4 gap-4">
        <div className="flex items-center gap-2 text-xs text-ink-soft">
          <Filter className="h-3.5 w-3.5" />
          <span className="font-medium">Filter Engine</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Location Filter */}
          <div className="flex rounded-xl bg-white/40 border border-white/60 p-0.5 text-[11px]">
            {["All", "Remote", "Onsite/Hybrid"].map((loc) => (
              <button
                key={loc}
                onClick={() => setLocationFilter(loc)}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  locationFilter === loc ? "bg-white text-ink shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                {loc}
              </button>
            ))}
          </div>

          {/* Job Type Filter */}
          <div className="flex rounded-xl bg-white/40 border border-white/60 p-0.5 text-[11px]">
            {["All", "Full-time", "Hybrid"].map((type) => (
              <button
                key={type}
                onClick={() => setTypeFilter(type)}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  typeFilter === type ? "bg-white text-ink shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Remaining Jobs list */}
      <div className="space-y-4">
        <h2 className="text-xs uppercase font-bold tracking-widest text-ink-soft">
          Other Pipeline Opportunities
        </h2>
        
        <div className="glass-card rounded-3xl border border-white/60 bg-white/30 overflow-hidden shadow-sm">
          {filteredRemainingJobs.length === 0 ? (
            <div className="py-12 text-center">
              <span className="text-xs text-ink-soft">No remaining jobs match your selection.</span>
            </div>
          ) : (
            <div className="divide-y divide-white/20">
              {filteredRemainingJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between px-6 py-4 hover:bg-white/40 transition-colors group"
                >
                  <div className="flex items-center gap-6">
                    <div className="grid h-10 w-10 place-items-center rounded-2xl bg-white/70 border border-white/80 text-xs font-semibold text-ink">
                      {job.company.slice(0, 1)}
                    </div>
                    
                    <div className="space-y-0.5">
                      <h4 className="text-sm font-semibold text-ink group-hover:text-[color:var(--peach-deep)] transition-colors">
                        {job.role}
                      </h4>
                      <div className="flex items-center gap-3 text-[11px] text-ink-soft">
                        <span>{job.company}</span>
                        <span>•</span>
                        <span>{job.location}</span>
                        <span>•</span>
                        <span>{job.type}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <span className="text-xs font-semibold text-[color:var(--peach-deep)]">
                      {job.match}% match
                    </span>
                    <button className="btn-dark px-4 py-1.5 text-xs rounded-xl opacity-80 group-hover:opacity-100 transition-opacity">
                      Apply
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
