'use client';

import React, { useState } from 'react';
import { Check, ShieldCheck, Zap, Building2, CreditCard } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { apiClient } from '@/lib/api-client';
import { CheckoutResponse } from '@/lib/types';

interface PricingCardsProps {
  onSelectB2B: () => void;
  onRequireAuth: () => void;
}

export const PricingCards: React.FC<PricingCardsProps> = ({ onSelectB2B, onRequireAuth }) => {
  const { user, accessToken } = useAuthStore();
  const [loadingPeriod, setLoadingPeriod] = useState<'month' | 'year' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleCheckout = async (period: 'month' | 'year') => {
    if (!accessToken) {
      onRequireAuth();
      return;
    }

    setLoadingPeriod(period);
    setErrorMessage(null);

    try {
      const resp = await apiClient<CheckoutResponse>('/api/v1/billing/create-checkout', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ billing_period: period }),
      });

      if (resp.confirmation_url) {
        window.location.href = resp.confirmation_url;
      }
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Не удалось инициировать оплату через платежный шлюз'
      );
    } finally {
      setLoadingPeriod(null);
    }
  };

  const isPro = user?.plan === 'pro';

  return (
    <div className="space-y-6">
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800">
          {errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Тариф Free */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Базовый
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 font-medium">
                Free
              </span>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-1">0 ₽</h3>
            <p className="text-xs text-slate-500 mb-6">Бессрочный доступ для нерегулярных задач</p>

            <ul className="space-y-3 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>3 конвертации в сутки (1 гость + 2 после входа)</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Размер документа до 10 МБ</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Превью первых 2 страниц для многостраничных PDF</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Хранение и автоудаление через 2 часа (152-ФЗ)</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 pt-4 border-t border-slate-100">
            <span className="block text-center text-sm font-medium text-slate-500 py-2.5">
              {!isPro ? 'Текущий тариф' : 'Доступно'}
            </span>
          </div>
        </div>

        {/* Тариф PRO Месяц */}
        <div className="rounded-2xl border-2 border-blue-600 bg-white p-6 flex flex-col justify-between shadow-md relative">
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-semibold px-3 py-0.5 rounded-full shadow-sm">
            Популярный выбор
          </div>
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
                Для специалистов
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 font-medium">
                PRO 1 месяц
              </span>
            </div>
            <div className="flex items-baseline gap-1 mb-1">
              <h3 className="text-2xl font-bold text-slate-900">1 490 ₽</h3>
              <span className="text-xs text-slate-500">/ месяц</span>
            </div>
            <p className="text-xs text-slate-500 mb-6">Полная конвертация без ограничений объема</p>

            <ul className="space-y-3 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <span className="font-medium text-slate-900">Безлимитная конвертация</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Документы до 100 МБ и до 250 страниц</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>OCR движок Docling (распознавание сканов)</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Приоритетная очередь обработки</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Оплата картами РФ и СБП (ЮKassa, чек 54-ФЗ)</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 pt-4 border-t border-slate-100">
            {isPro ? (
              <span className="block text-center text-sm font-semibold text-blue-700 bg-blue-50 py-2.5 rounded-xl">
                Ваш текущий тариф активен
              </span>
            ) : (
              <button
                onClick={() => handleCheckout('month')}
                disabled={loadingPeriod !== null}
                className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white py-3 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                <CreditCard className="w-4 h-4" />
                {loadingPeriod === 'month' ? 'Подготовка оплаты...' : 'Оплатить картой или СБП'}
              </button>
            )}
          </div>
        </div>

        {/* Тариф PRO Год / B2B */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Для компаний и ИП
              </span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium">
                Экономия 33%
              </span>
            </div>
            <div className="flex items-baseline gap-1 mb-1">
              <h3 className="text-2xl font-bold text-slate-900">11 900 ₽</h3>
              <span className="text-xs text-slate-500">/ год</span>
            </div>
            <p className="text-xs text-slate-500 mb-6">Безналичный расчет с закрывающими актами</p>

            <ul className="space-y-3 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <Building2 className="w-4 h-4 text-slate-700 shrink-0 mt-0.5" />
                <span className="font-medium text-slate-900">Счет на оплату для юрлиц (DaData)</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Все преимущества тарифа PRO на 365 дней</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Закрывающие акты и электронный документооборот</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Выделенная линия технической поддержки</span>
              </li>
              <li className="flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>Договор-оферта и полное соответствие 152-ФЗ</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 pt-4 border-t border-slate-100 space-y-2">
            <button
              onClick={onSelectB2B}
              className="w-full bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white py-3 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2"
            >
              <Building2 className="w-4 h-4" />
              Выставить счет по ИНН
            </button>
            <button
              onClick={() => handleCheckout('year')}
              disabled={loadingPeriod !== null}
              className="w-full border border-slate-200 hover:bg-slate-50 text-slate-700 py-2.5 rounded-xl font-medium text-xs transition-colors"
            >
              {loadingPeriod === 'year' ? 'Подготовка...' : 'Оплатить картой за год (11 900 ₽)'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
