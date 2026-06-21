"use client";

import { useCallback, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/utils";
import type {
  AdminConversation,
  AdminConversationListResponse,
  AdminUser,
  AdminUserListResponse,
  ConversationWithMessages,
} from "@/types";

export function useAdminConversations() {
  const [conversations, setConversations] = useState<AdminConversation[]>([]);
  const [conversationsTotal, setConversationsTotal] = useState(0);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [selectedConversation, setSelectedConversation] = useState<ConversationWithMessages | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadingCount = useRef(0);
  const startLoad = () => {
    loadingCount.current++;
    setIsLoading(true);
  };
  const endLoad = () => {
    loadingCount.current = Math.max(0, loadingCount.current - 1);
    if (loadingCount.current === 0) setIsLoading(false);
  };

  const fetchConversations = useCallback(
    async (params?: {
      skip?: number;
      limit?: number;
      search?: string;
      user_id?: string;
      status?: "active" | "archived" | "all";
      sort_by?: string;
      sort_dir?: "asc" | "desc";
    }) => {
      startLoad();
      setError(null);
      try {
        const query = new URLSearchParams();
        if (params?.skip) query.set("skip", String(params.skip));
        if (params?.limit) query.set("limit", String(params.limit));
        if (params?.search) query.set("search", params.search);
        if (params?.user_id) query.set("user_id", params.user_id);
        if (params?.status) query.set("status", params.status);
        if (params?.sort_by) query.set("sort_by", params.sort_by);
        if (params?.sort_dir) query.set("sort_dir", params.sort_dir);

        const response = await apiClient.get<AdminConversationListResponse>(
          `/admin/conversations?${query.toString()}`,
        );
        setConversations(response.items);
        setConversationsTotal(response.total);
      } catch (err: unknown) {
        const message = getErrorMessage(err, "Failed to load conversations");
        setError(message);
      } finally {
        endLoad();
      }
    },
    [],
  );

  const fetchUsers = useCallback(
    async (params?: {
      skip?: number;
      limit?: number;
      search?: string;
      sort_by?: string;
      sort_dir?: "asc" | "desc";
    }) => {
      startLoad();
      setError(null);
      try {
        const query = new URLSearchParams();
        if (params?.skip) query.set("skip", String(params.skip));
        if (params?.limit) query.set("limit", String(params.limit));
        if (params?.search) query.set("search", params.search);
        if (params?.sort_by) query.set("sort_by", params.sort_by);
        if (params?.sort_dir) query.set("sort_dir", params.sort_dir);

        const response = await apiClient.get<AdminUserListResponse>(
          `/admin/conversations/users?${query.toString()}`,
        );
        setUsers(response.items);
        setUsersTotal(response.total);
      } catch (err: unknown) {
        const message = getErrorMessage(err, "Failed to load users");
        setError(message);
      } finally {
        endLoad();
      }
    },
    [],
  );

  const fetchConversationDetail = useCallback(async (conversationId: string) => {
    startLoad();
    setError(null);
    try {
      const conv = await apiClient.get<ConversationWithMessages>(
        `/admin/conversations/${conversationId}`,
      );
      setSelectedConversation(conv);
      return conv;
    } catch (err: unknown) {
      const message = getErrorMessage(err, "Failed to load conversation");
      setError(message);
      return null;
    } finally {
      endLoad();
    }
  }, []);

  return {
    conversations,
    conversationsTotal,
    users,
    usersTotal,
    selectedConversation,
    isLoading,
    error,
    fetchConversations,
    fetchUsers,
    fetchConversationDetail,
    setSelectedConversation,
  };
}
