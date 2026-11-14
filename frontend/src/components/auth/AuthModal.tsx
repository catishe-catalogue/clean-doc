'use client';
import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { EmailOtpForm } from './EmailOtpForm';
import { useFocusTrap } from '@/lib/useFocusTrap';

interface Props {
  open: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<Props> = ({ open, onClose }) => {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(panelRef, open);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop fixed inset-0 flex items-center justify-center z-[400] p-4 cursor-pointer"
      style={{ background: 'oklch(0% 0 0 / 0.45)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="modal-panel bg-cotton rounded-stock p-6 sm:p-8 max-w-sm w-full border border-rule-2 stock cursor-default"
      >
        <div className="flex justify-between items-center mb-6">
          <h2 id="auth-modal-title" className="text-base sm:text-lg font-medium text-ink">
            Вход в сервис
          </h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-ink p-1 rounded transition-colors focus-visible:outline-2 focus-visible:outline-focus"
            aria-label="Закрыть окно входа"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <EmailOtpForm onSuccess={onClose} />
      </div>
    </div>
  );
};
