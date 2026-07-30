"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { qk } from "@/lib/query-keys";
import { ApiError } from "@/lib/api-client";
import {
  deleteMemoryFile,
  listMemoryFiles,
  saveMemoryFile,
  type MemoryFileContent,
  type MemoryFileEntry,
} from "@/lib/memory-api";

interface UseMemoryFilesResult {
  files: MemoryFileEntry[];
  /** The store holds more files than `files` carries. */
  truncated: boolean;
  /** The deployment runs without agent memory — nothing to show or retry. */
  disabled: boolean;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  save: (
    path: string,
    input: { content: string; version: string | null },
  ) => Promise<MemoryFileContent>;
  remove: (path: string, version: string) => Promise<void>;
}

const EMPTY_LIST = { items: [] as MemoryFileEntry[], total: 0, truncated: false };

/**
 * Manages the user's agent memory files.
 *
 * React Query owns the listing; file content is fetched imperatively where it is
 * needed, because every save needs the freshest CAS version anyway. Mutations
 * refetch the list so sizes and versions are always current. Errors propagate as
 * throws so the calling UI can toast them.
 */
export function useMemoryFiles(): UseMemoryFilesResult {
  const queryClient = useQueryClient();

  const {
    data = EMPTY_LIST,
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: qk.memory.list(),
    queryFn: listMemoryFiles,
  });

  // A 503 means the feature is switched off, which is a state to explain rather
  // than an error to retry.
  const disabled = queryError instanceof ApiError && queryError.status === 503;
  const error = disabled
    ? null
    : queryError instanceof Error
      ? queryError.message
      : queryError
        ? "Failed to load memory"
        : null;

  const refresh = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const save = useCallback<UseMemoryFilesResult["save"]>(
    async (path, input) => {
      const updated = await saveMemoryFile(path, input);
      await queryClient.invalidateQueries({ queryKey: qk.memory.list() });
      return updated;
    },
    [queryClient],
  );

  const remove = useCallback<UseMemoryFilesResult["remove"]>(
    async (path, version) => {
      await deleteMemoryFile(path, version);
      await queryClient.invalidateQueries({ queryKey: qk.memory.list() });
    },
    [queryClient],
  );

  return {
    files: data.items,
    truncated: data.truncated,
    disabled,
    isLoading,
    error,
    refresh,
    save,
    remove,
  };
}
