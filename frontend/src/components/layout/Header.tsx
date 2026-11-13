'use client';
import React, { useEffect, useState } from 'react';
import { FileCheck, User, LogOut } from 'lucide-react';
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

  const conversionsLeft = user ? user.conversions_limit - user.conversions_today : null;

  return (
    <>
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCheck className="w-6 h-6 text-blue-600" />
            <span className="font-bold text-slate-900">Чистый документ</span>
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-slate-600">
                Осталось: <strong>{conversionsLeft}</strong> конв./день
              </span>
            )}
            {accessToken ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-700 flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {user?.email || user?.telegram_username || 'Профиль'}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-slate-400 hover:text-slate-600"
                  title="Выйти"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthOpen(true)}
                className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl font-medium transition-colors"
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

