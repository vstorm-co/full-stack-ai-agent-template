/**
 * API client for user-scoped MCP server connections (Settings → Integrations).
 *
 * Each record points at a remote MCP server the assistant can pull tools
 * from. The bearer token is write-only: the backend stores it encrypted and
 * responses only carry `has_auth_token`.
 */

import { apiClient } from "./api-client";

export interface McpConnectionRecord {
  id: string;
  name: string;
  url: string;
  has_auth_token: boolean;
  /** null = every tool the server offers is exposed to the agent. */
  allowed_tools: string[] | null;
  is_enabled: boolean;
  /** "bearer" (static token) or "oauth" (authorization-code flow). */
  auth_type: "bearer" | "oauth";
  /** OAuth connection that finished consent and has usable tokens. */
  oauth_authorized: boolean;
  /** Result of the most recent connectivity check ("ok" / "error"), if any. */
  last_status: string | null;
  last_error: string | null;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface McpToolInfo {
  name: string;
  description: string;
}

export interface McpConnectionTestResult {
  ok: boolean;
  error: string | null;
  tools: McpToolInfo[];
}

interface McpConnectionList {
  items: McpConnectionRecord[];
  total: number;
}

export interface WorkspaceMcpServer {
  name: string;
  /** null = every tool the server offers. */
  allowed_tools: string[] | null;
}

/**
 * Connection name → tool-name prefix, mirroring the backend's `_tool_prefix`
 * (app/agents/mcp.py). The agent exposes each MCP tool as `{prefix}_{tool}`,
 * so the UI can recognise which tool calls came from an MCP server.
 */
export function mcpToolPrefix(name: string): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || "mcp";
}

const ROOT = "/me/mcp-connections";

export async function listWorkspaceMcpServers(): Promise<WorkspaceMcpServer[]> {
  const data = await apiClient.get<{ items: WorkspaceMcpServer[]; total: number }>(
    `${ROOT}/workspace`,
  );
  return data.items;
}

export async function listMcpConnections(): Promise<McpConnectionRecord[]> {
  const data = await apiClient.get<McpConnectionList>(ROOT);
  return data.items;
}

export async function createMcpConnection(input: {
  name: string;
  url: string;
  auth_token?: string;
  allowed_tools?: string[] | null;
  is_enabled?: boolean;
}): Promise<McpConnectionRecord> {
  return apiClient.post<McpConnectionRecord>(ROOT, input);
}

export async function updateMcpConnection(
  id: string,
  patch: {
    name?: string;
    url?: string;
    /** "" clears the stored token. */
    auth_token?: string;
    allowed_tools?: string[];
    clear_allowed_tools?: boolean;
    is_enabled?: boolean;
  },
): Promise<McpConnectionRecord> {
  return apiClient.patch<McpConnectionRecord>(`${ROOT}/${id}`, patch);
}

export async function deleteMcpConnection(id: string): Promise<void> {
  await apiClient.delete(`${ROOT}/${id}`);
}

export async function testMcpConnection(id: string): Promise<McpConnectionTestResult> {
  return apiClient.post<McpConnectionTestResult>(`${ROOT}/${id}/test`);
}

/**
 * Begin the OAuth flow for a server. Returns the provider consent URL — the
 * caller redirects the browser there; the provider sends the user back to the
 * `/oauth/callback` route, which finishes the exchange.
 */
export async function startMcpOAuth(input: {
  name: string;
  url: string;
}): Promise<{ authorization_url: string }> {
  return apiClient.post<{ authorization_url: string }>(`${ROOT}/oauth/start`, input);
}
