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
    <div className="min-h-screen flex flex-col bg-paper text-ink">
      <Header />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-12 space-y-6">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Вернуться на главную</span>
          </Link>
        </div>

        <div className="bg-cotton rounded-stock border border-rule-2 p-6 sm:p-10 stock space-y-6 text-xs sm:text-sm text-ink leading-relaxed">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-ink">
            Договор публичной оферты
          </h1>
          <p className="text-xs text-muted">
            Редакция от 15 октября 2026 г. Действует бессрочно до замены новой редакцией.
          </p>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">1. Общие положения</h2>
            <p className="text-muted">
              Настоящий документ является официальным предложением (публичной офертой в соответствии со
              ст. 437 Гражданского кодекса РФ) сервиса «Чистый документ» (далее — Исполнитель) и определяет
              условия предоставления услуг онлайн-конвертации файлов PDF в редактируемые форматы DOCX и XLSX.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">2. Предмет оферты</h2>
            <p className="text-muted">
              Исполнитель обязуется оказывать Заказчику услуги по автоматической обработке и
              конвертации документов с использованием специализированного программного обеспечения, а
              Заказчик обязуется оплачивать услуги в соответствии с выбранным тарифным планом (Free, PRO).
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">3. Порядок оплаты и предоставления доступа</h2>
            <p className="text-muted">
              Оплата физическими лицами производится безналичным способом через авторизованный платежный
              шлюз ЮKassa (банковские карты РФ, СБП). Оплата юридическими лицами и индивидуальными
              предпринимателями производится по безналичному расчету на основании сформированного PDF-счета.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">4. Ответственность и гарантии</h2>
            <p className="text-muted">
              Исполнитель гарантирует обработку файлов исключительно в автоматическом режиме без участия
              операторов-людей, а также гарантирует полное удаление всех файлов из временного хранилища
              не позднее 2 часов с момента завершения конвертации.
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
