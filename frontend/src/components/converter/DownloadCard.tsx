'use client';
import React from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';
import { useAuthStore } from '@/store/useAuthStore';

export const DownloadCard: React.FC = () => {
  const { downloadUrl, status, isPreviewOnly, reset, targetFormat } = useConverterStore();
  const { accessToken } = useAuthStore();

  if (status !== 'completed' || isPreviewOnly || !downloadUrl) return null;

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  let fullDownloadUrl = downloadUrl.startsWith('http') ? downloadUrl : `${baseUrl}${downloadUrl}`;
  if (accessToken && !fullDownloadUrl.includes('token=')) {
    fullDownloadUrl += `${fullDownloadUrl.includes('?') ? '&' : '?'}token=${encodeURIComponent(accessToken)}`;
  }

  const formatUpper = (targetFormat || 'docx').toUpperCase();

  return (
    <div className="mt-8 p-6 rounded-stock bg-cotton border border-rule-2 stock flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>
        <h4 className="text-base font-medium text-ink">Документ готов к скачиванию</h4>
        <p className="text-xs text-muted mt-0.5">
          Файл сформирован с сохранением табличной структуры и разметки.
        </p>
      </div>
      <div className="flex items-center gap-3 w-full sm:w-auto">
        <a
          href={fullDownloadUrl}
          download
          className="btn-board flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
        >
          <Download className="w-4 h-4" />
          <span>Скачать {formatUpper}</span>
        </a>
        <button
          onClick={reset}
          className="btn-letterpress inline-flex items-center justify-center gap-1.5 text-xs text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus"
          title="Сконвертировать другой файл"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Еще</span>
        </button>
      </div>
    </div>
  );
};
