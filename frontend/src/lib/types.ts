export type TargetFormat = 'docx' | 'xlsx';
export type JobStatus = 'pending' | 'queued' | 'processing' | 'completed' | 'failed';

export interface SSEProgressPayload {
  job_id: string;
  status: JobStatus;
  progress_percent: number;
  current_step: string;
  page_current?: number;
  page_total?: number;
  preview_urls?: string[];
  download_url?: string | null;
  is_preview_only?: boolean;
  error?: string | null;
}

export interface UserProfile {
  id: string;
  email: string | null;
  telegram_username: string | null;
  plan: 'free' | 'pro';
  conversions_today: number;
  conversions_limit: number;
  is_blocked: boolean;
  created_at: string;
}

export interface UploadResponse {
  job_id: string;
  status: 'queued';
  stream_url: string;
}
