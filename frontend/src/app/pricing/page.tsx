'use client';

import React, { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PricingCards } from '@/components/billing/PricingCards';
import { B2BInvoiceForm } from '@/components/billing/B2BInvoiceForm';
import { AuthModal } from '@/components/auth/AuthModal';
import { useAuthStore } from '@/store/useAuthStore';
import { apiClient } from '@/lib/api-client';
import { ShieldCheck, Server, Clock, AlertTriangle, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function PricingPage() {
  const { user, accessToken, updatePlan } = useAuthStore();
  const [authOpen, setAuthOpen] = useState(false);
  const [showB2BForm, setShowB2BForm] = useState(false);
  const [cancellingSub, setCancellingSub] = useState(false);
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);

  const handleCancelSub = async () => {
    if (!accessToken) return;
    if (!window.confirm('Вы действительно хотите отменить автопродление подписки PRO?')) {
      return;
    }

    setCancellingSub(true);
    setCancelMessage(null);
    try {
      await apiClient('/api/v1/billing/cancel-subscription', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      setCancelMessage('Автопродление подписки успешно отменено.');
      updatePlan('free');
    } catch (err: unknown) {
      setCancelMessage(
        err instanceof Error ? err.message : 'Не удалось отменить подписку. Обратитесь в поддержку.'
      );
    } finally {
      setCancellingSub(false);
    }
  };

  const isPro = user?.plan === 'pro';

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-10 md:py-14 space-y-10">
        {/* Хлебные крошки / Назад */}
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Вернуться к конвертеру
          </Link>
        </div>

        {/* Hero-блок страницы тарифов */}
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight">
            Тарифные планы и оплата
          </h1>
          <p className="text-slate-600 text-sm md:text-base leading-relaxed">
            Прозрачные условия без скрытых комиссий. Оплата онлайн картами РФ и СБП для физлиц
            или официальный безналичный расчет по счету с закрывающими актами для компаний.
          </p>
        </div>

        {/* Статус активной подписки пользователя */}
        {isPro && (
          <div className="p-6 rounded-2xl bg-blue-50 border border-blue-200 text-blue-950 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse" />
                <h3 className="font-bold text-base text-blue-900">У вас активен тариф PRO</h3>
              </div>
              <p className="text-xs text-blue-700 mt-1">
                Вам доступна конвертация файлов до 100 МБ без ограничений по страницам и очереди.
              </p>
            </div>
            <button
              onClick={handleCancelSub}
              disabled={cancellingSub}
              className="text-xs text-slate-600 hover:text-red-700 border border-slate-300 hover:border-red-300 bg-white px-3.5 py-2 rounded-xl transition-colors shrink-0"
            >
              {cancellingSub ? 'Отмена...' : 'Отменить автопродление'}
            </button>
          </div>
        )}

        {cancelMessage && (
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{cancelMessage}</span>
          </div>
        )}

        {/* Карточки тарифов или B2B форма */}
        {showB2BForm ? (
          <B2BInvoiceForm
            onRequireAuth={() => setAuthOpen(true)}
            onBack={() => setShowB2BForm(false)}
          />
        ) : (
          <PricingCards
            onSelectB2B={() => setShowB2BForm(true)}
            onRequireAuth={() => setAuthOpen(true)}
          />
        )}

        {/* Блок доверия и гарантий (152-ФЗ, безопасность, инфраструктура) */}
        <div className="pt-8 border-t border-slate-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-slate-600">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 mt-0.5">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-900">152-ФЗ и защита данных</h4>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Не логируем содержимое документов. Все серверы и хранилище расположены на территории РФ.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 mt-0.5">
                <Server className="w-4 h-4 text-emerald-600" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-900">Инфраструктура Selectel</h4>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Отказоустойчивое S3-хранилище и изолированные воркеры в Санкт-Петербурге и Москве.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-700 shrink-0 mt-0.5">
                <Clock className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-900">Автоудаление через 2 часа</h4>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Исходные и сконвертированные файлы безвозвратно удаляются автоматическим планировщиком.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
