import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Dropzone } from './Dropzone';

vi.mock('@/store/useConverterStore', () => ({
  useConverterStore: () => ({
    file: null,
    setFile: vi.fn(),
    status: 'idle',
  }),
}));

describe('Dropzone', () => {
  it('renders upload prompt when no file', () => {
    render(<Dropzone />);
    expect(screen.getByText(/перетащите pdf/i)).toBeDefined();
  });
});

