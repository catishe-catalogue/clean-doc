'use client';
import { useEffect, RefObject } from 'react';

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

export function useFocusTrap(ref: RefObject<HTMLElement | null>, active: boolean) {
  useEffect(() => {
    if (!active) return;
    const el = ref.current;
    if (!el) return;

    const trigger = document.activeElement as HTMLElement | null;

    // Фокус на первый focusable-элемент внутри после монтирования
    const timer = setTimeout(() => {
      const first = el.querySelector<HTMLElement>(FOCUSABLE);
      first?.focus();
    }, 16);

    const trap = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const nodes = Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!nodes.length) { e.preventDefault(); return; }
      const first = nodes[0];
      const last = nodes[nodes.length - 1];

      if (!el.contains(document.activeElement)) {
        e.preventDefault();
        first.focus();
        return;
      }

      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };

    document.addEventListener('keydown', trap);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('keydown', trap);
      trigger?.focus(); // возврат фокуса на триггер
    };
  }, [active, ref]);
}
