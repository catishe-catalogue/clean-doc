'use client';
import React from 'react';

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

// global-error оборачивает весь layout, поэтому нужны базовые html/body теги
export default function GlobalError({ reset }: Props) {
  return (
    <html lang="ru">
      <body style={{ margin: 0, background: 'oklch(97% 0.006 55)', fontFamily: 'system-ui, sans-serif', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', flexDirection: 'column', gap: '1rem', padding: '1rem' }}>
        <p style={{ fontSize: '5rem', color: 'oklch(81% 0.011 55)', margin: 0, fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>500</p>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0, color: 'oklch(21% 0.012 38)' }}>Критическая ошибка</h1>
        <p style={{ fontSize: '0.875rem', color: 'oklch(47% 0.013 45)', margin: 0 }}>Пожалуйста, обновите страницу.</p>
        <button
          onClick={reset}
          style={{ marginTop: '0.5rem', padding: '0.75rem 1.5rem', background: 'oklch(22% 0.011 40)', color: 'oklch(96.5% 0.006 70)', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 500 }}
        >
          Обновить
        </button>
      </body>
    </html>
  );
}
