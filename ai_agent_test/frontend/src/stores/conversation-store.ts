"use client";

import { create } from "zustand";
import type { Conversation, ConversationMessage } from "@/types";

interface ConversationState {
  conversations: Conversation[];
  currentConversationId: string | null;
  currentMessages: ConversationMessage[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  removeConversation: (id: string) => void;
  setCurrentConversationId: (id: string | null) => void;
  setCurrentMessages: (messages: ConversationMessage[]) => void;
  addMessage: (message: ConversationMessage) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  conversations: [],
  currentConversationId: null,
  currentMessages: [],
  isLoading: false,
  error: null,
};

export const useConversationStore = create<ConversationState>((set) => ({
  ...initialState,

  setConversations: (conversations) => set({ conversations }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...(state.conversations || [])],
    })),

  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: (state.conversations || []).map((conv) =>
        conv.id === id ? { ...conv, ...updates } : conv,
      ),
    })),

  removeConversation: (id) =>
    set((state) => ({
      conversations: (state.conversations || []).filter((conv) => conv.id !== id),
      currentConversationId:
        state.currentConversationId === id ? null : state.currentConversationId,
    })),

  setCurrentConversationId: (id) => set({ currentConversationId: id }),

  setCurrentMessages: (messages) => set({ currentMessages: messages }),

  addMessage: (message) =>
    set((state) => ({
      currentMessages: [...(state.currentMessages || []), message],
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}));
