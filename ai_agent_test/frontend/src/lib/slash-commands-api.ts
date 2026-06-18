/**
 * API client for user-scoped slash command settings.
 *
 * Two row shapes share one table on the backend:
 *  - "custom"  → user-defined `/<name>` shortcuts (prompt is set)
 *  - "builtin-override" → on/off flag for one of the built-ins (prompt is null)
 */

import { apiClient } from "./api-client";

export interface UserSlashCommandRecord {
  id: string;
  name: string;
  /** null for built-in overrides; non-null for user-defined custom commands. */
  prompt: string | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string | null;
}

interface UserSlashCommandList {
  items: UserSlashCommandRecord[];
  total: number;
}

const ROOT = "/me/slash-commands";

export async function listSlashCommands(): Promise<UserSlashCommandRecord[]> {
  const data = await apiClient.get<UserSlashCommandList>(ROOT);
  return data.items;
}

export async function createCustomCommand(input: {
  name: string;
  prompt: string;
  is_enabled?: boolean;
}): Promise<UserSlashCommandRecord> {
  return apiClient.post<UserSlashCommandRecord>(`${ROOT}/custom`, input);
}

export async function upsertBuiltinOverride(input: {
  name: string;
  is_enabled: boolean;
}): Promise<UserSlashCommandRecord> {
  return apiClient.put<UserSlashCommandRecord>(`${ROOT}/builtin`, input);
}

export async function updateSlashCommand(
  id: string,
  patch: { name?: string; prompt?: string; is_enabled?: boolean },
): Promise<UserSlashCommandRecord> {
  return apiClient.patch<UserSlashCommandRecord>(`${ROOT}/${id}`, patch);
}

export async function deleteSlashCommand(id: string): Promise<void> {
  await apiClient.delete(`${ROOT}/${id}`);
}
