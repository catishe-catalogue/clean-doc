'use client';
import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { FileCheck, User, LogOut, Zap, Menu, X } from 'lucide-react';
import { useAuthStore } from '@/store/useAuthStore';
import { AuthModal } from '@/components/auth/AuthModal';
import { apiClient } from '@/lib/api-client';
import { useFocusTrap } from '@/lib/useFocusTrap';

export const Header: React.FC = () => {
  const { user, accessToken, clearAuth } = useAuthStore();
  const [authOpen, setAuthOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  useFocusTrap(drawerRef, drawerOpen);

  // Добавляем тень/бордер при скролле
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Закрытие drawer по Esc
  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  // Блокировка скролла при открытом drawer
  useEffect(() => {
    document.body.style.overflow = drawerOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [drawerOpen]);

  const handleLogout = async () => {
    try { await apiClient('/api/v1/auth/logout', { method: 'POST' }); } catch { /* ignore */ }
    clearAuth();
    setDrawerOpen(false);
  };

  const isPro = user?.plan === 'pro';

  const navLinks = (
    <>
      <Link
        href="/"
        onClick={() => setDrawerOpen(false)}
        className="text-sm font-medium text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
      >
        Конвертер
      </Link>
      <Link
        href="/pricing"
        onClick={() => setDrawerOpen(false)}
        className="text-sm font-medium text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
      >
        Тарифы
      </Link>
    </>
  );

  return (
    <>
      <header
        role="banner"
        className={`sticky top-0 h-14 flex items-center z-[300] transition-colors duration-150 ${
          scrolled
            ? 'border-b border-rule bg-paper/90 backdrop-blur-sm'
            : 'border-b border-transparent bg-paper'
        }`}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 w-full flex items-center justify-between gap-4">
          {/* Логотип */}
          <Link
            href="/"
            className="flex items-center gap-2.5 text-ink hover:text-ink-2 transition-colors focus-visible:outline-2 focus-visible:outline-focus shrink-0"
          >
            <div className="w-8 h-8 rounded-stock bg-cotton border border-rule-2 flex items-center justify-center shadow-card">
              <FileCheck className="w-5 h-5 text-ink" />
            </div>
            <span className="font-semibold text-ink text-base tracking-tight">Чистый документ</span>
          </Link>

          {/* Навигация — десктоп */}
          <nav aria-label="Основная навигация" className="hidden sm:flex items-center gap-5">
            {navLinks}
          </nav>

          {/* Правая часть */}
          <div className="hidden sm:flex items-center gap-3">
            {isPro && (
              <span className="inline-flex items-center gap-1.5 h-[22px] px-2.5 rounded-pill text-xs font-medium"
                style={{ background: 'var(--color-paid-muted)', color: 'var(--color-paid)' }}>
                <Zap className="w-3 h-3" />
                PRO
              </span>
            )}

            {accessToken ? (
              <div className="flex items-center gap-2 pl-3 border-l border-rule">
                <span className="text-xs text-ink flex items-center gap-1.5 max-w-[160px] truncate">
                  <User className="w-3.5 h-3.5 shrink-0 text-muted" />
                  <span className="truncate font-mono">{user?.email || user?.telegram_username || 'Профиль'}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="text-muted hover:text-ink p-1 rounded transition-colors focus-visible:outline-2 focus-visible:outline-focus"
                  aria-label="Выйти из аккаунта"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthOpen(true)}
                className="btn-letterpress text-sm font-medium px-4 py-1.5 focus-visible:outline-2 focus-visible:outline-focus"
              >
                Войти
              </button>
            )}
          </div>

          {/* Hamburger — мобайл */}
          <button
            className="sm:hidden p-1.5 rounded text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
            onClick={() => setDrawerOpen(true)}
            aria-label="Открыть меню"
            aria-expanded={drawerOpen}
            aria-controls="mobile-nav"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Мобильный drawer */}
      {drawerOpen && (
        <>
          {/* Overlay */}
          <div
            className="fixed inset-0 z-[350] bg-ink/40 sm:hidden"
            aria-hidden
            onClick={() => setDrawerOpen(false)}
            style={{ animation: 'modal-backdrop-in 200ms ease-out forwards' }}
          />
          {/* Панель */}
          <div
            id="mobile-nav"
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Навигация"
            className="fixed top-0 right-0 h-full w-72 max-w-[85vw] z-[400] bg-paper border-l border-rule sm:hidden flex flex-col"
            style={{ animation: 'drawer-in 220ms cubic-bezier(0.2,0,0,1) forwards' }}
          >
            <div className="flex items-center justify-between px-5 h-14 border-b border-rule shrink-0">
              <span className="font-semibold text-sm text-ink">Меню</span>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded text-muted hover:text-ink transition-colors focus-visible:outline-2 focus-visible:outline-focus"
                aria-label="Закрыть меню"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <nav className="flex flex-col gap-1 p-4 flex-1" aria-label="Мобильная навигация">
              <Link href="/" onClick={() => setDrawerOpen(false)}
                className="px-3 py-2.5 rounded-stock text-sm font-medium text-ink hover:bg-paper-2 transition-colors focus-visible:outline-2 focus-visible:outline-focus">
                Конвертер
              </Link>
              <Link href="/pricing" onClick={() => setDrawerOpen(false)}
                className="px-3 py-2.5 rounded-stock text-sm font-medium text-ink hover:bg-paper-2 transition-colors focus-visible:outline-2 focus-visible:outline-focus">
                Тарифы
              </Link>
            </nav>

            <div className="p-4 border-t border-rule shrink-0">
              {isPro && (
                <div className="mb-3 inline-flex items-center gap-1.5 h-[22px] px-2.5 rounded-pill text-xs font-medium"
                  style={{ background: 'var(--color-paid-muted)', color: 'var(--color-paid)' }}>
                  <Zap className="w-3 h-3" />
                  PRO активен
                </div>
              )}
              {accessToken ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted font-mono truncate">{user?.email || user?.telegram_username}</p>
                  <button
                    onClick={handleLogout}
                    className="btn-letterpress w-full text-sm text-muted justify-center flex items-center gap-2"
                  >
                    <LogOut className="w-4 h-4" />
                    Выйти
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => { setDrawerOpen(false); setAuthOpen(true); }}
                  className="btn-board w-full text-sm font-medium"
                >
                  Войти
                </button>
              )}
            </div>
          </div>
        </>
      )}

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} />
    </>
  );
};
