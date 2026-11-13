'use client';
import React from 'react';
import Link from 'next/link';
import { Zap, X, ShieldCheck } from 'lucide-react';
import { useConverterStore } from '@/store/useConverterStore';

export const UpsellModal: React.FC = () => {
  const { isPreviewOnly, status, reset } = useConverterStore();

  if (!isPreviewOnly || status !== 'completed') return null;

  return (
    <div className="fixed inset-0 bg-ink/60 flex items-center justify-center z-50 p-4">
      <div className="bg-cotton rounded-stock p-6 sm:p-8 max-w-md w-full border border-rule-2 stock">
        <div className="flex justify-between items-start mb-4">
          <div className="w-10 h-10 rounded-stock bg-paper border border-rule-2 flex items-center justify-center shadow-card">
            <Zap className="w-5 h-5 text-paid" />
          </div>
          <button
            onClick={reset}
            className="text-muted hover:text-ink p-1 rounded focus-visible:outline-2 focus-visible:outline-focus"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <h3 className="text-lg font-medium text-ink mb-2">
          Документ содержит более 2 страниц
        </h3>
        <p className="text-muted mb-5 text-sm leading-relaxed">
          На базовом тарифе доступна конвертация первых двух страниц. Для полной обработки многостраничных документов
          без ограничений перейдите на тариф PRO.
        </p>

        <div className="p-3.5 rounded-stock bg-paper-2 border border-rule-2 text-xs text-ink mb-6 space-y-1.5">
          <div className="flex items-center gap-1.5 font-medium text-ink">
            <ShieldCheck className="w-4 h-4 text-paid" />
            <span>Возможности тарифа PRO:</span>
          </div>
          <p className="text-muted">• Полная конвертация документов до 250 страниц и 100 МБ</p>
          <p className="text-muted">• Приоритетная очередь обработки в воркерах</p>
          <p className="text-muted">• Распознавание сканированных документов через OCR</p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href="/pricing"
            className="btn-board flex-1 text-center py-2.5 text-xs sm:text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
          >
            Перейти к тарифам
          </Link>
          <button
            onClick={reset}
            className="btn-letterpress flex-1 text-xs sm:text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};
