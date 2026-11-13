import React from 'react';
import Link from 'next/link';

export const Footer: React.FC = () => (
  <footer className="border-t border-rule py-8 mt-16 bg-paper">
    <div className="max-w-5xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted">
      <p className="text-center sm:text-left">
        Данные обрабатываются и хранятся на серверах в РФ в соответствии с 152-ФЗ.
      </p>
      <div className="flex flex-wrap items-center gap-4">
        <Link href="/offer" className="hover:text-ink transition-colors underline focus-visible:outline-2 focus-visible:outline-focus">
          Оферта
        </Link>
        <Link href="/privacy" className="hover:text-ink transition-colors underline focus-visible:outline-2 focus-visible:outline-focus">
          Политика конфиденциальности
        </Link>
        <a href="mailto:support@clean-doc.ru" className="hover:text-ink transition-colors underline focus-visible:outline-2 focus-visible:outline-focus">
          Поддержка
        </a>
      </div>
    </div>
  </footer>
);
