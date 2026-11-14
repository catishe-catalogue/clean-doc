'use client';
import { useCallback } from 'react';

// shortcut: hex от --color-paid + --color-accent, обновить при смене темы Coral
const COLORS = ['#9b4f30', '#c47a5a', '#e8d5c8', '#ffffff'];

export function useConfetti() {
  return useCallback(() => {
    if (typeof window === 'undefined') return;

    const count = 48;
    const origin = { x: window.innerWidth / 2, y: window.innerHeight * 0.35 };

    for (let i = 0; i < count; i++) {
      const el = document.createElement('div');
      el.className = 'confetti-piece';

      const angle = (Math.random() * 260 - 130) * (Math.PI / 180); // веер вверх/в стороны
      const speed = 180 + Math.random() * 240;
      const height = 6 + Math.random() * 10;
      const dist = speed + Math.random() * 160;
      const dur = 900 + Math.random() * 400;
      const delay = Math.random() * 180;
      const rot = (Math.random() > 0.5 ? 1 : -1) * (200 + Math.random() * 320);

      el.style.cssText = `
        left: ${origin.x + Math.sin(angle) * speed * 0.4}px;
        top: ${origin.y - Math.cos(angle) * speed * 0.4}px;
        height: ${height}px;
        background: ${COLORS[Math.floor(Math.random() * COLORS.length)]};
        --confetti-dur: ${dur}ms;
        --confetti-delay: ${delay}ms;
        --confetti-dist: ${dist}px;
        --confetti-rot: ${rot}deg;
      `;

      document.body.appendChild(el);
      setTimeout(() => el.remove(), dur + delay + 50);
    }
  }, []);
}
