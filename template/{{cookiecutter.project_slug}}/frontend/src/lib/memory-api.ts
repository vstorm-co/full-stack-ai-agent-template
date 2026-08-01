/**
 * API client for the current user's agent memory files.
 *
 * The agent maintains a per-user notebook of markdown files (MEMORY.md plus
 * optional extra notes). New files carry flat `*.md` names, but a name already
 * in the store may contain `/`, so the path travels as a query parameter rather
 * than a path segment. Writes are optimistic-concurrency: each file carries a
 * `version` and a stale save fails with 409.
 */

import { apiClient } from "./api-client";

export interface MemoryFileEntry {
  path: string;
  size_chars: number;
  version: string;
}

export interface MemoryFileContent {
  path: string;
  content: string;
  version: string;
  /** Content was cut to the server's per-file limit — do not save it back. */
  truncated: boolean;
}

export interface MemoryFileList {
  items: MemoryFileEntry[];
  total: number;
  /** The store holds more files than `items` carries. */
  truncated: boolean;
}

const ROOT = "/me/memory";

export async function listMemoryFiles(): Promise<MemoryFileList> {
  return apiClient.get<MemoryFileList>(ROOT);
}

export async function readMemoryFile(path: string): Promise<MemoryFileContent> {
  return apiClient.get<MemoryFileContent>(`${ROOT}/file`, { params: { path } });
}

export async function saveMemoryFile(
  path: string,
  input: { content: string; version: string | null },
): Promise<MemoryFileContent> {
  return apiClient.put<MemoryFileContent>(`${ROOT}/file`, input, { params: { path } });
}

export async function deleteMemoryFile(path: string, version: string): Promise<void> {
  await apiClient.delete(`${ROOT}/file`, { params: { path, version } });
}
