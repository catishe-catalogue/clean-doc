'use client';
import React from 'react';
import { Zap, X } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const UpsellModal: React.FC = () => {
  const { isPreviewOnly, status, reset } = useConverterStore();

  if (!isPreviewOnly || status !== 'completed') return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
        <div className="flex justify-between items-start mb-4">
          <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
            <Zap className="w-6 h-6 text-blue-600" />
          </div>
          <button onClick={reset} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <h3 className="text-xl font-bold text-slate-900 mb-2">Документ содержит более 2 страниц</h3>
        <p className="text-slate-600 mb-6 text-sm leading-relaxed">
          Бесплатный тариф позволяет скачать только первые 2 страницы. Перейдите на PRO для полной
          конвертации без ограничений.
        </p>
        <div className="flex gap-3">
          <a
            href="/pricing"
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-center py-3 rounded-xl font-medium transition-colors"
          >
            Перейти на PRO
          </a>
          <button
            onClick={reset}
            className="flex-1 border border-slate-200 text-slate-600 hover:bg-slate-50 py-3 rounded-xl font-medium transition-colors"
          >
            Скачать превью
          </button>
        </div>
      </div>
    </div>
  );
};
