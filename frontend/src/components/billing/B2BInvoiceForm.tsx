'use client';

import React, { useState } from 'react';
import { Building2, Download, AlertCircle, CheckCircle2, Loader2, ArrowLeft } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { apiClient } from '@/lib/api-client';
import { InvoiceResponse } from '@/lib/types';

interface B2BInvoiceFormProps {
  onRequireAuth: () => void;
  onBack?: () => void;
}

export const B2BInvoiceForm: React.FC<B2BInvoiceFormProps> = ({ onRequireAuth, onBack }) => {
  const { accessToken } = useAuthStore();
  const [inn, setInn] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null);

  const handleInnChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 12);
    setInn(val);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accessToken) {
      onRequireAuth();
      return;
    }

    if (inn.length !== 10 && inn.length !== 12) {
      setError('ИНН юридического лица должен содержать 10 цифр, а индивидуального предпринимателя — 12 цифр');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await apiClient<InvoiceResponse>('/api/v1/billing/invoices/create', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ inn, billing_period: 'year' }),
      });
      setInvoice(resp);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Не удалось сформировать счет. Проверьте правильность введенного ИНН.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!invoice) return;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const downloadUrl = `${apiBase}/api/v1/billing/invoices/${invoice.id}/pdf?token=${accessToken || ''}`;
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="bg-cotton rounded-stock border border-rule-2 p-6 sm:p-8 stock">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-stock bg-paper border border-rule-2 flex items-center justify-center text-ink shadow-card">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-medium text-ink">
              Выставление счета для юридических лиц и ИП
            </h3>
            <p className="text-xs text-muted">
              Автоматическое заполнение реквизитов организации через DaData API
            </p>
          </div>
        </div>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="text-xs text-muted hover:text-ink flex items-center gap-1 focus-visible:outline-2 focus-visible:outline-focus"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Назад к тарифам</span>
          </button>
        )}
      </div>

      {invoice ? (
        <div className="space-y-6">
          <div className="p-5 rounded-stock bg-paper-2 border border-rule-2 text-ink space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-paid shrink-0" />
              <span className="font-medium text-sm">
                Счет {invoice.invoice_number} успешно сформирован
              </span>
            </div>
            <div className="text-xs sm:text-sm space-y-1 text-muted pt-2 border-t border-rule-2">
              <p>
                <strong className="text-ink">Организация:</strong> {invoice.company_name}
              </p>
              <p>
                <strong className="text-ink">Сумма к оплате:</strong> <span className="font-mono tabular-nums">{invoice.amount_rub.toLocaleString('ru-RU')} ₽</span> (Без НДС)
              </p>
              <p>
                <strong className="text-ink">Назначение платежа:</strong> Годовая подписка на сервис «Чистый документ» (Тариф PRO)
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleDownload}
              className="btn-board flex-1 py-3 px-6 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 whitespace-nowrap focus-visible:outline-2 focus-visible:outline-focus"
            >
              <Download className="w-4 h-4" />
              <span>Скачать счет (PDF)</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setInvoice(null);
                setInn('');
              }}
              className="btn-letterpress py-3 px-6 text-xs sm:text-sm font-medium whitespace-nowrap focus-visible:outline-2 focus-visible:outline-focus"
            >
              Сформировать другой счет
            </button>
          </div>

          <p className="text-xs text-muted leading-relaxed">
            После поступления средств на расчетный счет подписка PRO активируется автоматически.
            Закрывающие акты формируются по окончании расчетного периода и направляются через ЭДО или на email.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="p-4 rounded-stock bg-error/10 border border-error/30 flex items-start gap-3 text-xs sm:text-sm text-error">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label htmlFor="inn-input" className="block text-xs sm:text-sm font-medium text-ink mb-1.5">
              ИНН организации или ИП
            </label>
            <input
              id="inn-input"
              type="text"
              value={inn}
              onChange={handleInnChange}
              placeholder="Например: 7707083893"
              disabled={loading}
              className="w-full px-4 py-2.5 rounded-stock border border-rule-2 bg-paper text-ink text-sm font-mono placeholder:text-muted focus-visible:outline-2 focus-visible:outline-focus"
            />
            <p className="text-xs text-muted mt-1.5">
              10 цифр для юридических лиц (ООО, АО), 12 цифр для индивидуальных предпринимателей
            </p>
          </div>

          <div className="p-4 rounded-stock bg-paper-2 border border-rule-2 text-xs text-muted space-y-1">
            <p className="font-medium text-ink">Параметры годовой подписки PRO:</p>
            <p>• Полный безлимит конвертаций PDF в Word и Excel до 250 страниц на файл</p>
            <p>• Приоритетная очередь с максимальной скоростью обработки</p>
            <p>• Предоставление оригиналов закрывающих документов и актов</p>
            <p>• Стоимость: 11 900 ₽ в год (скидка 33%)</p>
          </div>

          <button
            type="submit"
            disabled={loading || (inn.length !== 10 && inn.length !== 12)}
            className="btn-board w-full py-3 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 nowrap whitespace-nowrap focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-50 disabled:pointer-events-none"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Генерация счета…</span>
              </>
            ) : (
              <>
                <Building2 className="w-4 h-4" />
                <span>Выставить счет</span>
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
};
