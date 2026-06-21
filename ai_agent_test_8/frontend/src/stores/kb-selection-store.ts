"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Draft selection of active knowledge bases for the *next* (or current)
 * conversation. Persisted to localStorage so the user's preferred KB set
 * survives a page refresh / new browser tab.
 *
 * Two states co-exist with the per-conversation row in the database:
 *  - When the chat hasn't created a conversation yet, this store is the
 *    only source of truth — the WS payload carries it as
 *    ``active_knowledge_base_ids`` so the first agent turn already searches
 *    the chosen KBs.
 *  - Once a conversation exists, the draft IS the conversation's value:
 *    toggling either side hits the backend, and on load we hydrate from the
 *    conversation row to overwrite any stale local state.
 */
interface KBSelectionState {
  activeKBIds: string[];
  setActiveKBIds: (ids: string[]) => void;
  toggle: (id: string) => void;
  clear: () => void;
  /** Hydrate from a conversation that the user just opened. */
  hydrateFromConversation: (ids: string[] | null | undefined) => void;
}

export const useKBSelectionStore = create<KBSelectionState>()(
  persist(
    (set, get) => ({
      activeKBIds: [],
      setActiveKBIds: (ids) => set({ activeKBIds: Array.from(new Set(ids)) }),
      toggle: (id) => {
        const current = get().activeKBIds;
        const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
        set({ activeKBIds: next });
      },
      clear: () => set({ activeKBIds: [] }),
      hydrateFromConversation: (ids) => {
        // Only overwrite when the conversation has its own selection. ``null``
        // means "use defaults" — keep the local draft as a hint for future
        // edits in this conversation.
        if (Array.isArray(ids)) set({ activeKBIds: ids });
      },
    }),
    {
      name: "kb-selection",
      version: 1,
    },
  ),
);
