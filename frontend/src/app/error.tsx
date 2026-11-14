'use client';
import React from 'react';
import Link from 'next/link';

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: Props) {
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
        500
      </p>
      <h1 className="text-xl sm:text-2xl font-semibold text-ink mb-2">
        Произошла ошибка сервера
      </h1>
      <p className="text-muted text-sm mb-8 text-center max-w-xs">
        Мы уже получили уведомление и скоро все исправим.
      </p>
      {process.env.NODE_ENV === 'development' && error.message && (
        <pre className="mb-6 text-xs text-muted bg-paper-2 border border-rule-2 rounded-stock px-4 py-3 max-w-sm w-full overflow-auto">
          {error.message}
        </pre>
      )}
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="btn-board text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
        >
          Попробовать снова
        </button>
        <Link
          href="/"
          className="btn-letterpress text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus"
        >
          На главную
        </Link>
      </div>
    </div>
  );
}
