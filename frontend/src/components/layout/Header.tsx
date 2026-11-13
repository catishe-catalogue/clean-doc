'use client';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileCheck, User, LogOut, Zap } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { AuthModal } from '@/components/auth/AuthModal';
import { apiClient } from '@/lib/api-client';
import { UserProfile } from '@/lib/types';

export const Header: React.FC = () => {
  const { user, accessToken, clearAuth, setAuth } = useAuthStore();
  const [authOpen, setAuthOpen] = useState(false);

  useEffect(() => {
    if (accessToken && user) return;
    const initAuth = async () => {
      try {
        const devSession = await apiClient<{ access_token: string }>(
          '/api/v1/auth/dev-session',
          { method: 'GET' }
        ).catch(() => null);

        const token = devSession?.access_token || accessToken;
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const profile = await apiClient<UserProfile>('/api/v1/auth/me', { headers });
        if (profile) {
          setAuth(token || '', profile);
        }
      } catch {
        // Гостевой режим в продакшене
      }
    };
    initAuth();
  }, [accessToken, user, setAuth]);

  const handleLogout = async () => {
    try {
      await apiClient('/api/v1/auth/logout', { method: 'POST' });
    } catch {
      // ignore
    }
    clearAuth();
  };

  const isPro = user?.plan === 'pro';
  const conversionsLeft = user ? user.conversions_limit - user.conversions_today : null;

  return (
    <>
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-slate-900 hover:text-blue-600 transition-colors">
            <FileCheck className="w-6 h-6 text-blue-600" />
            <span className="font-bold text-slate-900">Чистый документ</span>
          </Link>

          <div className="flex items-center gap-4">
            <nav className="flex items-center gap-3">
              <Link
                href="/pricing"
                className="text-xs md:text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors flex items-center gap-1"
              >
                <span>Тарифы</span>
                {!isPro && (
                  <span className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-700 rounded font-semibold">
                    PRO
                  </span>
                )}
              </Link>
            </nav>

            {isPro ? (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-200">
                <Zap className="w-3 h-3 text-blue-600 fill-blue-600" />
                Тариф PRO
              </span>
            ) : user ? (
              <span className="text-xs text-slate-500 hidden sm:inline">
                Осталось: <strong className="text-slate-800">{conversionsLeft}</strong> конв./день
              </span>
            ) : null}

            {accessToken ? (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <span className="text-xs md:text-sm text-slate-700 flex items-center gap-1 max-w-[140px] md:max-w-[180px] truncate">
                  <User className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{user?.email || user?.telegram_username || 'Профиль'}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="text-slate-400 hover:text-slate-600 p-1"
                  title="Выйти"
                  aria-label="Выйти"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthOpen(true)}
                className="text-xs md:text-sm bg-blue-600 hover:bg-blue-700 text-white px-3.5 py-1.5 rounded-xl font-medium transition-colors"
              >
                Войти
              </button>
            )}
          </div>
        </div>
      </header>
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </>
  );
};
