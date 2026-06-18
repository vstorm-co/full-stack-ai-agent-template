"use client";

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuthStore } from "@/stores";
import { apiClient, ApiError } from "@/lib/api-client";
import type { User, LoginRequest, RegisterRequest } from "@/types";
import { ROUTES } from "@/lib/constants";

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, setUser, setLoading, logout } = useAuthStore();

  // Check auth status on mount — always fetch fresh user data.
  // /auth/me returns the access_token in the body so we can use it for
  // WebSocket auth (cookie is httpOnly, not readable from JS).
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const data = await apiClient.get<User & { access_token?: string }>("/auth/me");
        const { access_token, ...userData } = data;
        setUser(userData as User);
        useAuthStore.getState().setAccessToken(access_token ?? null);
      } catch {
        setUser(null);
        useAuthStore.getState().setAccessToken(null);
      }
    };

    checkAuth();
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
        router.push(response.user.role === "admin" ? ROUTES.DASHBOARD : ROUTES.CHAT);
        return response;
      } catch (error) {
        throw error;
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
      // Re-fetch user after token refresh
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
