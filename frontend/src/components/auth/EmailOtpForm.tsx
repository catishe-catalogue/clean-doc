'use client';
import React, { useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/useAuthStore';
import { UserProfile } from '@/lib/types';

interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface Props {
  onSuccess: () => void;
}

export const EmailOtpForm: React.FC<Props> = ({ onSuccess }) => {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setAuth } = useAuthStore();

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiClient('/api/v1/auth/magic-link', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
      setStep('code');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка отправки кода');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const tokenResp = await apiClient<AuthTokenResponse>('/api/v1/auth/verify-code', {
        method: 'POST',
        body: JSON.stringify({ email, code }),
      });
      const profile = await apiClient<UserProfile>('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${tokenResp.access_token}` },
      });
      setAuth(tokenResp.access_token, profile);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Ошибка проверки кода');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'code') {
    return (
      <form onSubmit={handleVerifyCode} className="space-y-4">
        <p className="text-xs sm:text-sm text-muted">
          Код отправлен на <strong className="text-ink font-mono">{email}</strong>
        </p>
        <input
          type="text"
          inputMode="numeric"
          pattern="\d{6}"
          maxLength={6}
          placeholder="000000"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="w-full border border-rule-2 rounded-stock px-4 py-2.5 text-center text-xl tracking-widest font-mono bg-paper text-ink focus-visible:outline-2 focus-visible:outline-focus"
          autoFocus
        />
        {error && <p className="text-xs text-error">{error}</p>}
        <button
          type="submit"
          disabled={loading || code.length !== 6}
          className="btn-board w-full py-2.5 text-xs sm:text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-50 disabled:pointer-events-none"
        >
          {loading ? 'Проверка…' : 'Войти'}
        </button>
        <button
          type="button"
          onClick={() => setStep('email')}
          className="w-full text-xs text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
        >
          Изменить email
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleRequestCode} className="space-y-4">
      <input
        type="email"
        placeholder="your@email.ru"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full border border-rule-2 rounded-stock px-4 py-2.5 text-xs sm:text-sm bg-paper text-ink placeholder:text-muted focus-visible:outline-2 focus-visible:outline-focus"
        required
      />
      {error && <p className="text-xs text-error">{error}</p>}
      <button
        type="submit"
        disabled={loading || !email}
        className="btn-board w-full py-2.5 text-xs sm:text-sm font-medium focus-visible:outline-2 focus-visible:outline-focus disabled:opacity-50 disabled:pointer-events-none"
      >
        {loading ? 'Отправка кода…' : 'Получить 6-значный код'}
      </button>
    </form>
  );
};
