export type DiscoveryPreferenceValues = {
  roles?: string[]; skills?: string[]; employment_types?: string[]; seniority?: string[];
  cities?: string[]; countries?: string[]; remote?: boolean; remote_country?: string;
  excluded_companies?: string[]; excluded_keywords?: string[]; portfolio_urls?: string[];
  github_url?: string; projects?: CandidateProject[]; max_age_days?: number | null;
  search_depth?: string; max_queries?: number; results_per_source?: number;
  notifications_enabled?: boolean; notification_min_score?: number; notification_hours?: number;
};

export interface JobResearch {
  recommendation_status?: "recommended" | "needs_review" | "excluded";
  recommendation_reasons?: string[];
  state?: string; verification_status?: string; experience_level?: string;
  first_discovered_at?: string; last_seen_at?: string; posted_at?: string; deadline?: string;
  viewed_at?: string; remote_eligibility?: string; application_url?: string;
  enrichment_state?: string; eligibility_concerns?: string[]; exclusion_reasons?: string[];
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface ExperienceItem {
  title: string;
  company: string;
  start_date: string | null;
  end_date: string | null;
  bullets: string[];
}

export interface EducationItem {
  degree: string;
  school: string;
  year: string | null;
}

export interface CandidateProject { name?: string; description?: string; technologies?: string[]; }

export interface ResumeProfile {
  target_roles?: string[];
  projects?: CandidateProject[];
  portfolio_urls?: string[];
  github_url?: string | null;
  summary: string;
  skills: string[];
  experience: ExperienceItem[];
  education: EducationItem[];
}

export interface Resume {
  id: string;
  original_filename: string;
  file_type: string;
  is_primary: boolean;
  parse_status: "pending" | "parsing" | "parsed" | "failed";
  parse_error: string | null;
  structured_profile: ResumeProfile | null;
}

export interface Job {
  research?: JobResearch;
  id: string;
  source_type: "url" | "text" | "crawl";
  source_url: string | null;
  raw_input_text: string;
  title: string | null;
  company: string | null;
  location: string | null;
  salary_range: string | null;
  employment_type: string | null;
  work_mode: string | null;
  description_text: string | null;
  requirements: string[] | null;
  contact_email: string | null;
  extraction_status: "pending" | "extracting" | "extracted" | "failed";
  extraction_error: string | null;
}

export interface Match {
  details?: { relevant_projects?: string[]; eligibility_concerns?: string[]; score_label?: string };
  id: string;
  job_id: string;
  resume_id: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  rationale: string | null;
}

export interface GeneratedDocument {
  id: string;
  job_id: string;
  resume_id: string;
  doc_type: "cover_letter" | "resume_bullets";
  content: string;
  model_used: string;
}

export type ApplicationStatus = "saved" | "applied" | "interview" | "offer" | "rejected";

export interface Application {
  id: string;
  job_id: string;
  resume_id: string | null;
  status: ApplicationStatus;
  applied_at: string | null;
  notes: string | null;
  followup_opt_out: boolean;
  followup_count: number;
  last_followup_at: string | null;
  next_followup_due_at: string | null;
}

export interface FollowUp {
  id: string;
  sent_at: string;
  status: "sent" | "failed";
  subject: string;
  error: string | null;
}

export interface EmailAccount {
  id: string;
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  from_name: string | null;
  from_email: string;
  use_tls: boolean;
  last_tested_at: string | null;
  last_test_ok: boolean | null;
}

export interface EmailAccountInput {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  from_name: string | null;
  from_email: string;
  use_tls: boolean;
}

export interface EmailTestResult {
  ok: boolean;
  error: string | null;
}

export interface DashboardStats {
  saved: number;
  applied: number;
  interview: number;
  offer: number;
  rejected: number;
  total: number;
}

export interface Profile {
  preferences?: DiscoveryPreferenceValues;
  portfolio_data?: Record<string, unknown>;
  country: string | null;
  city: string | null;
  search_keywords: string | null;
  crawl_enabled: boolean;
  followup_enabled: boolean;
  followup_first_days: number;
  followup_interval_days: number;
  followup_max_count: number;
}

export interface CrawlSourceResult {
  source: string;
  tier: string | null;
  jobs_found: number;
  error: string | null;
}

export interface CrawlRun {
  intent?: string;
  plan?: Record<string, unknown>;
  id: string;
  started_at: string;
  finished_at: string | null;
  status: "success" | "partial" | "failed" | "queued" | "running" | "cancelling" | "cancelled" | "interrupted";
  jobs_found: number;
  jobs_created: number;
  source_results: CrawlSourceResult[];
  error_message: string | null;
}

export interface DashboardJobRow {
  research?: JobResearch;
  job_id: string;
  title: string | null;
  company: string | null;
  location: string | null;
  employment_type: string | null;
  work_mode: string | null;
  extraction_status: string;
  match_score: number | null;
  missing_skills: string[] | null;
  application_id: string | null;
  application_status: ApplicationStatus | null;
}

