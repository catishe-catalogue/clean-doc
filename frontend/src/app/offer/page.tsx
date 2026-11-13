import React from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { ArrowLeft } from 'lucide-react';

export const metadata = {
  title: 'Публичная оферта — Чистый документ',
  description: 'Договор публичной оферты на оказание услуг онлайн-конвертации документов',
};

export default function OfferPage() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-10 md:py-14 space-y-6">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Вернуться на главную
          </Link>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-10 shadow-sm space-y-6 text-sm text-slate-700 leading-relaxed">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
            Договор публичной оферты
          </h1>
          <p className="text-xs text-slate-500">
            Редакция от 15 октября 2026 г. Действует бессрочно до замены новой редакцией.
          </p>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">1. Общие положения</h2>
            <p>
              Настоящий документ является официальным предложением (публичной офертой в соответствии со
              ст. 437 Гражданского кодекса РФ) сервиса «Чистый документ» (далее — Исполнитель) и определяет
              условия предоставления услуг онлайн-конвертации файлов PDF в редактируемые форматы DOCX и XLSX.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">2. Предмет оферты</h2>
            <p>
              Исполнитель обязуется оказывать Заказчику услуги по автоматической обработке и
              конвертации документов с использованием специализированного программного обеспечения, а
              Заказчик обязуется оплачивать услуги в соответствии с выбранным тарифным планом (Free, PRO).
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">3. Порядок оплаты и предоставления доступа</h2>
            <p>
              Оплата физическими лицами производится безналичным способом через авторизованный платежный
              шлюз ЮKassa (банковские карты РФ, СБП). Оплата юридическими лицами и индивидуальными
              предпринимателями производится по безналичному расчету на основании сформированного PDF-счета.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">4. Безопасность и хранение данных</h2>
            <p>
              Вся обработка и хранение файлов осуществляются на серверах, расположенных на территории
              Российской Федерации в соответствии с Федеральным законом № 152-ФЗ «О персональных данных».
              Файлы Заказчика автоматически удаляются с серверов через 2 часа после завершения конвертации.
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
