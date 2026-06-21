"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface OrgState {
  // UI selection only — the orgs list itself is owned by React Query
  // (qk.organizations.list). This store persists which org the user picked.
  activeOrgId: string | null;
  setActiveOrgId: (id: string | null) => void;
}

export const useOrgStore = create<OrgState>()(
  persist(
    (set) => ({
      activeOrgId: null,
      setActiveOrgId: (id) => set({ activeOrgId: id }),
    }),
    {
      name: "org-storage",
      partialize: (state) => ({
        activeOrgId: state.activeOrgId,
      }),
    },
  ),
);
