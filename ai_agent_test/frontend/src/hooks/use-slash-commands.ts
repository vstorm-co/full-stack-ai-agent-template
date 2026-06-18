"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
 * Errors from individual mutations propagate as throws so the calling UI can
 * show a toast — they're never swallowed. The list state is refreshed
 * optimistically when a mutation succeeds.
 */
export function useSlashCommands(): UseSlashCommandsResult {
  const [records, setRecords] = useState<UserSlashCommandRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setRecords(await listSlashCommands());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load commands");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createCustom = useCallback<UseSlashCommandsResult["createCustom"]>(async (input) => {
    const created = await createCustomCommand(input);
    setRecords((prev) => [...prev, created]);
    return created;
  }, []);

  const updateCustom = useCallback<UseSlashCommandsResult["updateCustom"]>(async (id, patch) => {
    const updated = await updateSlashCommand(id, patch);
    setRecords((prev) => prev.map((r) => (r.id === id ? updated : r)));
    return updated;
  }, []);

  const setBuiltinEnabled = useCallback<UseSlashCommandsResult["setBuiltinEnabled"]>(
    async (name, isEnabled) => {
      const updated = await upsertBuiltinOverride({ name, is_enabled: isEnabled });
      setRecords((prev) => {
        const existing = prev.findIndex((r) => r.name === name && r.prompt === null);
        if (existing >= 0) {
          const next = prev.slice();
          next[existing] = updated;
          return next;
        }
        return [...prev, updated];
      });
    },
    [],
  );

  const remove = useCallback<UseSlashCommandsResult["remove"]>(async (id) => {
    await deleteSlashCommand(id);
    setRecords((prev) => prev.filter((r) => r.id !== id));
  }, []);

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
