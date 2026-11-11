import { create } from 'zustand';
import { TargetFormat, JobStatus, SSEProgressPayload } from '@/lib/types';

interface ConverterState {
  file: File | null;
  targetFormat: TargetFormat;
  jobId: string | null;
  status: JobStatus | 'idle';
  progress: number;
  currentStep: string;
  pageCurrent?: number;
  pageTotal?: number;
  previewUrls: string[];
  downloadUrl: string | null;
  isPreviewOnly: boolean;
  errorMessage: string | null;

  setFile: (file: File | null) => void;
  setTargetFormat: (format: TargetFormat) => void;
  startJob: (jobId: string) => void;
  updateFromSSE: (payload: SSEProgressPayload) => void;
  setError: (msg: string) => void;
  reset: () => void;
}

export const useConverterStore = create<ConverterState>((set) => ({
  file: null,
  targetFormat: 'docx',
  jobId: null,
  status: 'idle',
  progress: 0,
  currentStep: '',
  previewUrls: [],
  downloadUrl: null,
  isPreviewOnly: false,
  errorMessage: null,

  setFile: (file) =>
    set({ file, errorMessage: null, status: 'idle', progress: 0, previewUrls: [], downloadUrl: null }),
  setTargetFormat: (targetFormat) => set({ targetFormat }),
  startJob: (jobId) => set({ jobId, status: 'queued', progress: 5, currentStep: 'Постановка в очередь...' }),
  updateFromSSE: (payload) =>
    set({
      status: payload.status,
      progress: payload.progress_percent,
      currentStep: payload.current_step,
      pageCurrent: payload.page_current,
      pageTotal: payload.page_total,
      previewUrls: payload.preview_urls ?? [],
      downloadUrl: payload.download_url ?? null,
      isPreviewOnly: Boolean(payload.is_preview_only),
      errorMessage: payload.error ?? null,
    }),
  setError: (errorMessage) => set({ status: 'failed', errorMessage, progress: 0 }),
  reset: () =>
    set({
      file: null,
      jobId: null,
      status: 'idle',
      progress: 0,
      currentStep: '',
      previewUrls: [],
      downloadUrl: null,
      isPreviewOnly: false,
      errorMessage: null,
    }),
}));
