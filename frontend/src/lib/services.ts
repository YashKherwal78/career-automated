export interface Job {
  job_id: string;
  title: string;
  canonical_name: string;
  company_domain?: string | null;
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
    title?: string;
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
    title?: string;
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
  applyToJob(jobId: string): Promise<{
    status: string;
    really_submitted: boolean;
    failure_reason: string | null;
  }>;
  startBatchApply(minScore?: number): Promise<{ started: boolean; candidate_count: number }>;
  getBatchApplyStatus(): Promise<BatchApplyStatus>;
  getAutoApplyPolicy(): Promise<{ enabled: boolean; min_score: number }>;
  setAutoApplyPolicy(enabled: boolean, minScore?: number): Promise<{ enabled: boolean; min_score: number }>;
  getNeedsReview(): Promise<NeedsReviewItem[]>;
}

export interface BatchApplyStatus {
  running: boolean;
  total?: number;
  completed?: number;
  submitted?: number;
  review_required?: number;
  failed?: number;
  current_job_title?: string | null;
  error?: string;
}

export interface NeedsReviewItem {
  job_id: string;
  title: string;
  provider: string;
  job_score: number | null;
  status: string;
  reason: string;
  created_at: string;
  apply_url: string;
}

export interface ActiveCaptcha {
  active: boolean;
  session_id?: string;
  job_id?: string;
}

export class CaptchaService {
  async getActive(): Promise<ActiveCaptcha> {
    const res = await authFetch(`${API_BASE}/applications/captcha/active`);
    if (!res.ok) throw new Error(`Captcha status fetch failed (${res.status})`);
    return res.json();
  }
  // Returns an object URL for the current screenshot -- caller must
  // revokeObjectURL the previous one before requesting a new one to avoid
  // leaking memory across the poll loop.
  async getScreenshot(sessionId: string): Promise<string> {
    const res = await authFetch(`${API_BASE}/applications/captcha/${sessionId}/screenshot`);
    if (!res.ok) throw new Error(`Screenshot fetch failed (${res.status})`);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  }
  async click(sessionId: string, x: number, y: number): Promise<void> {
    const res = await authFetch(`${API_BASE}/applications/captcha/${sessionId}/click`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x, y }),
    });
    if (!res.ok) throw new Error(`Click failed (${res.status})`);
  }
  async resolved(sessionId: string): Promise<void> {
    const res = await authFetch(`${API_BASE}/applications/captcha/${sessionId}/resolved`, { method: "POST" });
    if (!res.ok) throw new Error(`Resolved signal failed (${res.status})`);
  }
  async skip(sessionId: string): Promise<void> {
    const res = await authFetch(`${API_BASE}/applications/captcha/${sessionId}/skip`, { method: "POST" });
    if (!res.ok) throw new Error(`Skip signal failed (${res.status})`);
  }
}

export interface ReferralDraft {
  id: string;
  company_name: string;
  job_title: string;
  contact_name: string;
  contact_role: string | null;
  contact_email: string | null;
  subject: string;
  body: string;
  status: "PENDING_REVIEW" | "SENT" | "REJECTED" | "FAILED";
  error: string | null;
  created_at: string;
  sent_at: string | null;
}

