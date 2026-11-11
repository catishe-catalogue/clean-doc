'use client';
import React from 'react';
import { Loader2 } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const ProcessingView: React.FC = () => {
  const { status, progress, currentStep, pageCurrent, pageTotal } = useConverterStore();

  if (status !== 'processing' && status !== 'queued') return null;

  return (
    <div className="mt-6 space-y-3">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
        <span>{currentStep}</span>
        {pageCurrent && pageTotal && (
          <span className="text-slate-400">({pageCurrent}/{pageTotal} стр.)</span>
        )}
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-xs text-right text-slate-400">{progress}%</p>
    </div>
  );
};
