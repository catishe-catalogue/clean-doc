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
            Политика конфиденциальности (152-ФЗ)
          </h1>
          <p className="text-xs text-muted">
            Редакция от 15 октября 2026 г. В соответствии с Федеральным законом № 152-ФЗ «О персональных данных».
          </p>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">1. Принципы обработки данных</h2>
            <p className="text-muted">
              Сервис «Чистый документ» строго соблюдает требования законодательства РФ в области защиты
              информации. Мы не собираем избыточные данные и обрабатываем исключительно информацию,
              необходимую для аутентификации пользователя (email / Telegram ID) и совершения платежей.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">2. Содержимое документов клиентов</h2>
            <p className="text-muted">
              В системные логи сервиса категорически запрещено записывать текст, имена клиентских файлов
              и содержимое обрабатываемых документов. Все логи ведутся в обезличенном виде: UUID задачи,
              размер в байтах и время обработки.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">3. Локализация и удаление файлов</h2>
            <p className="text-muted">
              Все серверные мощности и S3-хранилища расположены в Российской Федерации (Selectel, регион
              ru-1). Исходные документы и результаты конвертации хранятся в зашифрованном виде (AES-256)
              не более 2 часов, после чего автоматически и безвозвратно удаляются.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-medium text-ink">4. Права субъектов персональных данных</h2>
            <p className="text-muted">
              Пользователь вправе в любой момент отозвать свое согласие на обработку персональных данных,
              направив запрос в службу поддержки сервиса по адресу электронной почты support@clean-doc.ru.
            </p>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
