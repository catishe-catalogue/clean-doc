import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { B2BInvoiceForm } from './B2BInvoiceForm';
import * as apiModule from '@/lib/api-client';

vi.mock('@/lib/api-client', () => ({
  apiClient: vi.fn(),
}));

vi.mock('@/store/useAuthStore', () => ({
  useAuthStore: () => ({
    accessToken: 'test-token',
  }),
}));

describe('B2BInvoiceForm', () => {
  const onRequireAuth = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('validates INN length and displays error for invalid digits count', async () => {
    render(<B2BInvoiceForm onRequireAuth={onRequireAuth} />);

    const input = screen.getByPlaceholderText(/например: 7707083893/i);
    // Enter 8 digits (invalid INN)
    fireEvent.change(input, { target: { value: '12345678' } });

    // The submit button is disabled when length is not 10 or 12
    const submitBtn = screen.getByRole('button', { name: /выставить счет/i });
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it('submits valid 10-digit INN and displays invoice details', async () => {
    vi.spyOn(apiModule, 'apiClient').mockResolvedValueOnce({
      id: 'inv-123',
      invoice_number: 'СЧ-001',
      company_name: 'ООО «Ромашка»',
      inn: '7707083893',
      amount_rub: 11900,
      status: 'pending',
      created_at: new Date().toISOString(),
    });

    render(<B2BInvoiceForm onRequireAuth={onRequireAuth} />);

    const input = screen.getByPlaceholderText(/например: 7707083893/i);
    fireEvent.change(input, { target: { value: '7707083893' } });

    const submitBtn = screen.getByRole('button', { name: /выставить счет/i });
    expect((submitBtn as HTMLButtonElement).disabled).toBe(false);

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/счет СЧ-001 успешно сформирован/i)).toBeDefined();
      expect(screen.getByText('ООО «Ромашка»')).toBeDefined();
      expect(screen.getByText('11 900 ₽')).toBeDefined();
    });
  });

  it('clears error on input change', async () => {
    vi.spyOn(apiModule, 'apiClient').mockRejectedValueOnce(new Error('Организация не найдена'));

    render(<B2BInvoiceForm onRequireAuth={onRequireAuth} />);

    const input = screen.getByPlaceholderText(/например: 7707083893/i);
    fireEvent.change(input, { target: { value: '7707083893' } });

    const submitBtn = screen.getByRole('button', { name: /выставить счет/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Организация не найдена')).toBeDefined();
    });

    // Reset on change
    fireEvent.change(input, { target: { value: '7707083894' } });
    expect(screen.queryByText('Организация не найдена')).toBeNull();
  });
});
