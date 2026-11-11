'use client';

import React from 'react';
import { Eye } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const PreviewCards: React.FC = () => {
  const { previewUrls } = useConverterStore();

  if (!previewUrls || previewUrls.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        <Eye className="w-4 h-4 text-blue-600" />
        <span>Предварительный просмотр первых страниц (150 DPI)</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {previewUrls.map((url, idx) => (
          <div key={idx} className="group relative border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow">
            <div className="aspect-[1/1.414] bg-slate-100 flex items-center justify-center overflow-hidden">
              <img
                src={url}
                alt={`Страница ${idx + 1}`}
                className="w-full h-full object-contain"
                loading="lazy"
              />
            </div>
            <div className="p-2 text-center text-xs font-medium text-slate-500 bg-slate-50 border-t border-slate-100">
              Страница {idx + 1}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
