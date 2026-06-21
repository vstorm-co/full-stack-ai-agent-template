"use client";

import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { getErrorMessage } from "@/lib/utils";
import type {
  Conversation,
  ConversationListResponse,
  ConversationShare,
  ConversationShareListResponse,
} from "@/types";

export function useConversationShares() {
  const queryClient = useQueryClient();

  // The shares list belongs to whichever conversation was last requested via
  // fetchShares. React Query owns the cache; we just track which key is active.
  const [conversationId, setConversationId] = useState<string | null>(null);
  // shared-with-me is paginated; remember the last requested window.
  const [sharedWithMeParams, setSharedWithMeParams] = useState<{
    skip: number;
    limit: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sharesQuery = useQuery({
    queryKey: conversationId
      ? qk.conversationShares.list(conversationId)
      : qk.conversationShares.all(),
    queryFn: async () => {
      const response = await apiClient.get<ConversationShareListResponse>(
        `/conversations/${conversationId}/shares`,
      );
      return response.items;
    },
    enabled: !!conversationId,
  });

  const sharedWithMeQuery = useQuery({
    queryKey: sharedWithMeParams
      ? qk.conversationShares.sharedWithMe(sharedWithMeParams.skip, sharedWithMeParams.limit)
      : qk.conversationShares.sharedWithMe(0, 50),
    queryFn: async () => {
      const { skip, limit } = sharedWithMeParams!;
      return apiClient.get<ConversationListResponse>(
        `/conversations/shared-with-me?skip=${skip}&limit=${limit}`,
      );
    },
    enabled: !!sharedWithMeParams,
  });

  const shares: ConversationShare[] = sharesQuery.data ?? [];
  const sharedWithMe: Conversation[] = sharedWithMeQuery.data?.items ?? [];
  const sharedWithMeTotal = sharedWithMeQuery.data?.total ?? 0;
  const isLoading = sharesQuery.isFetching || sharedWithMeQuery.isFetching;

  const shareConversation = useCallback(
    async (
      conversationId: string,
      data: {
        shared_with?: string;
        permission?: "view" | "edit";
        generate_link?: boolean;
      },
    ) => {
      setError(null);
      try {
        const share = await apiClient.post<ConversationShare>(
          `/conversations/${conversationId}/shares`,
          data,
        );
        // Optimistically prepend so the dialog updates instantly, then refetch.
        queryClient.setQueryData<ConversationShare[]>(
          qk.conversationShares.list(conversationId),
          (prev = []) => [share, ...prev],
        );
        queryClient.invalidateQueries({
          queryKey: qk.conversationShares.list(conversationId),
        });
        return share;
      } catch (err: unknown) {
        const message = getErrorMessage(err, "Failed to share");
        setError(message);
        throw err;
      }
    },
    [queryClient],
  );

  const fetchShares = useCallback(
    async (conversationId: string) => {
      setError(null);
      setConversationId(conversationId);
      try {
        await queryClient.invalidateQueries({
          queryKey: qk.conversationShares.list(conversationId),
        });
      } catch (err: unknown) {
        const message = getErrorMessage(err, "Failed to load shares");
        setError(message);
      }
    },
    [queryClient],
  );

  const revokeShare = useCallback(
    async (conversationId: string, shareId: string) => {
      setError(null);
      try {
        await apiClient.delete(`/conversations/${conversationId}/shares/${shareId}`);
        queryClient.setQueryData<ConversationShare[]>(
          qk.conversationShares.list(conversationId),
          (prev = []) => prev.filter((s) => s.id !== shareId),
        );
        queryClient.invalidateQueries({
          queryKey: qk.conversationShares.list(conversationId),
        });
      } catch (err: unknown) {
        const message = getErrorMessage(err, "Failed to revoke");
        setError(message);
        throw err;
      }
    },
    [queryClient],
  );

  const fetchSharedWithMe = useCallback(
    async (skip = 0, limit = 50) => {
      setError(null);
      setSharedWithMeParams({ skip, limit });
      try {
        await queryClient.invalidateQueries({
          queryKey: qk.conversationShares.sharedWithMe(skip, limit),
        });
      } catch (err: unknown) {
        const message = getErrorMessage(err, "Failed to load shared");
        setError(message);
      }
    },
    [queryClient],
  );

  return {
    shares,
    sharedWithMe,
    sharedWithMeTotal,
    isLoading,
    error,
    shareConversation,
    fetchShares,
    revokeShare,
    fetchSharedWithMe,
  };
}
