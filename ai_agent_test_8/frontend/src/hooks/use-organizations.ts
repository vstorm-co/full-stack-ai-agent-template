"use client";

import { useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { useOrgStore } from "@/stores";
import type { Organization, OrganizationList, CreateOrganizationInput } from "@/types";

export function useOrganizations() {
  const queryClient = useQueryClient();
  const activeOrgId = useOrgStore((s) => s.activeOrgId);
  const setActiveOrgId = useOrgStore((s) => s.setActiveOrgId);

  // React Query owns the list: cached across navigations, deduped, no refetch
  // storms (this replaces the old session-singleton guard). Mutations patch the
  // cache directly so the UI stays instant.
  const { data: orgs = [] } = useQuery({
    queryKey: qk.organizations.list(),
    queryFn: async () => (await apiClient.get<OrganizationList>("/orgs")).items,
  });

  // Default the active org to the user's personal org (or the first one) once
  // the list loads and nothing is selected yet — preserves the behavior that
  // used to live inside fetchOrgs.
  useEffect(() => {
    if (activeOrgId) return;
    if (orgs.length === 0) return;
    const personal = orgs.find((o) => o.is_personal) ?? orgs[0];
    if (personal) setActiveOrgId(personal.id);
  }, [activeOrgId, orgs, setActiveOrgId]);

  const activeOrg = orgs.find((o) => o.id === activeOrgId) ?? null;

  const writeCache = useCallback(
    (updater: (prev: Organization[]) => Organization[]) =>
      queryClient.setQueryData<Organization[]>(qk.organizations.list(), (prev = []) =>
        updater(prev),
      ),
    [queryClient],
  );

  // Kept for API compatibility: the list auto-fetches on mount; this forces a
  // background refresh. The `force` arg is accepted for call-site compatibility
  // but invalidation always refetches.
  const fetchOrgs = useCallback(
    async (_force = false) => {
      await queryClient.invalidateQueries({ queryKey: qk.organizations.list() });
    },
    [queryClient],
  );

  const createOrg = useCallback(
    async (input: CreateOrganizationInput): Promise<Organization | null> => {
      try {
        const org = await apiClient.post<Organization>("/orgs", input);
        writeCache((prev) => [...prev, org]);
        toast.success("Organization created");
        return org;
      } catch {
        toast.error("Failed to create organization");
        return null;
      }
    },
    [writeCache],
  );

  const patchOrg = useCallback(
    async (id: string, patch: Partial<Pick<Organization, "name" | "avatar_url">>) => {
      try {
        const updated = await apiClient.patch<Organization>(`/orgs/${id}`, patch);
        writeCache((prev) => prev.map((o) => (o.id === id ? updated : o)));
        toast.success("Organization updated");
        return updated;
      } catch {
        toast.error("Failed to update organization");
        return null;
      }
    },
    [writeCache],
  );

  const deleteOrg = useCallback(
    async (id: string) => {
      try {
        await apiClient.delete(`/orgs/${id}`);
        writeCache((prev) => prev.filter((o) => o.id !== id));
        // Mirror the old store behavior: clear the active selection if it was
        // the org we just removed.
        if (useOrgStore.getState().activeOrgId === id) {
          setActiveOrgId(null);
        }
        toast.success("Organization deleted");
      } catch {
        toast.error("Failed to delete organization");
      }
    },
    [writeCache, setActiveOrgId],
  );

  const switchOrg = useCallback(
    (id: string) => {
      setActiveOrgId(id);
    },
    [setActiveOrgId],
  );

  return {
    orgs,
    activeOrgId,
    activeOrg,
    fetchOrgs,
    createOrg,
    patchOrg,
    deleteOrg,
    switchOrg,
  };
}
