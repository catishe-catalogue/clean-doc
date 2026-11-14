'use client';

import React, { useEffect, useState } from 'react';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { PricingCards } from '@/components/billing/PricingCards';
import { B2BInvoiceForm } from '@/components/billing/B2BInvoiceForm';
import { AuthModal } from '@/components/auth/AuthModal';
import { useAuthStore } from '@/store/useAuthStore';
import { useNotifyStore } from '@/store/useNotifyStore';
import { useConfetti } from '@/lib/useConfetti';
import { apiClient } from '@/lib/api-client';
import { ShieldCheck, Server, Clock, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function PricingPage() {
  const { user, accessToken, updatePlan } = useAuthStore();
  const { notify } = useNotifyStore();
  const fireConfetti = useConfetti();
  const [authOpen, setAuthOpen] = useState(false);
  const [showB2BForm, setShowB2BForm] = useState(false);
  const [cancellingSub, setCancellingSub] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('payment') === 'success') {
        fireConfetti();
        notify('success', 'Подписка PRO успешно оформлена!');
      }
    }
  }, [fireConfetti, notify]);

  const handleCancelSub = async () => {
    if (!accessToken) return;
    setCancellingSub(true);
    try {
      await apiClient('/api/v1/billing/cancel-subscription', {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      updatePlan('free');
      setShowCancelConfirm(false);
      notify('info', 'Автопродление подписки отключено. Доступ к PRO останется до конца периода.');
    } catch (err: unknown) {
      notify('error', err instanceof Error ? err.message : 'Не удалось отменить подписку. Обратитесь в поддержку.');
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
          <div className="p-5 rounded-stock bg-cotton border border-ink text-ink stock space-y-3">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-paid" />
                  <h3 className="font-medium text-sm text-ink">У вас активен тариф PRO</h3>
                </div>
                <p className="text-xs text-muted mt-1">
                  Вам доступна конвертация файлов до 100 МБ без ограничений по страницам и очереди.
                </p>
              </div>
              {!showCancelConfirm && (
                <button
                  onClick={() => setShowCancelConfirm(true)}
                  className="btn-letterpress text-xs font-medium text-muted shrink-0 focus-visible:outline-2 focus-visible:outline-focus"
                >
                  Отменить автопродление
                </button>
              )}
            </div>

            {showCancelConfirm && (
              <div className="p-4 rounded-stock bg-paper-2 border border-rule-2 space-y-3">
                <p className="text-sm text-ink">
                  Вы уверены? Доступ к PRO останется до конца оплаченного периода.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={handleCancelSub}
                    disabled={cancellingSub}
                    className="btn-letterpress text-xs disabled:opacity-50"
                    style={{ color: 'var(--color-danger)', borderColor: 'color-mix(in oklch, var(--color-danger) 40%, transparent)' }}
                  >
                    {cancellingSub ? 'Отмена…' : 'Да, отключить'}
                  </button>
                  <button
                    onClick={() => setShowCancelConfirm(false)}
                    className="btn-letterpress text-xs"
                  >
                    Нет, оставить
                  </button>
                </div>
              </div>
            )}
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
