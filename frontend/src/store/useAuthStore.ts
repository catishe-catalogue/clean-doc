'use client';
import { create } from 'zustand';
import { UserProfile } from '@/lib/types';

interface AuthState {
  accessToken: string | null;
  user: UserProfile | null;
  setAuth: (token: string, user: UserProfile) => void;
  updatePlan: (plan: 'free' | 'pro') => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setAuth: (accessToken, user) => set({ accessToken, user }),
  updatePlan: (plan) =>
    set((state) => (state.user ? { user: { ...state.user, plan } } : state)),
  clearAuth: () => set({ accessToken: null, user: null }),
}));
