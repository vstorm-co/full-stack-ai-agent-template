"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import type { ConnectorInfo, ConnectorList, SyncSourceCreate, SyncSourceList, SyncSourceRead } from "@/lib/rag-api";
import type { KnowledgeBase, KnowledgeBaseList } from "@/types";

export function useOrgIntegrations(orgId: string | null) {
  const [sources, setSources] = useState<SyncSourceRead[]>([]);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    try {
      const [srcList, connList, kbList] = await Promise.all([
        apiClient.get<SyncSourceList>(`/orgs/${orgId}/integrations`),
        apiClient.get<ConnectorList>(`/orgs/${orgId}/integrations/connectors`),
        apiClient.get<KnowledgeBaseList>("/kb").catch(() => ({ items: [] as KnowledgeBase[], total: 0 })),
      ]);
      setSources(srcList.items);
      setConnectors(connList.items);
      setKbs(kbList.items);
    } catch {
      toast.error("Failed to load integrations");
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    load();
  }, [load]);

  const createIntegration = useCallback(
    async (data: SyncSourceCreate) => {
      if (!orgId) return;
      setSubmitting(true);
      try {
        const created = await apiClient.post<SyncSourceRead>(`/orgs/${orgId}/integrations`, data);
        setSources((prev) => [created, ...prev]);
        toast.success("Integration created");
        return created;
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to create integration");
        throw e;
      } finally {
        setSubmitting(false);
      }
    },
    [orgId],
  );

  const deleteIntegration = useCallback(
    async (sourceId: string) => {
      if (!orgId) return;
      try {
        await apiClient.delete(`/orgs/${orgId}/integrations/${sourceId}`);
        setSources((prev) => prev.filter((s) => s.id !== sourceId));
        toast.success("Integration removed");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to remove integration");
      }
    },
    [orgId],
  );

  const triggerIntegration = useCallback(
    async (sourceId: string) => {
      if (!orgId) return;
      try {
        await apiClient.post(`/orgs/${orgId}/integrations/${sourceId}/trigger`);
        toast.success("Sync started");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to trigger sync");
      }
    },
    [orgId],
  );

  return {
    sources,
    connectors,
    kbs,
    isLoading,
    submitting,
    load,
    createIntegration,
    deleteIntegration,
    triggerIntegration,
  };
}
