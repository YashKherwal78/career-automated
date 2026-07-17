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
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

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
        refresh
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
