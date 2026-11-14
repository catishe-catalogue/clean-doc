'use client';

import React from 'react';
import Image from 'next/image';
import { Eye } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const PreviewCards: React.FC = () => {
  const { previewUrls } = useConverterStore();

  if (!previewUrls || previewUrls.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 space-y-4">
      <div className="flex items-center gap-2 text-sm font-medium text-ink">
        <Eye className="w-4 h-4 text-muted" />
        <span>Предварительный просмотр первых страниц (150 DPI)</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-[repeat(auto-fit,minmax(0,1fr))] gap-4">
        {previewUrls.map((url, idx) => {
          const imgSrc = url.startsWith('http') || url.startsWith('/') ? url : `/${url}`;
          return (
            <div
              key={idx}
              className="group relative border border-rule-2 rounded-stock overflow-hidden stock transition-transform duration-150 ease-out hover:-translate-y-[1px]"
            >
              <div className="aspect-[1/1.414] bg-paper-2 flex items-center justify-center overflow-hidden p-2">
                <Image
                  src={imgSrc}
                  alt={`Страница ${idx + 1}`}
                  width={1240}
                  height={1754}
                  className="w-full h-full object-contain"
                  priority={idx === 0}
                  unoptimized
                />
              </div>
              <div className="p-2.5 text-center text-xs font-mono text-muted bg-paper border-t border-rule-2">
                Страница {idx + 1}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
