import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Dropzone } from './Dropzone';

const mockSetFile = vi.fn();
let mockStatus = 'idle';
let mockFile: File | null = null;

vi.mock('@/store/useConverterStore', () => ({
  useConverterStore: () => ({
    file: mockFile,
    setFile: mockSetFile,
    status: mockStatus,
  }),
}));

describe('Dropzone', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = 'idle';
    mockFile = null;
  });

  it('renders upload prompt when no file', () => {
    render(<Dropzone />);
    expect(screen.getByText(/перетащите pdf/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /загрузить pdf файл/i })).toBeDefined();
  });

  it('rejects non-PDF files with inline error message', () => {
    render(<Dropzone />);
    const input = screen.getByLabelText(/загрузить pdf файл/i);

    // Drop an invalid txt file
    const txtFile = new File(['hello'], 'document.txt', { type: 'text/plain' });
    fireEvent.drop(input, {
      dataTransfer: {
        files: [txtFile],
      },
    });

    expect(screen.getByText('Пожалуйста, выберите файл в формате PDF')).toBeDefined();
    expect(mockSetFile).not.toHaveBeenCalled();
  });

  it('accepts valid PDF file and calls setFile', () => {
    render(<Dropzone />);
    const input = screen.getByLabelText(/загрузить pdf файл/i);

    const pdfFile = new File(['%PDF-1.4 sample content'], 'contract.pdf', { type: 'application/pdf' });
    fireEvent.drop(input, {
      dataTransfer: {
        files: [pdfFile],
      },
    });

    expect(mockSetFile).toHaveBeenCalledWith(pdfFile);
  });

  it('renders completed state when status is completed', () => {
    mockStatus = 'completed';
    mockFile = new File(['dummy'], 'result.pdf', { type: 'application/pdf' });
    render(<Dropzone />);
    expect(screen.getByText('Конвертация завершена')).toBeDefined();
  });
});
