import React from 'react';
import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-paper text-ink px-4">
      <p
        className="font-outlier leading-none select-none mb-6"
        style={{
          fontSize: 'clamp(5rem, 20vw, 10rem)',
          color: 'var(--color-rule-2)',
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.04em',
        }}
        aria-hidden
      >
        404
      </p>
      <h1 className="text-xl sm:text-2xl font-semibold text-ink mb-2">
        Страница не найдена
      </h1>
      <p className="text-muted text-sm mb-8 text-center max-w-xs">
        Возможно, ссылка устарела или адрес введен с ошибкой.
      </p>
      <Link
        href="/"
        className="btn-board text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
      >
        Вернуться на главную
      </Link>
    </div>
  );
}