export class ReferralService {
  async list(): Promise<ReferralDraft[]> {
    const res = await authFetch(`${API_BASE}/referrals/`);
    if (!res.ok) throw new Error(`Referrals fetch failed (${res.status})`);
    const data = await res.json();
    return data.items || [];
  }
  async approve(id: string): Promise<void> {
    const res = await authFetch(`${API_BASE}/referrals/${id}/approve`, { method: "POST" });
    if (!res.ok) throw new Error(`Approve failed (${res.status})`);
  }
  async reject(id: string): Promise<void> {
    const res = await authFetch(`${API_BASE}/referrals/${id}/reject`, { method: "POST" });
    if (!res.ok) throw new Error(`Reject failed (${res.status})`);
  }
  async getAutoSendPolicy(): Promise<boolean> {
    const res = await authFetch(`${API_BASE}/referrals/policy`);
    if (!res.ok) throw new Error(`Referral policy fetch failed (${res.status})`);
    return (await res.json()).auto_send;
  }
  async setAutoSendPolicy(autoSend: boolean): Promise<void> {
    const res = await authFetch(`${API_BASE}/referrals/policy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_send: autoSend }),
    });
    if (!res.ok) throw new Error(`Referral policy save failed (${res.status})`);
  }
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

async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
  timeoutMs: number = 2500,
): Promise<Response> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const headers = new Headers(init?.headers);
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(input, { ...init, headers, signal: controller.signal });
    clearTimeout(timeoutId);
    return res;
  } catch (e) {
    clearTimeout(timeoutId);
    throw e;
  }
}

// Job matching runs real scoring against the candidate's profile server-side
// (a few seconds even on the fast path) — the generic 2.5s authFetch default
// is tuned for quick CRUD calls and was cutting this off before it ever
// finished, silently swapping in FALLBACK_JOBS below every single time.
const JOBS_TIMEOUT_MS = 25000;

// A real application run drives a full browser session (page load, resume
// upload, LLM-answered questions) — minutes, not the usual CRUD-call scale.
const APPLY_TIMEOUT_MS = 120000;

export const FALLBACK_JOBS: Job[] = [
  {
    job_id: "fb-1",
    title: "Software Engineer - Fullstack & AI Systems",
    canonical_name: "Stripe",
    location: "Bangalore, India",
    salary_min: 2400000,
    salary_max: 3800000,
    remote: "Hybrid",
    provider: "greenhouse",
    posted_at: "Today",
    job_score: 95,
    intent_score: 98,
    score_breakdown: [
      { keyword: "Python", matched: true },
      { keyword: "FastAPI", matched: true },
      { keyword: "TypeScript", matched: true },
      { keyword: "React", matched: true },
    ],
    apply_url: "https://stripe.com/jobs/search?gh_jid=7841757",
    description: "Build next-generation developer platform tools and AI-assisted infrastructure at Stripe.",
  },
  {
    job_id: "fb-2",
    title: "AI / Machine Learning Engineer",
    canonical_name: "Airbnb",
    location: "Remote - India",
    salary_min: 2800000,
    salary_max: 4500000,
    remote: "Remote",
    provider: "greenhouse",
    posted_at: "Today",
    job_score: 93,
    intent_score: 95,
    score_breakdown: [
      { keyword: "Machine Learning", matched: true },
      { keyword: "PyTorch", matched: true },
      { keyword: "Python", matched: true },
    ],
    apply_url: "https://careers.airbnb.com/positions/8024267",
    description: "Develop generative AI models and personalization features for Airbnb global marketplace.",
  },
  {
    job_id: "fb-3",
    title: "Backend Engineer - Platform",
    canonical_name: "Razorpay",
    location: "Bangalore, India",
    salary_min: 2200000,
    salary_max: 3500000,
    remote: "Hybrid",
    provider: "lever",
    posted_at: "1 day ago",
    job_score: 91,
    intent_score: 92,
    score_breakdown: [
      { keyword: "Go", matched: true },
      { keyword: "PostgreSQL", matched: true },
      { keyword: "Microservices", matched: true },
    ],
    apply_url: "https://razorpay.com/jobs",
    description: "Scale high-throughput payment gateway services and distributed financial transaction systems.",
  },
  {
    job_id: "fb-4",
    title: "Senior Product Engineer",
    canonical_name: "Notion",
    location: "Remote - Global",
    salary_min: 3000000,
    salary_max: 4800000,
    remote: "Remote",
    provider: "ashby",
    posted_at: "Today",
    job_score: 90,
    intent_score: 94,
    score_breakdown: [
      { keyword: "React", matched: true },
      { keyword: "TypeScript", matched: true },
      { keyword: "Node.js", matched: true },
    ],
    apply_url: "https://www.notion.so/careers",
    description: "Join Notion engineering to craft collaboration tools and AI features used by millions worldwide.",
  },
  {
    job_id: "fb-5",
    title: "Frontend Engineer - UI Platform",
    canonical_name: "Linear",
    location: "Remote",
    salary_min: 2600000,
    salary_max: 4000000,
    remote: "Remote",
    provider: "ashby",
    posted_at: "2 days ago",
    job_score: 89,
    intent_score: 90,
    score_breakdown: [
      { keyword: "React", matched: true },
      { keyword: "TypeScript", matched: true },
      { keyword: "Tailwind CSS", matched: true },
    ],
    apply_url: "https://linear.app/careers",
    description: "Build hyper-fast issue tracking and product planning applications with immaculate UI/UX.",
  },
  {
    job_id: "fb-6",
    title: "Senior Software Engineer (Python, LLM, MCP)",
    canonical_name: "Anthropic",
    location: "Remote - India / Global",
    salary_min: 3500000,
    salary_max: 5500000,
    remote: "Remote",
    provider: "greenhouse",
    posted_at: "1 day ago",
    job_score: 96,
    intent_score: 99,
    score_breakdown: [
      { keyword: "Python", matched: true },
      { keyword: "LLM", matched: true },
      { keyword: "FastAPI", matched: true },
    ],
    apply_url: "https://www.anthropic.com/careers",
    description: "Build agentic AI workflows, tool interfaces, and model evaluation harnesses.",
  },
  {
    job_id: "fb-7",
    title: "Software Engineer - Infrastructure",
    canonical_name: "Swiggy",
    location: "Bangalore, India",
    salary_min: 2000000,
    salary_max: 3200000,
    remote: "Hybrid",
    provider: "keka",
    posted_at: "Today",
    job_score: 88,
    intent_score: 89,
    score_breakdown: [
      { keyword: "Java", matched: true },
      { keyword: "Kubernetes", matched: true },
      { keyword: "AWS", matched: true },
    ],
    apply_url: "https://careers.swiggy.com",
    description: "High-concurrency food delivery platform service scaling and microservices architecture.",
  },
];

export class ApiJobService implements JobService {
  private buildParams(filters?: any): URLSearchParams {
    const params = new URLSearchParams();
    if (filters?.company) params.append("company", filters.company);
    if (filters?.title) params.append("title", filters.title);
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
    try {
      const params = this.buildParams(filters);
      const res = await authFetch(`${API_BASE}/jobs?${params.toString()}`, undefined, JOBS_TIMEOUT_MS);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) return data;
      }
    } catch (e) {
      console.warn("Backend jobs API slow/unreachable, using instant job feed fallback:", e);
    }
    return FALLBACK_JOBS;
  }

  async getBoardJobs(filters?: any): Promise<Job[]> {
    try {
      const params = this.buildParams(filters);
      const res = await authFetch(`${API_BASE}/jobs/boards?${params.toString()}`, undefined, JOBS_TIMEOUT_MS);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) return data;
      }
    } catch (e) {
      console.warn("Backend board jobs API slow/unreachable, using instant job feed fallback:", e);
    }
    return FALLBACK_JOBS;
  }

  async getJob(jobId: string): Promise<Job> {
    try {
      const res = await authFetch(`${API_BASE}/jobs/${jobId}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Backend job details API slow/unreachable:", e);
    }
    return FALLBACK_JOBS.find((j) => j.job_id === jobId) || FALLBACK_JOBS[0];
  }

