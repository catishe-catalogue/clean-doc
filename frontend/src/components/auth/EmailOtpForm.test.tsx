import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmailOtpForm } from './EmailOtpForm';
import * as apiModule from '@/lib/api-client';

vi.mock('@/lib/api-client', () => ({
  apiClient: vi.fn(),
}));

describe('EmailOtpForm', () => {
  const onSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email input and sends magic link', async () => {
    vi.spyOn(apiModule, 'apiClient').mockResolvedValueOnce({ status: 'ok' });

    render(<EmailOtpForm onSuccess={onSuccess} />);

    const input = screen.getByPlaceholderText('your@email.ru');
    fireEvent.change(input, { target: { value: 'user@clean-doc.ru' } });

    const submitBtn = screen.getByRole('button', { name: /получить 6-значный код/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('000000')).toBeDefined();
    });
  });

  it('displays error and clears it when user edits input', async () => {
    vi.spyOn(apiModule, 'apiClient').mockRejectedValueOnce(new Error('Неверный адрес почты'));

    render(<EmailOtpForm onSuccess={onSuccess} />);

    const input = screen.getByPlaceholderText('your@email.ru');
    fireEvent.change(input, { target: { value: 'bad@email' } });

    const submitBtn = screen.getByRole('button', { name: /получить 6-значный код/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Неверный адрес почты')).toBeDefined();
    });

    // UX-правило сброса: ошибка сбрасывается на onChange
    fireEvent.change(input, { target: { value: 'correct@email.ru' } });
    expect(screen.queryByText('Неверный адрес почты')).toBeNull();
  });
});
