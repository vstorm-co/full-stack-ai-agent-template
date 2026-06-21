"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { OrganizationMember, OrganizationMemberList, OrgRole } from "@/types";

export function useMembers(orgId: string) {
  const queryClient = useQueryClient();

  // React Query owns the list: cached per-org, deduped, no refetch storms.
  // We cache the full list response so `total` survives alongside `members`,
  // and mutations patch the cache directly to keep the UI instant.
  const { data, isLoading } = useQuery({
    queryKey: qk.organizations.members(orgId),
    queryFn: () => apiClient.get<OrganizationMemberList>(`/orgs/${orgId}/members`),
    enabled: !!orgId,
  });

  const members = data?.items ?? [];
  const total = data?.total ?? 0;

  const writeCache = useCallback(
    (updater: (prev: OrganizationMemberList) => OrganizationMemberList) =>
      queryClient.setQueryData<OrganizationMemberList>(
        qk.organizations.members(orgId),
        (prev = { items: [], total: 0 }) => updater(prev),
      ),
    [queryClient, orgId],
  );

  // Kept for API compatibility: the list auto-fetches on mount; this forces a
  // background refresh.
  const fetchMembers = useCallback(() => {
    if (!orgId) return;
    queryClient.invalidateQueries({ queryKey: qk.organizations.members(orgId) });
  }, [queryClient, orgId]);

  const changeRole = useCallback(
    async (userId: string, role: OrgRole) => {
      try {
        const updated = await apiClient.patch<OrganizationMember>(
          `/orgs/${orgId}/members/${userId}`,
          { role },
        );
        writeCache((prev) => ({
          ...prev,
          items: prev.items.map((m) => (m.user_id === userId ? updated : m)),
        }));
        toast.success("Role updated");
      } catch {
        toast.error("Failed to update role");
      }
    },
    [orgId, writeCache],
  );

  const removeMember = useCallback(
    async (userId: string) => {
      try {
        await apiClient.delete(`/orgs/${orgId}/members/${userId}`);
        writeCache((prev) => ({
          items: prev.items.filter((m) => m.user_id !== userId),
          total: prev.total - 1,
        }));
        toast.success("Member removed");
      } catch {
        toast.error("Failed to remove member");
      }
    },
    [orgId, writeCache],
  );

  return { members, total, isLoading, fetchMembers, changeRole, removeMember };
}
