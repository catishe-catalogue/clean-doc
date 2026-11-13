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

export interface PlanPriceResponse {
  plan: string;
  price_month_rub: number;
  price_year_rub: number;
}

export interface CreateCheckoutRequest {
  billing_period: 'month' | 'year';
}

export interface CheckoutResponse {
  payment_id: string;
  confirmation_url: string;
  amount_rub: number;
}

export interface CreateInvoiceRequest {
  inn: string;
  billing_period?: 'year';
}

export interface InvoiceResponse {
  id: string;
  invoice_number: string;
  company_name: string;
  amount_rub: number;
  pdf_download_url: string;
  status: 'pending' | 'paid' | 'cancelled';
  created_at: string;
}

export interface SubscriptionStatusResponse {
  status: 'active' | 'past_due' | 'cancelled';
  plan: string;
  billing_period: string;
  current_period_end: string;
}
