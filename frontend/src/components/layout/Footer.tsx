import React from 'react';

export const Footer: React.FC = () => (
  <footer className="border-t border-slate-200 py-6 mt-12">
    <div className="max-w-4xl mx-auto px-4 text-center text-sm text-slate-500 space-y-1">
      <p>Данные обрабатываются и хранятся на серверах в РФ в соответствии с 152-ФЗ.</p>
      <p>
        <a href="/offer" className="hover:text-slate-700 underline">Оферта</a>
        {' · '}
        <a href="/privacy" className="hover:text-slate-700 underline">Политика конфиденциальности</a>
        {' · '}
        <a href="mailto:support@clean-doc.ru" className="hover:text-slate-700 underline">Поддержка</a>
      </p>
    </div>
  </footer>
);

