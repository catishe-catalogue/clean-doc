import type { Metadata } from 'next';
import '@/styles/globals.css';
import Providers from './providers';

export const metadata: Metadata = {
  title: 'Чистый документ — онлайн-конвертер PDF в Word и Excel',
  description: 'Конвертация PDF документов с сохранением верстки таблиц и соответствием 152-ФЗ',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className="overflow-x-clip">
      <body className="overflow-x-clip min-h-screen bg-paper text-ink selection:bg-accent/20">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
