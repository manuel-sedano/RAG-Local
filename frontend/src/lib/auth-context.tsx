"use client";

import * as React from "react";

import { api } from "@/lib/api-client";
import type { AuthUser } from "@/lib/auth-types";
import { AUTH_USER_STORAGE_KEY, clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth-tokens";

const USER_KEY = AUTH_USER_STORAGE_KEY;

type AuthState = {
  user: AuthUser | null;
  ready: boolean;
};

type AuthContextValue = AuthState & {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

function readStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  if (!getAccessToken()) {
    window.localStorage.removeItem(USER_KEY);
    return null;
  }
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    React.startTransition(() => {
      setUser(readStoredUser());
      setReady(true);
    });
  }, []);

  React.useEffect(() => {
    const onReset = () => setUser(null);
    window.addEventListener("rag:session-reset", onReset);
    return () => window.removeEventListener("rag:session-reset", onReset);
  }, []);

  const login = React.useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{
      access_token: string;
      refresh_token: string;
      user: AuthUser;
    }>("/api/auth/login", { email, password });
    setTokens(data.access_token, data.refresh_token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setUser(data.user);
  }, []);

  const logout = React.useCallback(async () => {
    const refresh = getRefreshToken();
    try {
      await api.post("/api/auth/logout", {
        refresh_token: refresh,
        all_devices: !refresh,
      });
    } catch {
      /* ignorar errores de red; limpiamos sesión local igual */
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      ready,
      login,
      logout,
    }),
    [user, ready, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return ctx;
}
