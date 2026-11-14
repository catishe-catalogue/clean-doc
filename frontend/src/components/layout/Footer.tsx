import React from 'react';
import Link from 'next/link';

export const Footer: React.FC = () => (
  <footer className="border-t border-rule mt-auto bg-paper">
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 grid grid-cols-1 sm:grid-cols-3 gap-8 text-xs text-muted">
      {/* Колонка 1: бренд */}
      <div className="space-y-1.5">
        <p className="font-medium text-ink text-sm">Чистый документ</p>
        <p>© {new Date().getFullYear()} ООО «Чистый документ»</p>
        <p>Данные хранятся на серверах в РФ (152-ФЗ)</p>
      </div>

      {/* Колонка 2: юридические ссылки */}
      <div className="flex flex-col gap-1.5">
        <Link
          href="/offer"
          className="hover:text-ink transition-colors underline underline-offset-2 w-fit focus-visible:outline-2 focus-visible:outline-focus"
        >
          Оферта
        </Link>
        <Link
          href="/privacy"
          className="hover:text-ink transition-colors underline underline-offset-2 w-fit focus-visible:outline-2 focus-visible:outline-focus"
        >
          Политика конфиденциальности
        </Link>
      </div>

      {/* Колонка 3: контакт */}
      <div>
        <a
          href="mailto:support@clean-doc.ru"
          className="hover:text-ink transition-colors underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-focus"
        >
          support@clean-doc.ru
        </a>
      </div>
    </div>
  </footer>
);
