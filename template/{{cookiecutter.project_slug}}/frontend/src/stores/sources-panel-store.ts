"use client";

import { create } from "zustand";
import type { SourceItem } from "@/lib/chat-sources";

interface SourcesPanelState {
  isOpen: boolean;
  sources: SourceItem[];
  highlightedIndex: number | null;
  open: (sources: SourceItem[], highlightedIndex?: number | null) => void;
  close: () => void;
}

export const useSourcesPanelStore = create<SourcesPanelState>((set) => ({
  isOpen: false,
  sources: [],
  highlightedIndex: null,
  open: (sources, highlightedIndex = null) => set({ isOpen: true, sources, highlightedIndex }),
  close: () => set({ isOpen: false, highlightedIndex: null }),
}));
