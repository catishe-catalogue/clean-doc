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
        <div className="p-4 rounded-stock bg-error/10 border border-error/30 text-xs sm:text-sm text-error">
          {errorMessage}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Тариф Free */}
        <div className="rounded-stock border border-rule-2 bg-cotton p-6 flex flex-col justify-between stock">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-medium text-muted">
                Базовый доступ
              </span>
              <span className="text-xs px-2 py-0.5 rounded-stock bg-paper border border-rule-2 text-muted font-mono">
                Free
              </span>
            </div>
            <h3 className="text-2xl sm:text-3xl font-semibold text-ink font-mono tabular-nums mb-1">0 ₽</h3>
            <p className="text-xs text-muted mb-6">Бессрочный доступ для разовых задач</p>

            <ul className="space-y-3 text-xs sm:text-sm text-ink">
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>3 конвертации в сутки (1 гость + 2 после входа)</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Размер документа до 10 МБ</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Превью первых 2 страниц для многостраничных PDF</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Хранение и автоудаление через 2 часа (152-ФЗ)</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 pt-4 border-t border-rule-2">
            <span className="block text-center text-xs font-medium text-muted py-2">
              {!isPro ? 'Текущий тариф' : 'Доступно'}
            </span>
          </div>
        </div>

        {/* Тариф PRO Месяц */}
        <div className="rounded-stock border border-ink bg-cotton p-6 flex flex-col justify-between stock relative">
          <div className="absolute -top-3 left-6 bg-board text-board-type text-xs font-medium px-2.5 py-0.5 rounded-stock shadow-card">
            Рекомендуемый
          </div>
          <div>
            <div className="flex items-center justify-between mb-4 mt-1">
              <span className="text-xs font-medium text-ink">
                Для специалистов
              </span>
              <span className="text-xs px-2 py-0.5 rounded-stock bg-paper border border-rule-2 text-ink font-mono">
                PRO 1 месяц
              </span>
            </div>
            <div className="flex items-baseline gap-1.5 mb-1">
              <h3 className="text-2xl sm:text-3xl font-semibold text-ink font-mono tabular-nums">1 490 ₽</h3>
              <span className="text-xs text-muted">/ месяц</span>
            </div>
            <p className="text-xs text-muted mb-6">Полная конвертация без ограничений объема</p>

            <ul className="space-y-3 text-xs sm:text-sm text-ink">
              <li className="flex items-start gap-2">
                <Zap className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span className="font-medium text-ink">Безлимитная конвертация</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Документы до 100 МБ и до 250 страниц</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Встроенное OCR распознавание сканов</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Приоритетная очередь обработки</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Оплата картами РФ и СБП (кассовый чек 54-ФЗ)</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 pt-4 border-t border-rule-2">
            {isPro ? (
              <span className="block text-center text-xs sm:text-sm font-medium text-ink bg-paper-2 border border-rule-2 py-2 rounded-stock">
                Ваш текущий тариф активен
              </span>
            ) : (
              <button
                onClick={() => handleCheckout('month')}
                disabled={loadingPeriod !== null}
                className="btn-board w-full py-2.5 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 focus-visible:outline-2 focus-visible:outline-focus"
              >
                <CreditCard className="w-4 h-4" />
                <span>{loadingPeriod === 'month' ? 'Подготовка оплаты...' : 'Оплатить картой или СБП'}</span>
              </button>
            )}
          </div>
        </div>

        {/* Тариф PRO Год / B2B */}
        <div className="rounded-stock border border-rule-2 bg-cotton p-6 flex flex-col justify-between stock">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-medium text-muted">
                Для компаний и ИП
              </span>
              <span className="text-xs px-2 py-0.5 rounded-stock bg-paper border border-rule-2 text-paid font-mono">
                Скидка 33%
              </span>
            </div>
            <div className="flex items-baseline gap-1.5 mb-1">
              <h3 className="text-2xl sm:text-3xl font-semibold text-ink font-mono tabular-nums">11 900 ₽</h3>
              <span className="text-xs text-muted">/ год</span>
            </div>
            <p className="text-xs text-muted mb-6">Безналичный расчет с закрывающими документами</p>

            <ul className="space-y-3 text-xs sm:text-sm text-ink">
              <li className="flex items-start gap-2">
                <Building2 className="w-4 h-4 text-ink shrink-0 mt-0.5" />
                <span className="font-medium text-ink">Счет на оплату для юрлиц (DaData)</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Все преимущества тарифа PRO на 365 дней</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Закрывающие акты через ЭДО (Диадок / СБИС)</span>
              </li>
              <li className="flex items-start gap-2">
                <Check className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Выделенная линия технической поддержки</span>
              </li>
              <li className="flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-paid shrink-0 mt-0.5" />
                <span>Договор-оферта и соответствие 152-ФЗ</span>
              </li>
            </ul>
          </div>

          <div className="mt-8 pt-4 border-t border-rule-2 space-y-2.5">
            <button
              onClick={onSelectB2B}
              className="btn-letterpress w-full py-2.5 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 focus-visible:outline-2 focus-visible:outline-focus"
            >
              <Building2 className="w-4 h-4" />
              <span>Выставить счет по ИНН</span>
            </button>
            <button
              onClick={() => handleCheckout('year')}
              disabled={loadingPeriod !== null}
              className="w-full text-xs text-muted hover:text-ink py-1.5 text-center transition-colors focus-visible:outline-2 focus-visible:outline-focus"
            >
              {loadingPeriod === 'year' ? 'Подготовка…' : 'Оплатить картой за год (11 900 ₽)'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
