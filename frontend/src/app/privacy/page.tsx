import React from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { ArrowLeft } from 'lucide-react';

export const metadata = {
  title: 'Политика конфиденциальности — Чистый документ',
  description: 'Политика обработки персональных данных и соответствие 152-ФЗ',
};

export default function PrivacyPage() {
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
            Политика конфиденциальности (152-ФЗ)
          </h1>
          <p className="text-xs text-slate-500">
            Редакция от 15 октября 2026 г. В соответствии с Федеральным законом № 152-ФЗ «О персональных данных».
          </p>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">1. Принципы обработки данных</h2>
            <p>
              Сервис «Чистый документ» строго соблюдает требования законодательства РФ в области защиты
              информации. Мы не собираем избыточные данные и обрабатываем исключительно информацию,
              необходимую для аутентификации пользователя (email / Telegram ID) и совершения платежей.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">2. Содержимое документов клиентов</h2>
            <p>
              В системные логи сервиса категорически запрещено записывать текст, имена клиентских файлов
              и содержимое обрабатываемых документов. Все логи ведутся в обезличенном виде: UUID задачи,
              размер в байтах и время обработки.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">3. Локализация и удаление файлов</h2>
            <p>
              Все серверные мощности и S3-хранилища расположены в Российской Федерации (Selectel, регион
              ru-1). Исходные документы и результаты конвертации хранятся в зашифрованном виде (AES-256)
              не более 2 часов, после чего автоматически и безвозвратно удаляются.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-semibold text-slate-900">4. Платежные данные</h2>
            <p>
              Сервис не хранит и не обрабатывает данные банковских карт. Все расчеты производятся на
              защищенной платежной странице шлюза ЮKassa, сертифицированного по стандарту PCI DSS.
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
