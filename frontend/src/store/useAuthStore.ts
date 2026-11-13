'use client';
import { create } from 'zustand';
import { UserProfile } from '@/lib/types';
import { apiClient } from '@/lib/api-client';

interface AuthState {
  accessToken: string | null;
  user: UserProfile | null;
  isLoading: boolean;
  setAuth: (token: string, user: UserProfile) => void;
  updatePlan: (plan: 'free' | 'pro') => void;
  clearAuth: () => void;
  initDevAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isLoading: false,
  setAuth: (accessToken, user) => set({ accessToken, user, isLoading: false }),
  updatePlan: (plan) =>
    set((state) => (state.user ? { user: { ...state.user, plan } } : state)),
  clearAuth: () => set({ accessToken: null, user: null, isLoading: false }),
  initDevAuth: async () => {
    if (get().accessToken && get().user) return;
    set({ isLoading: true });
    try {
      const devSession = await apiClient<{ access_token: string }>(
        '/api/v1/auth/dev-session',
        { method: 'GET' }
      ).catch(() => null);

      const token = devSession?.access_token || get().accessToken;
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const profile = await apiClient<UserProfile>('/api/v1/auth/me', { headers }).catch(
        () => null
      );
      if (profile) {
        set({ accessToken: token || '', user: profile, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch {
      set({ isLoading: false });
    }
  },
}));
