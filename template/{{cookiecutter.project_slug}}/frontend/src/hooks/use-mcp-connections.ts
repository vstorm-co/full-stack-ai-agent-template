"use client";

import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { qk } from "@/lib/query-keys";
import {
  createMcpConnection,
  deleteMcpConnection,
  listMcpConnections,
  listWorkspaceMcpServers,
  mcpToolPrefix,
  testMcpConnection,
  updateMcpConnection,
  type McpConnectionRecord,
  type McpConnectionTestResult,
} from "@/lib/mcp-connections-api";

interface UseMcpConnectionsResult {
  connections: McpConnectionRecord[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  create: (input: {
    name: string;
    url: string;
    auth_token?: string;
    allowed_tools?: string[] | null;
  }) => Promise<McpConnectionRecord>;
  update: (
    id: string,
    patch: {
      name?: string;
      url?: string;
      auth_token?: string;
      allowed_tools?: string[];
      clear_allowed_tools?: boolean;
      is_enabled?: boolean;
    },
  ) => Promise<McpConnectionRecord>;
  remove: (id: string) => Promise<void>;
  test: (id: string) => Promise<McpConnectionTestResult>;
}

/**
 * Manages the user's MCP server connections (Settings → Integrations).
 *
 * React Query owns the list; mutations patch the cache directly so the UI
 * stays instant. A test refetches the list because it updates last_status
 * on the backend. Mutation errors propagate as throws for toast handling.
 */
export function useMcpConnections(): UseMcpConnectionsResult {
  const queryClient = useQueryClient();

  const {
    data: connections = [],
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: qk.mcpConnections.list(),
    queryFn: listMcpConnections,
  });

  const error =
    queryError instanceof Error
      ? queryError.message
      : queryError
        ? "Failed to load connections"
        : null;

  const writeCache = useCallback(
    (updater: (prev: McpConnectionRecord[]) => McpConnectionRecord[]) =>
      queryClient.setQueryData<McpConnectionRecord[]>(qk.mcpConnections.list(), (prev = []) =>
        updater(prev),
      ),
    [queryClient],
  );

  const refresh = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const create = useCallback<UseMcpConnectionsResult["create"]>(
    async (input) => {
      const created = await createMcpConnection(input);
      writeCache((prev) => [...prev, created]);
      return created;
    },
    [writeCache],
  );

  const update = useCallback<UseMcpConnectionsResult["update"]>(
    async (id, patch) => {
      const updated = await updateMcpConnection(id, patch);
      writeCache((prev) => prev.map((r) => (r.id === id ? updated : r)));
      return updated;
    },
    [writeCache],
  );

  const remove = useCallback<UseMcpConnectionsResult["remove"]>(
    async (id) => {
      await deleteMcpConnection(id);
      writeCache((prev) => prev.filter((r) => r.id !== id));
    },
    [writeCache],
  );

  const test = useCallback<UseMcpConnectionsResult["test"]>(
    async (id) => {
      const result = await testMcpConnection(id);
      // The test persists last_status/last_checked_at server-side.
      await refetch();
      return result;
    },
    [refetch],
  );

  return { connections, isLoading, error, refresh, create, update, remove, test };
}

/**
 * Resolves a tool-call name to the MCP server it came from, or null for
 * built-in tools. Used to badge MCP-backed tool calls in the chat.
 *
 * Matching mirrors the backend prefix scheme (`{server}_{tool}`) using the
 * names of the user's enabled connections plus workspace servers — the same
 * names the agent used to build the prefixes, so this is authoritative for
 * the current user's own conversations.
 */
export function useMcpToolResolver(): (toolName: string) => string | null {
  const { data: connections = [] } = useQuery({
    queryKey: qk.mcpConnections.list(),
    queryFn: listMcpConnections,
    staleTime: 60_000,
  });
  const { data: workspace = [] } = useQuery({
    queryKey: qk.mcpConnections.workspace(),
    queryFn: listWorkspaceMcpServers,
    staleTime: 60_000,
  });

  // Longest prefix first so a more specific server wins over a shorter one
  // (e.g. "github_work" before "github").
  const byPrefix = useMemo(() => {
    const names = [
      ...connections.filter((c) => c.is_enabled).map((c) => c.name),
      ...workspace.map((w) => w.name),
    ];
    return names
      .map((name) => ({ name, prefix: mcpToolPrefix(name) }))
      .sort((a, b) => b.prefix.length - a.prefix.length);
  }, [connections, workspace]);

  return useCallback(
    (toolName: string) => {
      for (const { name, prefix } of byPrefix) {
        if (toolName === prefix || toolName.startsWith(`${prefix}_`)) return name;
      }
      return null;
    },
    [byPrefix],
  );
}
