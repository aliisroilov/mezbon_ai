import { create } from "zustand";
import type { User } from "../types";
import { authAPI, setAccessToken } from "../api/client";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    const result = await authAPI.login(email, password);
    setAccessToken(result.access_token);
    set({ user: result.user, isAuthenticated: true });
  },

  logout: async () => {
    try {
      await authAPI.logout();
    } catch {
      // ignore logout errors
    }
    setAccessToken(null);
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    try {
      const user = await authAPI.me();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      setAccessToken(null);
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  setUser: (user) => set({ user, isAuthenticated: !!user }),
}));
