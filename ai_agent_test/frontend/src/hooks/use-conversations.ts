"use client";

import { useCallback, useRef } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { useConversationStore, useChatStore } from "@/stores";
import type { Conversation, ConversationMessage, ConversationListResponse } from "@/types";

interface CreateConversationResponse {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
}

interface MessagesResponse {
  items: ConversationMessage[];
  total: number;
}

export function useConversations() {
  const {
    conversations,
    currentConversationId,
    currentMessages,
    isLoading,
    error,
    setConversations,
    addConversation,
    updateConversation,
    removeConversation,
    setCurrentConversationId,
    setCurrentMessages,
    setLoading,
    setError,
  } = useConversationStore();
  const { clearMessages } = useChatStore();
  const hasMoreRef = useRef(true);
  const PAGE_SIZE = 30;

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch both active and archived in one call so the sidebar tabs can
      // partition them client-side. Archived items are filtered out of the
      // default tab, and surfaced only when the user opens "Archived".
      const response = await apiClient.get<ConversationListResponse>(
        `/conversations?limit=${PAGE_SIZE}&include_archived=true`,
      );
      setConversations(response.items);
      hasMoreRef.current = response.items.length >= PAGE_SIZE;
      // URL ?id= param always takes priority
      const urlId = new URLSearchParams(window.location.search).get("id");
      if (urlId && useConversationStore.getState().currentConversationId !== urlId) {
        setCurrentConversationId(urlId);
        clearMessages();
        setCurrentMessages([]);
        try {
          const msgs = await apiClient.get<MessagesResponse>(`/conversations/${urlId}/messages`);
          setCurrentMessages(msgs.items);
        } catch {
          // Not accessible (deleted, no permission) — clear the stale id
          setCurrentConversationId(null);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch conversations";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [
    setConversations,
    setLoading,
    setError,
    setCurrentConversationId,
    setCurrentMessages,
    clearMessages,
  ]);

  const loadingMoreRef = useRef(false);

  const fetchMoreConversations = useCallback(async () => {
    if (!hasMoreRef.current || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    const current = useConversationStore.getState().conversations;
    try {
      const response = await apiClient.get<ConversationListResponse>(
        `/conversations?limit=${PAGE_SIZE}&skip=${current.length}&include_archived=true`,
      );
      if (response.items.length > 0) {
        setConversations([...current, ...response.items]);
      }
      hasMoreRef.current = response.items.length >= PAGE_SIZE;
    } catch {
    } finally {
      loadingMoreRef.current = false;
    }
  }, [setConversations]);

  const createConversation = useCallback(
    async (title?: string): Promise<Conversation | null> => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.post<CreateConversationResponse>("/conversations", {
          title,
        });
        const newConversation: Conversation = {
          id: response.id,
          title: response.title,
          created_at: response.created_at,
          updated_at: response.updated_at,
          is_archived: response.is_archived,
        };
        addConversation(newConversation);
        return newConversation;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create conversation";
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [addConversation, setLoading, setError],
  );

  const selectConversation = useCallback(
    async (id: string) => {
      setCurrentConversationId(id);
      clearMessages();
      const url = new URL(window.location.href);
      url.searchParams.set("id", id);
      window.history.replaceState({}, "", url.toString());
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<MessagesResponse>(`/conversations/${id}/messages`);
        setCurrentMessages(response.items);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to fetch messages";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [setCurrentConversationId, clearMessages, setCurrentMessages, setLoading, setError],
  );

  const archiveConversation = useCallback(
    async (id: string) => {
      try {
        await apiClient.patch(`/conversations/${id}`, { is_archived: true });
        updateConversation(id, { is_archived: true });
        toast.success("Conversation archived");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to archive conversation";
        setError(message);
        toast.error(message);
      }
    },
    [updateConversation, setError],
  );

  const unarchiveConversation = useCallback(
    async (id: string) => {
      try {
        await apiClient.patch(`/conversations/${id}`, { is_archived: false });
        updateConversation(id, { is_archived: false });
        toast.success("Conversation restored");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to restore conversation";
        setError(message);
        toast.error(message);
      }
    },
    [updateConversation, setError],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      try {
        await apiClient.delete(`/conversations/${id}`);
        removeConversation(id);
        toast.success("Conversation deleted");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to delete conversation";
        setError(message);
        toast.error(message);
      }
    },
    [removeConversation, setError],
  );

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      try {
        await apiClient.patch(`/conversations/${id}`, { title });
        updateConversation(id, { title });
        toast.success("Conversation renamed");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to rename conversation";
        setError(message);
        toast.error(message);
      }
    },
    [updateConversation, setError],
  );
  const updateActiveKBs = useCallback(
    async (conversationId: string, kbIds: string[]) => {
      updateConversation(conversationId, { active_knowledge_base_ids: kbIds });
      try {
        await apiClient.patch(`/conversations/${conversationId}`, {
          active_knowledge_base_ids: kbIds,
        });
      } catch {
        toast.error("Failed to update knowledge bases");
      }
    },
    [updateConversation],
  );

  const startNewChat = useCallback(async () => {
    // If current conversation is empty (no messages), just reuse it
    const currentId = useConversationStore.getState().currentConversationId;
    if (currentId) {
      const msgs = useConversationStore.getState().currentMessages;
      if (msgs.length === 0) {
        clearMessages();
        return;
      }
    }
    clearMessages();
    setCurrentMessages([]);
    setCurrentConversationId(null);
    // Strip the stale ?id= immediately so a refresh mid-flight lands on a
    // fresh /chat instead of the old conversation. The new id will be set
    // by the WS conversation_created event on first message.
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (url.searchParams.has("id")) {
        url.searchParams.delete("id");
        window.history.replaceState({}, "", url.toString());
      }
    }
  }, [clearMessages, setCurrentMessages, setCurrentConversationId]);

  return {
    conversations,
    currentConversationId,
    currentMessages,
    isLoading,
    error,
    fetchConversations,
    fetchMoreConversations,
    hasMore: hasMoreRef.current,
    createConversation,
    selectConversation,
    archiveConversation,
    unarchiveConversation,
    deleteConversation,
    renameConversation,
    startNewChat,
    updateActiveKBs,
  };
}
