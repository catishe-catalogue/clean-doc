'use client';
import React from 'react';
import { Download } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const DownloadCard: React.FC = () => {
  const { downloadUrl, status, isPreviewOnly } = useConverterStore();

  if (status !== 'completed' || isPreviewOnly || !downloadUrl) return null;

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const fullDownloadUrl = downloadUrl.startsWith('http') ? downloadUrl : `${baseUrl}${downloadUrl}`;

  return (
    <div className="mt-6 flex justify-center">
      <a
        href={fullDownloadUrl}
        download
        className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-xl font-medium transition-colors"
      >
        <Download className="w-5 h-5" />
        Скачать результат
      </a>
    </div>
  );
};
