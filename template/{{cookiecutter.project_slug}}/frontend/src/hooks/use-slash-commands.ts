"use client";

import { useCallback, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { qk } from "@/lib/query-keys";
import {
  createCustomCommand,
  deleteSlashCommand,
  listSlashCommands,
  updateSlashCommand,
  upsertBuiltinOverride,
  type UserSlashCommandRecord,
} from "@/lib/slash-commands-api";
import {
  BUILTIN_COMMANDS,
  mergeWithUserCommands,
  type SlashCommand,
} from "@/components/chat/slash-commands";

interface UseSlashCommandsResult {
  /** Raw rows from the backend (custom commands + built-in overrides). */
  records: UserSlashCommandRecord[];
  /** Effective list, with overrides applied — pass to <ChatInput>. */
  commands: SlashCommand[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  createCustom: (input: { name: string; prompt: string }) => Promise<UserSlashCommandRecord>;
  updateCustom: (
    id: string,
    patch: { name?: string; prompt?: string; is_enabled?: boolean },
  ) => Promise<UserSlashCommandRecord>;
  setBuiltinEnabled: (name: string, isEnabled: boolean) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

/**
 * Manages the user's slash command settings.
 *
 * React Query owns the list: cached across navigations, deduped, no refetch
 * storms. Mutations patch the cache directly so the UI stays instant.
 *
 * Errors from individual mutations propagate as throws so the calling UI can
 * show a toast — they're never swallowed.
 */
export function useSlashCommands(): UseSlashCommandsResult {
  const queryClient = useQueryClient();

  const {
    data: records = [],
    isLoading,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: qk.slashCommands.list(),
    queryFn: listSlashCommands,
  });

  const error = queryError instanceof Error ? queryError.message : queryError ? "Failed to load commands" : null;

  const writeCache = useCallback(
    (updater: (prev: UserSlashCommandRecord[]) => UserSlashCommandRecord[]) =>
      queryClient.setQueryData<UserSlashCommandRecord[]>(qk.slashCommands.list(), (prev = []) =>
        updater(prev),
      ),
    [queryClient],
  );

  // Kept for API compatibility: the list auto-fetches on mount; this forces a
  // background refresh and resolves once the refetch settles.
  const refresh = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const createCustom = useCallback<UseSlashCommandsResult["createCustom"]>(
    async (input) => {
      const created = await createCustomCommand(input);
      writeCache((prev) => [...prev, created]);
      return created;
    },
    [writeCache],
  );

  const updateCustom = useCallback<UseSlashCommandsResult["updateCustom"]>(
    async (id, patch) => {
      const updated = await updateSlashCommand(id, patch);
      writeCache((prev) => prev.map((r) => (r.id === id ? updated : r)));
      return updated;
    },
    [writeCache],
  );

  const setBuiltinEnabled = useCallback<UseSlashCommandsResult["setBuiltinEnabled"]>(
    async (name, isEnabled) => {
      const updated = await upsertBuiltinOverride({ name, is_enabled: isEnabled });
      writeCache((prev) => {
        const existing = prev.findIndex((r) => r.name === name && r.prompt === null);
        if (existing >= 0) {
          const next = prev.slice();
          next[existing] = updated;
          return next;
        }
        return [...prev, updated];
      });
    },
    [writeCache],
  );

  const remove = useCallback<UseSlashCommandsResult["remove"]>(
    async (id) => {
      await deleteSlashCommand(id);
      writeCache((prev) => prev.filter((r) => r.id !== id));
    },
    [writeCache],
  );

  const commands = useMemo(() => mergeWithUserCommands(records), [records]);

  return {
    records,
    commands,
    isLoading,
    error,
    refresh,
    createCustom,
    updateCustom,
    setBuiltinEnabled,
    remove,
  };
}

/**
 * Helper used by the settings UI to figure out, for a given built-in,
 * whether it's currently enabled given the override state.
 */
export function isBuiltinEnabled(name: string, records: UserSlashCommandRecord[]): boolean {
  const ovr = records.find((r) => r.name === name && r.prompt === null);
  return ovr ? ovr.is_enabled : true;
}

/** Static list of built-in commands for settings UI. */
export const BUILTIN_COMMAND_LIST = BUILTIN_COMMANDS;
