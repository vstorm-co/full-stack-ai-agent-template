"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { Invitation, InvitationList, InviteMemberInput } from "@/types";

export function useInvitations(orgId: string) {
  const queryClient = useQueryClient();

  // React Query owns the list: cached per-org, deduped, no refetch storms.
  // Mutations patch the cache directly to keep the UI instant. The query stays
  // disabled until an orgId is provided (some consumers mount with "" to only
  // use acceptInvitation).
  const { data: invitations = [], isLoading } = useQuery({
    queryKey: qk.invitations.list(orgId),
    queryFn: async () =>
      (await apiClient.get<InvitationList>(`/orgs/${orgId}/invitations`)).items,
    enabled: !!orgId,
  });

  const writeCache = useCallback(
    (updater: (prev: Invitation[]) => Invitation[]) =>
      queryClient.setQueryData<Invitation[]>(qk.invitations.list(orgId), (prev = []) =>
        updater(prev),
      ),
    [queryClient, orgId],
  );

  // Kept for API compatibility: the list auto-fetches on mount; this forces a
  // background refresh.
  const fetchInvitations = useCallback(() => {
    if (!orgId) return;
    queryClient.invalidateQueries({ queryKey: qk.invitations.list(orgId) });
  }, [queryClient, orgId]);

  const invite = useCallback(
    async (input: InviteMemberInput): Promise<Invitation | null> => {
      try {
        const inv = await apiClient.post<Invitation>(`/orgs/${orgId}/invitations`, input);
        writeCache((prev) => [inv, ...prev]);
        toast.success(`Invitation sent to ${input.email}`);
        return inv;
      } catch {
        toast.error("Failed to send invitation");
        return null;
      }
    },
    [orgId, writeCache],
  );

  const revokeInvitation = useCallback(
    async (token: string) => {
      try {
        await apiClient.delete(`/invitations/${token}`);
        writeCache((prev) => prev.filter((i) => i.token !== token));
        toast.success("Invitation revoked");
      } catch {
        toast.error("Failed to revoke invitation");
      }
    },
    [writeCache],
  );

  const acceptInvitation = useCallback(async (token: string) => {
    try {
      await apiClient.post(`/invitations/${token}/accept`);
      toast.success("Joined organization!");
    } catch {
      toast.error("Failed to accept invitation");
    }
  }, []);

  return { invitations, isLoading, fetchInvitations, invite, revokeInvitation, acceptInvitation };
}

