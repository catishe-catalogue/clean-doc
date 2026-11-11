'use client';
import React, { useEffect, useRef } from 'react';

interface Props {
  botName: string;
  onAuth: (data: Record<string, unknown>) => void;
}

export const TelegramLoginButton: React.FC<Props> = ({ botName, onAuth }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !botName) return;
    const script = document.createElement('script');
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.setAttribute('data-telegram-login', botName);
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '12');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    script.setAttribute('data-request-access', 'write');
    script.async = true;
    (window as unknown as Record<string, unknown>)['onTelegramAuth'] = onAuth;
    ref.current.appendChild(script);
    return () => {
      delete (window as unknown as Record<string, unknown>)['onTelegramAuth'];
    };
  }, [botName, onAuth]);

  if (!botName) return null;
  return <div ref={ref} />;
};
