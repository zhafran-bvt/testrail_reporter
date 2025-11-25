export type Plan = { id: number; name?: string; created_on?: number; is_completed?: number };
export type Run = { id: number; name?: string; is_completed?: number; suite_name?: string };
export type CaseItem = { id: number; title?: string; refs?: string; updated_on?: number; priority_id?: number; section_id?: number };
export type ReportJobMeta = {
  generated_at?: string;
  duration_ms?: number;
  api_call_count?: number;
  api_calls?: Array<{ kind?: string; endpoint?: string; elapsed_ms?: number; status?: string }>;
  stage?: string;
  stage_payload?: Record<string, any>;
  progress_updates?: Array<{ stage?: string; payload?: any }>;
};
export type ReportJob = {
  id?: string;
  status?: string;
  queue_position?: number | null;
  path?: string;
  url?: string;
  error?: string;
  meta?: ReportJobMeta;
  params?: any;
  started_at?: string;
};
export type AppConfig = {
  defaultSuiteId?: number | null;
  defaultSectionId?: number | null;
};
