"use client";

import { create } from "zustand";
import type { ChatMessageFile } from "@/types";

interface FilePreviewState {
  /** Currently-opened file metadata. null = panel closed. */
  file: ChatMessageFile | null;
  open: (file: ChatMessageFile) => void;
  close: () => void;
}

export const useFilePreviewStore = create<FilePreviewState>((set) => ({
  file: null,
  open: (file) => set({ file }),
  close: () => set({ file: null }),
}));
