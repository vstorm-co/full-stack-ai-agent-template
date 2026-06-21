"use client";

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "@/stores";
import { apiClient, ApiError } from "@/lib/api-client";
import type { User, LoginRequest, RegisterRequest } from "@/types";
import { ROUTES } from "@/lib/constants";
import { isAppAdmin } from "@/lib/utils";

// Session-level singletons so /auth/me runs ONCE per page load no matter how
// many components mount useAuth(). Concurrent mounts share the in-flight
// promise; later mounts skip entirely (the store is persisted across the
// session). Reset on logout so the next login re-checks.
let authCheckPromise: Promise<void> | null = null;
let authChecked = false;

// Access tokens expire after 15 min. The in-memory token (used by the chat
// WebSocket and proxied API calls) is set once on load and would otherwise go
// stale while the tab stays open — causing WS auth failures / "Offline" chat.
// Refresh it ahead of expiry on a single shared interval. /auth/me
// transparently mints a fresh access token from the refresh cookie.
let tokenRefreshTimer: ReturnType<typeof setInterval> | null = null;
const TOKEN_REFRESH_INTERVAL_MS = 10 * 60 * 1000;

function ensureTokenRefresh(): void {
  if (tokenRefreshTimer) return;
  tokenRefreshTimer = setInterval(() => {
    if (!useAuthStore.getState().isAuthenticated) return;
    void (async () => {
      try {
        const data = await apiClient.get<User & { access_token?: string }>("/auth/me");
        if (data.access_token) useAuthStore.getState().setAccessToken(data.access_token);
      } catch {
        // Ignore — the next real request (or its 401 → refresh) handles failure.
      }
    })();
  }, TOKEN_REFRESH_INTERVAL_MS);
}

function stopTokenRefresh(): void {
  if (tokenRefreshTimer) {
    clearInterval(tokenRefreshTimer);
    tokenRefreshTimer = null;
  }
}

function runAuthCheck(setUser: (u: User | null) => void): Promise<void> {
  if (authChecked) return Promise.resolve();
  if (authCheckPromise) return authCheckPromise;
  authCheckPromise = (async () => {
    try {
      const data = await apiClient.get<User & { access_token?: string }>("/auth/me");
      const { access_token, ...userData } = data;
      setUser(userData as User);
      useAuthStore.getState().setAccessToken(access_token ?? null);
    } catch {
      setUser(null);
      useAuthStore.getState().setAccessToken(null);
    } finally {
      authChecked = true;
      authCheckPromise = null;
    }
  })();
  return authCheckPromise;
}

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, setUser, setLoading, logout } = useAuthStore();

  // Check auth status once per session. /auth/me returns the access_token in
  // the body (httpOnly cookie isn't JS-readable) for WebSocket auth.
  useEffect(() => {
    void runAuthCheck(setUser);
    ensureTokenRefresh();
  }, [setUser]);

  const login = useCallback(
    async (credentials: LoginRequest) => {
      setLoading(true);
      try {
        const response = await apiClient.post<{
          user: User;
          access_token: string;
          message: string;
        }>("/auth/login", credentials);
        setUser(response.user);
        useAuthStore.getState().setAccessToken(response.access_token);
        authChecked = true; // login already populated user + token; skip /auth/me
        router.push(isAppAdmin(response.user) ? ROUTES.DASHBOARD : ROUTES.CHAT);
        return response;
      } finally {
        setLoading(false);
      }
    },
    [router, setUser, setLoading],
  );

  const register = useCallback(async (data: RegisterRequest) => {
    const response = await apiClient.post<{ id: string; email: string }>("/auth/register", data);
    return response;
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // Ignore logout errors
    } finally {
      authChecked = false; // re-check on next login
      authCheckPromise = null;
      stopTokenRefresh();
      logout();
      toast.success("Logged out");
      router.push(ROUTES.LOGIN);
    }
  }, [logout, router]);

  const refreshToken = useCallback(async () => {
    try {
      const refreshResponse = await apiClient.post<{ access_token: string; message: string }>(
        "/auth/refresh",
      );
      useAuthStore.getState().setAccessToken(refreshResponse.access_token);
      const userData = await apiClient.get<User>("/auth/me");
      setUser(userData);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        logout();
        router.push(ROUTES.LOGIN);
      }
      return false;
    }
  }, [logout, router, setUser]);

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout: handleLogout,
    refreshToken,
  };
}
