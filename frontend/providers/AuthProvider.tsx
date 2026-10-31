"use client";

import { createContext, useContext, useEffect, useState } from "react";

import { ApiError, apiFetch, clearToken, getToken, setToken } from "@/lib/api-client";
import type { Token, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadCurrentUser() {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiFetch<User>("/auth/me");
      setUser(me);
    } catch (err) {
      if (err instanceof ApiError) clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    const request = getToken() ? apiFetch<User>("/auth/me") : Promise.resolve(null);
    request.then((me) => { if (!cancelled) setUser(me); })
      .catch((error) => { if (!cancelled) { if (error instanceof ApiError) clearToken(); setUser(null); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function login(email: string, password: string) {
    const token = await apiFetch<Token>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(token.access_token);
    await loadCurrentUser();
  }

  async function register(email: string, password: string, fullName?: string) {
    const token = await apiFetch<Token>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName ?? null }),
    });
    setToken(token.access_token);
    await loadCurrentUser();
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
