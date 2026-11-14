import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from './Header';

vi.mock('@/store/useAuthStore', () => ({
  useAuthStore: () => ({
    user: null,
    accessToken: null,
    clearAuth: vi.fn(),
  }),
}));

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders brand logo and direct navigation links', () => {
    render(<Header />);
    expect(screen.getByText('Чистый документ')).toBeDefined();
    expect(screen.getAllByText('Конвертер').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Тарифы').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Войти')).toBeDefined();
  });

  it('opens and closes mobile drawer', () => {
    render(<Header />);
    const menuBtn = screen.getByRole('button', { name: /открыть меню/i });
    fireEvent.click(menuBtn);

    expect(screen.getByRole('dialog', { name: 'Навигация' })).toBeDefined();

    const closeBtn = screen.getByRole('button', { name: /закрыть меню/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole('dialog', { name: 'Навигация' })).toBeNull();
  });
});
