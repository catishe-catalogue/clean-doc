'use client';

import React, { useCallback } from 'react';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { Dropzone } from '@/components/converter/Dropzone';
import { FormatSelector } from '@/components/converter/FormatSelector';
import { ProcessingView } from '@/components/converter/ProcessingView';
import { PreviewCards } from '@/components/converter/PreviewCards';
import { DownloadCard } from '@/components/converter/DownloadCard';
import { UpsellModal } from '@/components/converter/UpsellModal';
import { useConverterStore } from '@/store/useConverterStore';
import { useAuthStore } from '@/store/useAuthStore';
import { useSSEStream } from '@/lib/sse-client';
import { apiClient } from '@/lib/api-client';
import { SSEProgressPayload, UploadResponse } from '@/lib/types';

export default function HomePage() {
  const { file, targetFormat, jobId, status, startJob, updateFromSSE, setError, reset } = useConverterStore();
  const { accessToken } = useAuthStore();

  const streamUrl = jobId
    ? `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/convert/jobs/${jobId}/stream`
    : null;

  const handleSSEMessage = useCallback(
    (payload: SSEProgressPayload) => updateFromSSE(payload),
    [updateFromSSE],
  );

  const handleSSEError = useCallback(
    () => setError('Потеряно соединение с сервером. Попробуйте снова.'),
    [setError],
  );

  useSSEStream(
    status === 'queued' || status === 'processing' ? streamUrl : null,
    handleSSEMessage,
    handleSSEError,
  );

  const handleConvert = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_format', targetFormat);

    try {
      const headers: Record<string, string> = {};
      if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

      const resp = await apiClient<UploadResponse>('/api/v1/convert/upload', {
        method: 'POST',
        body: formData,
        headers,
      });
      startJob(resp.job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка при загрузке файла');
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header />
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-10">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">PDF в Word и Excel</h1>
          <p className="text-slate-600 mt-2 text-sm">
            Конвертация с сохранением верстки. Данные хранятся в РФ (152-ФЗ).
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
          <Dropzone />

          {file && status === 'idle' && (
            <>
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Формат результата:</p>
                <FormatSelector />
              </div>
              <button
                onClick={handleConvert}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-medium transition-colors"
              >
                Конвертировать
              </button>
            </>
          )}

          {status === 'failed' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              {useConverterStore.getState().errorMessage || 'Ошибка конвертации'}
              <button onClick={reset} className="ml-2 underline">Попробовать снова</button>
            </div>
          )}

          <ProcessingView />
        </div>

        <PreviewCards />
        <DownloadCard />
      </main>
      <Footer />
      <UpsellModal />
    </div>
  );
}
