"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";

export interface AdminUserRead {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_app_admin: boolean;
  created_at: string;
}

interface AdminUserList {
  items: AdminUserRead[];
  total: number;
}

interface ImpersonateResponse {
  access_token: string;
  token_type: string;
  impersonated_user_id: string;
  impersonated_by: string;
  expires_in: number;
}

export function useAdminUsers() {
  const [users, setUsers] = useState<AdminUserRead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [impersonating, setImpersonating] = useState<string | null>(null);

  const fetchUsers = useCallback(
    async ({
      skip = 0,
      limit = 50,
      search,
    }: { skip?: number; limit?: number; search?: string } = {}) => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
        if (search) params.set("search", search);
        const data = await apiClient.get<AdminUserList>(`/admin/users?${params}`);
        setUsers(data.items);
        setTotal(data.total);
      } catch {
        toast.error("Failed to load users");
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const updateUser = useCallback(async (userId: string, patch: Partial<AdminUserRead>) => {
    try {
      const updated = await apiClient.patch<AdminUserRead>(`/admin/users/${userId}`, patch);
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
      toast.success("User updated");
    } catch {
      toast.error("Failed to update user");
    }
  }, []);

  const deleteUser = useCallback(async (userId: string) => {
    try {
      await apiClient.delete(`/admin/users/${userId}`);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setTotal((t) => t - 1);
      toast.success("User deleted");
    } catch {
      toast.error("Failed to delete user");
    }
  }, []);

  const impersonateUser = useCallback(async (userId: string) => {
    setImpersonating(userId);
    try {
      const { access_token } = await apiClient.post<ImpersonateResponse>(
        `/admin/users/${userId}/impersonate`,
      );
      return access_token;
    } catch {
      toast.error("Failed to impersonate user");
      return null;
    } finally {
      setImpersonating(null);
    }
  }, []);

  return {
    users,
    total,
    isLoading,
    impersonating,
    fetchUsers,
    updateUser,
    deleteUser,
    impersonateUser,
  };
}
