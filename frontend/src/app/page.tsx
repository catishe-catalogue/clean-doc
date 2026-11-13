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
import { ShieldCheck, TableProperties, Sparkles } from 'lucide-react';

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
    <div className="min-h-screen flex flex-col bg-paper text-ink">
      <Header />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-12">
        {/* Hero Section */}
        <div className="text-center mb-8 max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-4xl font-semibold tracking-tight text-ink">
            Конвертер PDF в Word и Excel
          </h1>
          <p className="text-muted mt-2 text-sm sm:text-base leading-relaxed">
            Точное сохранение верстки таблиц с соблюдением требований 152-ФЗ на серверах РФ.
          </p>
        </div>

        {/* Workbench Card on Cotton Stock */}
        <div className="rounded-stock bg-cotton border border-rule-2 stock p-6 sm:p-8 space-y-6">
          <Dropzone />

          {file && status === 'idle' && (
            <div className="pt-2 border-t border-rule-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <p className="text-xs font-medium text-muted mb-2">Формат выгрузки:</p>
                <FormatSelector />
              </div>
              <button
                onClick={handleConvert}
                className="btn-board w-full sm:w-auto text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
              >
                Конвертировать
              </button>
            </div>
          )}

          {status === 'failed' && (
            <div className="bg-error/10 border border-error/30 rounded-stock p-4 text-xs sm:text-sm text-error flex items-center justify-between">
              <span>{useConverterStore.getState().errorMessage || 'Ошибка конвертации'}</span>
              <button
                onClick={reset}
                className="btn-letterpress ml-3 text-xs shrink-0 focus-visible:outline-2 focus-visible:outline-focus"
              >
                Попробовать снова
              </button>
            </div>
          )}

          <ProcessingView />
        </div>

        {/* Hallmark Floor 8: No invented metrics. True architectural guarantees */}
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2">
            <div className="flex items-center gap-2 mb-1.5 text-ink font-medium text-xs sm:text-sm">
              <TableProperties className="w-4 h-4 text-paid" />
              <span>Табличная сетка</span>
            </div>
            <p className="text-xs text-muted leading-relaxed">
              Координатный разбор Docling сохраняет ячейки, спаны и форматирование без смещения.
            </p>
          </div>

          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2">
            <div className="flex items-center gap-2 mb-1.5 text-ink font-medium text-xs sm:text-sm">
              <ShieldCheck className="w-4 h-4 text-paid" />
              <span>Безопасность 152-ФЗ</span>
            </div>
            <p className="text-xs text-muted leading-relaxed">
              Обработка на изолированных VDS в РФ без сохранения содержимого документов в логах.
            </p>
          </div>

          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2">
            <div className="flex items-center gap-2 mb-1.5 text-ink font-medium text-xs sm:text-sm">
              <Sparkles className="w-4 h-4 text-paid" />
              <span>Быстрое превью</span>
            </div>
            <p className="text-xs text-muted leading-relaxed">
              Мгновенная нарезка первых страниц в 150 DPI через PyMuPDF до тяжелой конвертации.
            </p>
          </div>
        </div>

        <PreviewCards />
        <DownloadCard />
      </main>

      <Footer />
      <UpsellModal />
    </div>
  );
}