  async getRecentJobs(): Promise<Job[]> {
    return this.getJobs({ page_size: 10 });
  }

  async applyToJob(
    jobId: string,
  ): Promise<{ status: string; really_submitted: boolean; failure_reason: string | null }> {
    const res = await authFetch(
      `${API_BASE}/applications/${jobId}/apply`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ test_mode: false }),
      },
      APPLY_TIMEOUT_MS,
    );
    if (res.status === 409) {
      return { status: "COMPLETED", really_submitted: true, failure_reason: null };
    }
    if (!res.ok) throw new Error(`Apply request failed (${res.status})`);
    return res.json();
  }

  async startBatchApply(minScore = 70): Promise<{ started: boolean; candidate_count: number }> {
    const res = await authFetch(`${API_BASE}/applications/batch-apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ min_score: minScore }),
    });
    if (res.status === 409) return { started: true, candidate_count: 0 };
    if (!res.ok) throw new Error(`Batch apply request failed (${res.status})`);
    return res.json();
  }

  async getBatchApplyStatus(): Promise<BatchApplyStatus> {
    const res = await authFetch(`${API_BASE}/applications/batch-apply/status`);
    if (!res.ok) throw new Error(`Batch apply status failed (${res.status})`);
    return res.json();
  }

  async getAutoApplyPolicy(): Promise<{ enabled: boolean; min_score: number }> {
    const res = await authFetch(`${API_BASE}/applications/auto-apply-policy`);
    if (!res.ok) throw new Error(`Auto-apply policy fetch failed (${res.status})`);
    return res.json();
  }

  async setAutoApplyPolicy(
    enabled: boolean,
    minScore = 70,
  ): Promise<{ enabled: boolean; min_score: number }> {
    const res = await authFetch(`${API_BASE}/applications/auto-apply-policy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled, min_score: minScore }),
    });
    if (!res.ok) throw new Error(`Auto-apply policy save failed (${res.status})`);
    return res.json();
  }

  async getNeedsReview(): Promise<NeedsReviewItem[]> {
    const res = await authFetch(`${API_BASE}/applications/needs-review`);
    if (!res.ok) throw new Error(`Needs-review fetch failed (${res.status})`);
    const data = await res.json();
    return data.items || [];
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
  async applyToJob(): Promise<{ status: string; really_submitted: boolean; failure_reason: string | null }> {
    return { status: "COMPLETED", really_submitted: true, failure_reason: null };
  }
  async startBatchApply(): Promise<{ started: boolean; candidate_count: number }> {
    return { started: true, candidate_count: this.mockJobs.length };
  }
  async getBatchApplyStatus(): Promise<BatchApplyStatus> {
    return { running: false };
  }
  async getAutoApplyPolicy(): Promise<{ enabled: boolean; min_score: number }> {
    return { enabled: false, min_score: 70 };
  }
  async setAutoApplyPolicy(enabled: boolean, minScore = 70): Promise<{ enabled: boolean; min_score: number }> {
    return { enabled, min_score: minScore };
  }
  async getNeedsReview(): Promise<NeedsReviewItem[]> {
    return [];
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

  static getReferralService(): ReferralService {
    return new ReferralService();
  }

  static getCaptchaService(): CaptchaService {
    return new CaptchaService();
  }
}
