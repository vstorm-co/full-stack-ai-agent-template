"use client";
import { createContext, useContext } from "react";

/** Live browsing state, published by the demo replay so the chat's Web Search card can mirror the
 *  Agent's-computer animation instead of running an independent (drifting) spinner.
 *
 *  - `toolCallId` — the web-search tool call whose pages are being opened right now (or null).
 *  - `visitIndex` — the page the panel animation is currently on, so the chat spinner lands on the
 *    SAME row (true sync when the panel is open). `null` means there's no animation to mirror
 *    (panel closed / graph view) — the card then walks its own fast spinner.
 *
 *  The real app never provides this context, so it defaults to inert and the card behaves
 *  normally there. */
export interface BrowseActivity {
  toolCallId: string | null;
  visitIndex: number | null;
}

const BrowseActivityContext = createContext<BrowseActivity>({ toolCallId: null, visitIndex: null });

export const BrowseActivityProvider = BrowseActivityContext.Provider;

/** Browsing state for a given tool-call id: whether it's the active browse, and which page (if
 *  mirrored from the panel animation) its card should highlight. */
export function useBrowseState(toolCallId: string): { busy: boolean; visitIndex: number | null } {
  const ctx = useContext(BrowseActivityContext);
  return ctx.toolCallId === toolCallId
    ? { busy: true, visitIndex: ctx.visitIndex }
    : { busy: false, visitIndex: null };
}
