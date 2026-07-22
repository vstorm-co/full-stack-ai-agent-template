"use client";

import { createContext, useContext, type ReactNode } from "react";

/**
 * True when tool cards are rendered inside a demo replay or the self-contained
 * export — never in a live chat. The MCP "plugin" badge (server logo + name) is
 * a demo-only affordance: it makes it obvious to a viewer that a tool call went
 * through an external MCP server, without cluttering the normal chat UI.
 */
const DemoModeContext = createContext(false);

export function DemoModeProvider({ children }: { children: ReactNode }) {
  return <DemoModeContext.Provider value={true}>{children}</DemoModeContext.Provider>;
}

export function useDemoMode(): boolean {
  return useContext(DemoModeContext);
}
