'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { FileCheck, User, LogOut, Zap } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { AuthModal } from '@/components/auth/AuthModal';
import { apiClient } from '@/lib/api-client';

export const Header: React.FC = () => {
  const { user, accessToken, clearAuth } = useAuthStore();
  const [authOpen, setAuthOpen] = useState(false);

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
      <header className="border-b border-rule bg-paper sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2.5 text-ink hover:text-ink-2 transition-colors focus-visible:outline-2 focus-visible:outline-focus"
          >
            <div className="w-8 h-8 rounded-stock bg-cotton border border-rule-2 flex items-center justify-center shadow-card">
              <FileCheck className="w-5 h-5 text-ink" />
            </div>
            <span className="font-semibold text-ink text-base tracking-tight">Чистый документ</span>
          </Link>

          <div className="flex items-center gap-4">
            <nav className="flex items-center gap-4">
              <Link
                href="/pricing"
                className="text-sm font-medium text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
              >
                Тарифы
              </Link>
            </nav>

            {isPro ? (
              <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-stock bg-cotton text-ink border border-rule-2 shadow-card font-medium">
                <Zap className="w-3.5 h-3.5 text-paid fill-paid" />
                Тариф PRO
              </span>
            ) : user ? (
              <span className="text-xs text-muted hidden sm:inline">
                Осталось: <span className="text-ink font-mono font-medium">{conversionsLeft}</span> конв./день
              </span>
            ) : null}

            {accessToken ? (
              <div className="flex items-center gap-2 pl-3 border-l border-rule">
                <span className="text-xs sm:text-sm text-ink flex items-center gap-1.5 max-w-[140px] sm:max-w-[200px] truncate">
                  <User className="w-3.5 h-3.5 shrink-0 text-muted" />
                  <span className="truncate font-mono text-xs">{user?.email || user?.telegram_username || 'Профиль'}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="text-muted hover:text-ink p-1 rounded transition-colors focus-visible:outline-2 focus-visible:outline-focus"
                  title="Выйти"
                  aria-label="Выйти"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthOpen(true)}
                className="btn-letterpress text-xs sm:text-sm font-medium px-4 py-1.5 focus-visible:outline-2 focus-visible:outline-focus"
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
