"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Per-client chat-mode toggle: whether the next turn runs as a deep-research
 * turn (planner + parallel subagents + cited report) or as a normal chat turn.
 * Carried on the WS payload as `deep_research`. Persisted so the preferred mode
 * survives a refresh; the backend forces normal chat when the feature is off.
 */
interface ChatModeState {
  deepResearch: boolean;
  setDeepResearch: (on: boolean) => void;
  toggleDeepResearch: () => void;
}

export const useChatModeStore = create<ChatModeState>()(
  persist(
    (set) => ({
      deepResearch: false,
      setDeepResearch: (on) => set({ deepResearch: on }),
      toggleDeepResearch: () => set((s) => ({ deepResearch: !s.deepResearch })),
    }),
    {
      name: "chat-mode",
      version: 1,
    },
  ),
);
