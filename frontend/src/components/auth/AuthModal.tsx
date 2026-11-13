'use client';
import React from 'react';
import { X } from 'lucide-react';
import { EmailOtpForm } from './EmailOtpForm';

interface Props {
  open: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<Props> = ({ open, onClose }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-ink/60 flex items-center justify-center z-50 p-4">
      <div className="bg-cotton rounded-stock p-6 sm:p-8 max-w-sm w-full border border-rule-2 stock">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-base sm:text-lg font-medium text-ink">Вход в сервис</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-ink p-1 rounded focus-visible:outline-2 focus-visible:outline-focus"
            aria-label="Закрыть"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <EmailOtpForm onSuccess={onClose} />
      </div>
    </div>
  );
};
