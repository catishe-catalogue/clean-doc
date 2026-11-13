'use client';
import React from 'react';
import Link from 'next/link';
import { Zap, X, ShieldCheck } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const UpsellModal: React.FC = () => {
  const { isPreviewOnly, status, reset } = useConverterStore();

  if (!isPreviewOnly || status !== 'completed') return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 md:p-8 max-w-md w-full shadow-2xl border border-slate-100">
        <div className="flex justify-between items-start mb-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center">
            <Zap className="w-6 h-6 text-blue-600" />
          </div>
          <button
            onClick={reset}
            className="text-slate-400 hover:text-slate-600 p-1"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <h3 className="text-xl font-bold text-slate-900 mb-2">
          Документ содержит более 2 страниц
        </h3>
        <p className="text-slate-600 mb-5 text-sm leading-relaxed">
          На бесплатном тарифе доступно скачивание первых 2 страниц. Для полной конвертации всего
          документа без ограничений оформите подписку PRO.
        </p>

        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 mb-6 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold text-slate-800">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Преимущества тарифа PRO:</span>
          </div>
          <p>• Полная конвертация файлов до 250 страниц и 100 МБ</p>
          <p>• Приоритетная очередь с максимальной скоростью</p>
          <p>• Доступ к OCR-распознаванию сканов</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href="/pricing"
            className="flex-1 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-center py-3 rounded-xl font-medium text-sm transition-colors shadow-sm"
          >
            Перейти к тарифам
          </Link>
          <button
            onClick={reset}
            className="flex-1 border border-slate-200 text-slate-600 hover:bg-slate-50 py-3 rounded-xl font-medium text-sm transition-colors"
          >
            Скачать превью
          </button>
        </div>
      </div>
    </div>
  );
};
