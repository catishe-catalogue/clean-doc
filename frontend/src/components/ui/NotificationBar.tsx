'use client';
import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { useNotifyStore } from '@/store/useNotifyStore';

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
} as const;

const STYLES = {
  success: 'bg-success-bg text-success border-success/30',
  error: 'bg-error/10 text-error border-error/30',
  info: 'bg-notify-bg text-ink border-rule-2',
} as const;

export const NotificationBar: React.FC = () => {
  const { notification, dismiss } = useNotifyStore();
  const [closing, setClosing] = useState(false);
  const prevId = useRef<number | null>(null);

  // Сброс closing при новом уведомлении
  useEffect(() => {
    if (notification && notification.id !== prevId.current) {
      setClosing(false);
      prevId.current = notification.id;
    }
  }, [notification]);

  const handleDismiss = () => {
    setClosing(true);
    setTimeout(dismiss, 180); // ждем анимацию выхода
  };

  if (!notification) return null;

  const Icon = ICONS[notification.type];

  return (
    <div
      className={`notify-bar sticky top-14 z-raised border-b ${STYLES[notification.type]}`}
      data-closing={closing || undefined}
      role="status"
      aria-live="polite"
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-2.5 flex items-center gap-3">
        <Icon className="w-4 h-4 shrink-0" aria-hidden />
        <span className="text-sm flex-1">{notification.message}</span>
        <button
          onClick={handleDismiss}
          className="p-1 rounded hover:opacity-70 transition-opacity focus-visible:outline-2 focus-visible:outline-focus shrink-0"
          aria-label="Закрыть уведомление"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
