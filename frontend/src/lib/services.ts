export interface Job {
  job_id: string;
  title: string;
  canonical_name: string;
  location: string;
  salary_min: number | null;
  salary_max: number | null;
  remote: string;
  provider: string;
  posted_at: string;
  job_score: number;
  intent_score: number | null;
  score_breakdown: string[] | { keyword: string; matched: boolean }[];
  apply_url: string;
  description?: string;
  application_status?: string;
}

export interface Company {
  company_id: string;
  company_name: string;
  website: string;
  ats_type: string | null;
  status: string | null;
  job_count: number | null;
  last_checked: number | null;
  crawl_status: string | null;
}

export interface PipelineStatus {
  companies: number;
  endpoints: number;
  verified: number;
  jobs: number;
  workers: {
    discovery: string;
    verification: string;
    crawler: string;
    retry_queue: number;
    failures: number;
  };
}

export interface FunnelOverview {
  companies: number;
  verified: number;
  jobs: number;
  active_workers: number;
  failed_workers: number;
  discovery_queue: number;
  verification_queue: number;
  crawl_queue: number;
}

export interface JobService {
  getJobs(filters?: {
    company?: string;
    provider?: string;
    min_score?: number;
    page?: number;
    location?: string;
    remote_type?: string;
    employment_type?: string;
    seniority?: string;
    min_salary?: number;
    sort_by?: string;
    page_size?: number;
  }): Promise<Job[]>;
  getBoardJobs(filters?: {
    company?: string;
    provider?: string;
    min_score?: number;
    page?: number;
    location?: string;
    remote_type?: string;
    employment_type?: string;
    seniority?: string;
    min_salary?: number;
    sort_by?: string;
    page_size?: number;
  }): Promise<Job[]>;
  getJob(jobId: string): Promise<Job>;
  getRecentJobs(): Promise<Job[]>;
}

export interface CompanyService {
  getCompanies(page?: number): Promise<Company[]>;
}

export interface PipelineService {
  getPipelineStatus(): Promise<PipelineStatus>;
}

export interface ResumeService {
  getResumeInfo(): Promise<{
    score: number;
    skills: string[];
    projectsCount: number;
    history: { date: string; score: number; changes: string }[];
  }>;
}

import { supabase } from "./supabase";
import { API_BASE } from "./api";

async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const headers = new Headers(init?.headers);
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  return fetch(input, { ...init, headers });
}

export class ApiJobService implements JobService {
  private buildParams(filters?: any): URLSearchParams {
    const params = new URLSearchParams();
    if (filters?.company) params.append("company", filters.company);
    if (filters?.provider) params.append("provider", filters.provider);
    if (filters?.min_score) params.append("min_score", String(filters.min_score));
    if (filters?.page) params.append("page", String(filters.page));
    if (filters?.location) params.append("location", filters.location);
    if (filters?.remote_type) params.append("remote_type", filters.remote_type);
    if (filters?.employment_type) params.append("employment_type", filters.employment_type);
    if (filters?.seniority) params.append("seniority", filters.seniority);
    if (filters?.min_salary) params.append("min_salary", String(filters.min_salary));
    if (filters?.sort_by) params.append("sort_by", filters.sort_by);
    params.append("page_size", String(filters?.page_size || 100));
    return params;
  }

  async getJobs(filters?: any): Promise<Job[]> {
    const params = this.buildParams(filters);
    const res = await authFetch(`${API_BASE}/jobs?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch jobs");
    return res.json();
  }

  async getBoardJobs(filters?: any): Promise<Job[]> {
    const params = this.buildParams(filters);
    const res = await authFetch(`${API_BASE}/jobs/boards?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch job board jobs");
    return res.json();
  }

  async getJob(jobId: string): Promise<Job> {
    const res = await authFetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error("Failed to fetch job details");
    return res.json();
  }

  async getRecentJobs(): Promise<Job[]> {
    const res = await authFetch(`${API_BASE}/jobs?page_size=10`);
    if (!res.ok) throw new Error("Failed to fetch recent jobs");
    return res.json();
  }
}

export class ApiCompanyService implements CompanyService {
  async getCompanies(page = 1): Promise<Company[]> {
    const res = await authFetch(`${API_BASE}/companies?page=${page}&page_size=30`);
    if (!res.ok) throw new Error("Failed to fetch companies");
    return res.json();
  }
}

export class ApiPipelineService implements PipelineService {
  async getPipelineStatus(): Promise<PipelineStatus> {
    const res = await authFetch(`${API_BASE}/analytics/pipeline`);
    if (!res.ok) throw new Error("Failed to fetch pipeline status");
    return res.json();
  }
}

export class ApiAnalyticsService implements AnalyticsService {
  async getOverview(): Promise<FunnelOverview> {
    const res = await authFetch(`${API_BASE}/dashboard`);
    if (!res.ok) throw new Error("Failed to fetch dashboard summary");
    return res.json();
  }
}

export interface CreateOrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
}

