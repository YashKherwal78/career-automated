import React, { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { 
  ServiceRegistry, 
  JobService, 
  CompanyService, 
  PipelineService, 
  AnalyticsService, 
  ResumeService, 
  Job, 
  Company, 
  PipelineStatus, 
  FunnelOverview 
} from "../../lib/services";

interface DashboardContextType {
  jobService: JobService;
  companyService: CompanyService;
  pipelineService: PipelineService;
  analyticsService: AnalyticsService;
  resumeService: ResumeService;
  recentJobs: Job[];
  companies: Company[];
  pipeline: PipelineStatus | null;
  overview: FunnelOverview | null;
  loading: boolean;
  refresh: () => Promise<void>;
  // Shared across every page that lists jobs (Dashboard home, Jobs page) so
  // toggling it in one place is reflected everywhere else immediately,
  // rather than each page keeping its own independent copy that could
  // drift out of sync. Persisted to localStorage so the choice survives a
  // reload/new session too, same as any other standing filter preference.
  includeInterns: boolean;
  setIncludeInterns: (value: boolean) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

const INCLUDE_INTERNS_STORAGE_KEY = "careerautomated:includeInterns";

function loadIncludeInterns(): boolean {
  try {
    const stored = localStorage.getItem(INCLUDE_INTERNS_STORAGE_KEY);
    return stored === null ? true : stored === "true";
  } catch {
    return true;
  }
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const jobService = ServiceRegistry.getJobService();
  const companyService = ServiceRegistry.getCompanyService();
  const pipelineService = ServiceRegistry.getPipelineService();
  const analyticsService = ServiceRegistry.getAnalyticsService();
  const resumeService = ServiceRegistry.getResumeService();

  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [overview, setOverview] = useState<FunnelOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [includeInterns, setIncludeInternsState] = useState(loadIncludeInterns);

  const setIncludeInterns = (value: boolean) => {
    setIncludeInternsState(value);
    try {
      localStorage.setItem(INCLUDE_INTERNS_STORAGE_KEY, String(value));
    } catch {
      // Storage unavailable (private browsing, quota) -- in-memory state
      // still updates above, this just won't survive a reload.
    }
  };

  const refresh = async () => {
    setLoading(true);
    try {
      const [jobsData, companiesData, pipelineData, overviewData] = await Promise.all([
        jobService.getRecentJobs().catch(() => []),
        companyService.getCompanies().catch(() => []),
        pipelineService.getPipelineStatus().catch(() => null),
        analyticsService.getOverview().catch(() => null)
      ]);
      setRecentJobs(jobsData);
      setCompanies(companiesData);
      setPipeline(pipelineData);
      setOverview(overviewData);
    } catch (e) {
      console.error("Failed to load dashboard context data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <DashboardContext.Provider
      value={{
        jobService,
        companyService,
        pipelineService,
        analyticsService,
        resumeService,
        recentJobs,
        companies,
        pipeline,
        overview,
        loading,
        refresh,
        includeInterns,
        setIncludeInterns,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboard must be used within DashboardProvider");
  return context;
}
