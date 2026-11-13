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
    <div className="min-h-screen flex flex-col bg-paper text-ink">
      <Header />

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Вернуться к конвертеру</span>
          </Link>
        </div>

        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h1 className="text-2xl sm:text-4xl font-semibold tracking-tight text-ink">
            Тарифные планы и оплата
          </h1>
          <p className="text-muted text-xs sm:text-sm leading-relaxed">
            Прозрачные условия без скрытых комиссий. Оплата онлайн картами РФ и СБП для физлиц
            или официальный безналичный расчет по счету с закрывающими актами для компаний.
          </p>
        </div>

        {isPro && (
          <div className="p-5 rounded-stock bg-cotton border border-ink text-ink flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 stock">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-paid" />
                <h3 className="font-medium text-sm text-ink">У вас активен тариф PRO</h3>
              </div>
              <p className="text-xs text-muted mt-1">
                Вам доступна конвертация файлов до 100 МБ без ограничений по страницам и очереди.
              </p>
            </div>
            <button
              onClick={handleCancelSub}
              disabled={cancellingSub}
              className="btn-letterpress text-xs font-medium text-muted hover:text-error shrink-0 focus-visible:outline-2 focus-visible:outline-focus"
            >
              {cancellingSub ? 'Отмена…' : 'Отменить автопродление'}
            </button>
          </div>
        )}

        {cancelMessage && (
          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2 text-xs sm:text-sm text-ink flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-paid shrink-0" />
            <span>{cancelMessage}</span>
          </div>
        )}

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

        {/* Гарантии и соответствие стандартам */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-paid shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs sm:text-sm font-medium text-ink">152-ФЗ и безопасность</h4>
              <p className="text-xs text-muted mt-1 leading-relaxed">
                Персональные данные не покидают РФ. Файлы хранятся в зашифрованном виде.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2 flex items-start gap-3">
            <Server className="w-5 h-5 text-paid shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs sm:text-sm font-medium text-ink">Закрывающие документы</h4>
              <p className="text-xs text-muted mt-1 leading-relaxed">
                Счета и акты формируются автоматически и отправляются через операторов ЭДО.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2 flex items-start gap-3">
            <Clock className="w-5 h-5 text-paid shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs sm:text-sm font-medium text-ink">Автоматическое удаление</h4>
              <p className="text-xs text-muted mt-1 leading-relaxed">
                Все временные копии документов стираются из S3-хранилища через 2 часа.
              </p>
            </div>
          </div>
        </div>
      </main>

      <Footer />
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </div>
  );
}
