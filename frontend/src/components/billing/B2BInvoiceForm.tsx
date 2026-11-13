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
    <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-800">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              Выставление счета для юридических лиц и ИП
            </h3>
            <p className="text-xs text-slate-500">
              Автоматическое заполнение реквизитов организации через DaData API
            </p>
          </div>
        </div>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Назад к тарифам
          </button>
        )}
      </div>

      {invoice ? (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-950 space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
              <span className="font-semibold text-sm">
                Счет {invoice.invoice_number} успешно сформирован
              </span>
            </div>
            <div className="text-sm space-y-1 text-emerald-900 pt-2 border-t border-emerald-200/60">
              <p>
                <strong>Организация:</strong> {invoice.company_name}
              </p>
              <p>
                <strong>Сумма к оплате:</strong> {invoice.amount_rub.toLocaleString('ru-RU')} ₽ (Без НДС)
              </p>
              <p>
                <strong>Назначение платежа:</strong> Годовая подписка на сервис «Чистый документ» (Тариф PRO)
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleDownload}
              className="flex-1 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white py-3.5 px-6 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2 shadow-sm"
            >
              <Download className="w-4 h-4" />
              Скачать официальный счет (PDF с факсимиле)
            </button>
            <button
              type="button"
              onClick={() => {
                setInvoice(null);
                setInn('');
              }}
              className="border border-slate-200 hover:bg-slate-50 text-slate-700 py-3.5 px-6 rounded-xl font-medium text-sm transition-colors"
            >
              Сформировать другой счет
            </button>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed">
            После поступления средств на расчетный счет подписка PRO активируется автоматически.
            Закрывающие акты формируются по окончании расчетного периода и направляются через ЭДО или на email.
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-sm text-red-800">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label htmlFor="inn-input" className="block text-sm font-medium text-slate-700 mb-1.5">
              ИНН организации или ИП
            </label>
            <input
              id="inn-input"
              type="text"
              value={inn}
              onChange={handleInnChange}
              placeholder="Например: 7707083893"
              disabled={loading}
              className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 outline-none text-slate-900 text-sm placeholder:text-slate-400"
            />
            <p className="text-xs text-slate-500 mt-1.5">
              10 цифр для юридических лиц (ООО, АО), 12 цифр для индивидуальных предпринимателей
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
            <p className="font-semibold text-slate-800">Что входит в тариф PRO (1 год):</p>
            <p>• Полный безлимит конвертаций PDF в Word и Excel до 250 страниц на файл</p>
            <p>• Приоритетная очередь с максимальной скоростью обработки</p>
            <p>• Предоставление оригиналов закрывающих документов и актов</p>
            <p>• Стоимость: 11 900 ₽ в год (скидка 33%)</p>
          </div>

          <button
            type="submit"
            disabled={loading || (inn.length !== 10 && inn.length !== 12)}
            className="w-full bg-slate-900 hover:bg-slate-800 active:bg-slate-950 disabled:bg-slate-300 text-white py-3.5 rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Поиск реквизитов и генерация счета...
              </>
            ) : (
              <>
                <Building2 className="w-4 h-4" />
                Сформировать счет на 11 900 ₽
              </>
            )}
          </button>
        </form>
      )}
    </div>
  );
};
