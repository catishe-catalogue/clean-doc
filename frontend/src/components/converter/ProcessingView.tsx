'use client';
import React from 'react';
import { Loader2 } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const ProcessingView: React.FC = () => {
  const { status, progress, currentStep, pageCurrent, pageTotal } = useConverterStore();

  if (status !== 'processing' && status !== 'queued') return null;

  return (
    <div className="mt-6 space-y-3.5 p-4 rounded-stock bg-paper-2 border border-rule-2">
      <div className="flex items-center justify-between text-xs sm:text-sm text-ink">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-ink" />
          <span className="font-medium">{currentStep}</span>
          {pageCurrent && pageTotal && (
            <span className="text-muted font-mono tabular-nums">
              (стр. {pageCurrent} из {pageTotal})
            </span>
          )}
        </div>
        <span className="font-mono tabular-nums text-xs font-medium text-muted">{progress}%</span>
      </div>

      <div className="w-full bg-paper-3 rounded-full h-2 overflow-hidden border border-rule-2">
        <div
          className="bg-board h-full transition-transform duration-300 origin-left"
          style={{ width: `${Math.max(progress, 2)}%` }}
        />
      </div>
    </div>
  );
};
