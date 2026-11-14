import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { NotificationBar } from './NotificationBar';
import { useNotifyStore } from '@/store/useNotifyStore';

describe('NotificationBar', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useNotifyStore.getState().dismiss();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders nothing when no notification is active', () => {
    const { container } = render(<NotificationBar />);
    expect(container.firstChild).toBeNull();
  });

  it('renders notification message and closes on button click', async () => {
    render(<NotificationBar />);

    act(() => {
      useNotifyStore.getState().notify('success', 'Подписка PRO успешно оформлена!');
    });

    expect(screen.getByText('Подписка PRO успешно оформлена!')).toBeDefined();

    const closeBtn = screen.getByRole('button', { name: /закрыть уведомление/i });
    fireEvent.click(closeBtn);

    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(screen.queryByText('Подписка PRO успешно оформлена!')).toBeNull();
  });

  it('auto-dismisses notification after 4000ms', () => {
    render(<NotificationBar />);

    act(() => {
      useNotifyStore.getState().notify('info', 'Тестовое информационное сообщение');
    });

    expect(screen.getByText('Тестовое информационное сообщение')).toBeDefined();

    act(() => {
      vi.advanceTimersByTime(4100);
    });

    expect(screen.queryByText('Тестовое информационное сообщение')).toBeNull();
  });
});
