"use client";

import { useCallback, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { getErrorMessage, setUrlParam } from "@/lib/utils";
import { useConversationStore, useChatStore } from "@/stores";
import type { Conversation, ConversationMessage, ConversationListResponse } from "@/types";

interface CreateConversationResponse {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  is_demo?: boolean;
}

interface MessagesResponse {
  items: ConversationMessage[];
  total: number;
}

const PAGE_SIZE = 30;

export function useConversations() {
  const queryClient = useQueryClient();
  const {
    currentConversationId,
    currentMessages,
    isLoading: selectLoading,
    error,
    setCurrentConversationId,
    setCurrentMessages,
    setLoading,
    setError,
  } = useConversationStore();
  const { clearMessages } = useChatStore();
  const hasMoreRef = useRef(true);
  // Tracks the in-flight message fetch so a rapid conversation switch can abort
  // the previous request — otherwise a slower earlier fetch could resolve last
  // and overwrite the messages of the conversation the user actually selected.
  const messagesAbortRef = useRef<AbortController | null>(null);

  // React Query owns the list: cached across navigations, deduped, no refetch
  // storms (this replaces the old manual fetch + session-singleton guard).
  // Both active and archived are fetched in one call so the sidebar tabs can
  // partition them client-side. Mutations patch the cache directly.
  const { data: conversations = [], isLoading: listLoading } = useQuery({
    queryKey: qk.conversations.list(),
    queryFn: async () => {
      const response = await apiClient.get<ConversationListResponse>(
        `/conversations?limit=${PAGE_SIZE}&include_archived=true`,
      );
      hasMoreRef.current = response.items.length >= PAGE_SIZE;
      return response.items;
    },
  });

  // `isLoading` historically reflected both the list fetch and the
  // select-messages fetch; preserve that union.
  const isLoading = listLoading || selectLoading;

  const writeCache = useCallback(
    (updater: (prev: Conversation[]) => Conversation[]) =>
      queryClient.setQueryData<Conversation[]>(qk.conversations.list(), (prev = []) =>
        updater(prev),
      ),
    [queryClient],
  );

  const fetchConversations = useCallback(async () => {
    // The list query auto-fetches and dedupes; force a fresh pull here to keep
    // the previous explicit-refresh semantics (e.g. after a new conversation is
    // created over WS).
    await queryClient.invalidateQueries({ queryKey: qk.conversations.list() });
    // URL ?id= param always takes priority: select that conversation and load
    // its messages if it isn't already the current one.
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
  }, [queryClient, setCurrentConversationId, setCurrentMessages, clearMessages]);

  const loadingMoreRef = useRef(false);

  const fetchMoreConversations = useCallback(async () => {
    if (!hasMoreRef.current || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    const current = queryClient.getQueryData<Conversation[]>(qk.conversations.list()) ?? [];
    try {
      const response = await apiClient.get<ConversationListResponse>(
        `/conversations?limit=${PAGE_SIZE}&skip=${current.length}&include_archived=true`,
      );
      if (response.items.length > 0) {
        // Dedupe in case a refetch raced with the append.
        writeCache((prev) => {
          const seen = new Set(prev.map((c) => c.id));
          return [...prev, ...response.items.filter((c) => !seen.has(c.id))];
        });
      }
      hasMoreRef.current = response.items.length >= PAGE_SIZE;
    } catch {
    } finally {
      loadingMoreRef.current = false;
    }
  }, [queryClient, writeCache]);

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
          is_demo: response.is_demo ?? false,
        };
        writeCache((prev) => [newConversation, ...prev]);
        return newConversation;
      } catch (err) {
        const message = getErrorMessage(err, "Failed to create conversation");
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [writeCache, setLoading, setError],
  );

  const selectConversation = useCallback(
    async (id: string) => {
      // Abort any previous in-flight message fetch so an earlier, slower request
      // can't resolve after this one and show the wrong messages.
      messagesAbortRef.current?.abort();
      const controller = new AbortController();
      messagesAbortRef.current = controller;

      setCurrentConversationId(id);
      clearMessages();
      setUrlParam("id", id);
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.get<MessagesResponse>(`/conversations/${id}/messages`, {
          signal: controller.signal,
        });
        // Guard against a superseded request resolving after a newer select.
        if (controller.signal.aborted) return;
        setCurrentMessages(response.items);
      } catch (err) {
        // Ignore aborted/superseded requests — they're expected on rapid switch.
        if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) {
          return;
        }
        const message = getErrorMessage(err, "Failed to fetch messages");
        setError(message);
      } finally {
        // Only the most recent request owns the loading flag.
        if (messagesAbortRef.current === controller) {
          setLoading(false);
          messagesAbortRef.current = null;
        }
      }
    },
    [setCurrentConversationId, clearMessages, setCurrentMessages, setLoading, setError],
  );

  const archiveConversation = useCallback(
    async (id: string) => {
      try {
        await apiClient.patch(`/conversations/${id}`, { is_archived: true });
        writeCache((prev) => prev.map((c) => (c.id === id ? { ...c, is_archived: true } : c)));
        toast.success("Conversation archived");
      } catch (err) {
        const message = getErrorMessage(err, "Failed to archive conversation");
        setError(message);
        toast.error(message);
      }
    },
    [writeCache, setError],
  );

  const unarchiveConversation = useCallback(
    async (id: string) => {
      try {
        await apiClient.patch(`/conversations/${id}`, { is_archived: false });
        writeCache((prev) => prev.map((c) => (c.id === id ? { ...c, is_archived: false } : c)));
        toast.success("Conversation restored");
      } catch (err) {
        const message = getErrorMessage(err, "Failed to restore conversation");
        setError(message);
        toast.error(message);
      }
    },
    [writeCache, setError],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      try {
        await apiClient.delete(`/conversations/${id}`);
        writeCache((prev) => prev.filter((c) => c.id !== id));
        // Mirror the old store behavior: clear the active selection if it was
        // the conversation we just removed.
        if (useConversationStore.getState().currentConversationId === id) {
          setCurrentConversationId(null);
        }
        toast.success("Conversation deleted");
      } catch (err) {
        const message = getErrorMessage(err, "Failed to delete conversation");
        setError(message);
        toast.error(message);
      }
    },
    [writeCache, setCurrentConversationId, setError],
  );

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      try {
        await apiClient.patch(`/conversations/${id}`, { title });
        writeCache((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
        toast.success("Conversation renamed");
      } catch (err) {
        const message = getErrorMessage(err, "Failed to rename conversation");
        setError(message);
        toast.error(message);
      }
    },
    [writeCache, setError],
  );
  const updateActiveKBs = useCallback(
    async (conversationId: string, kbIds: string[]) => {
      writeCache((prev) =>
        prev.map((c) =>
          c.id === conversationId ? { ...c, active_knowledge_base_ids: kbIds } : c,
        ),
      );
      try {
        await apiClient.patch(`/conversations/${conversationId}`, {
          active_knowledge_base_ids: kbIds,
        });
      } catch {
        toast.error("Failed to update knowledge bases");
      }
    },
    [writeCache],
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
    setUrlParam("id", null);
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
