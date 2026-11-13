'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/useAuthStore';

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  const initDevAuth = useAuthStore((s) => s.initDevAuth);

  useEffect(() => {
    initDevAuth();
  }, [initDevAuth]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