export interface SubscriptionResponse {
  tier: "free" | "pro";
  active_since: string | null;
}

export class BillingService {
  async createOrder(): Promise<CreateOrderResponse> {
    const res = await authFetch(`${API_BASE}/billing/create-order`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create Razorpay order");
    return res.json();
  }

  async verifyPayment(payload: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }): Promise<{ status: string }> {
    const res = await authFetch(`${API_BASE}/billing/verify-payment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Payment verification failed");
    return res.json();
  }

  async getSubscription(): Promise<SubscriptionResponse> {
    const res = await authFetch(`${API_BASE}/billing/subscription`);
    if (!res.ok) throw new Error("Failed to fetch subscription status");
    return res.json();
  }
}

export class ApiResumeService implements ResumeService {
  async getResumeInfo(): Promise<{
    score: number;
    skills: string[];
    projectsCount: number;
    history: { date: string; score: number; changes: string }[];
  }> {
    // Return mock since resume parsing is client-side uploaded
    return {
      score: 84,
      skills: [
        "React",
        "TypeScript",
        "Tailwind CSS",
        "FastAPI",
        "Python",
        "SQLite",
        "Git",
        "Docker",
        "REST APIs",
      ],
      projectsCount: 4,
      history: [
        { date: "Yesterday", score: 84, changes: "Added FastAPI details" },
        { date: "3 days ago", score: 78, changes: "Initial upload" },
      ],
    };
  }
}

export class MockJobService implements JobService {
  private mockJobs: Job[] = [
    {
      job_id: "mock-1",
      title: "Software Engineer",
      canonical_name: "Stripe",
      location: "Bangalore",
      salary_min: 1500000,
      salary_max: 2200000,
      remote: "Hybrid",
      provider: "greenhouse",
      posted_at: "Today",
      job_score: 92,
      score_breakdown: [
        { keyword: "Python", matched: true },
        { keyword: "FastAPI", matched: true },
        { keyword: "Docker", matched: false },
      ],
      apply_url: "https://stripe.com",
      description: "We are looking for a Software Engineer to help scale our payment systems.",
    },
  ];

  async getJobs(): Promise<Job[]> {
    return this.mockJobs;
  }
  async getJob(): Promise<Job> {
    return this.mockJobs[0];
  }
  async getRecentJobs(): Promise<Job[]> {
    return this.mockJobs;
  }
}

export class MockCompanyService implements CompanyService {
  async getCompanies(): Promise<Company[]> {
    return [
      {
        company_id: "stripe",
        company_name: "Stripe",
        website: "stripe.com",
        ats_type: "Greenhouse",
        status: "ACTIVE",
        job_count: 14,
        last_checked: Date.now(),
        crawl_status: "SUCCESS",
      },
    ];
  }
}

export class MockPipelineService implements PipelineService {
  async getPipelineStatus(): Promise<PipelineStatus> {
    return {
      companies: 6482,
      endpoints: 1867,
      verified: 1108,
      jobs: 145332,
      workers: {
        discovery: "Running",
        verification: "Running",
        crawler: "Running",
        retry_queue: 3,
        failures: 1,
      },
    };
  }
}

export class ServiceRegistry {
  // Mock services should only be enabled explicitly in development via environment variable.
  private static useMock = import.meta.env.VITE_USE_MOCK_SERVICES === "true";

  static getJobService(): JobService {
    return this.useMock ? new MockJobService() : new ApiJobService();
  }

  static getCompanyService(): CompanyService {
    return this.useMock ? new MockCompanyService() : new ApiCompanyService();
  }

  static getPipelineService(): PipelineService {
    return this.useMock ? new MockPipelineService() : new ApiPipelineService();
  }

  static getAnalyticsService(): AnalyticsService {
    // Both point to API for now, but mock can be added if needed
    return new ApiAnalyticsService();
  }

  static getResumeService(): ResumeService {
    return new ApiResumeService();
  }

  static getBillingService(): BillingService {
    return new BillingService();
  }
}
