{% raw %}/**
 * Slash command registry — drives the `/command` palette in <ChatInput>.
 *
 * Two layers:
 *   - BUILTIN_COMMANDS below — defined in code, shared across every user.
 *     Some are "client" actions (clear chat, open settings); others send a
 *     canned prompt as a user message.
 *   - User-defined commands fetched from `/api/v1/me/slash-commands`. Always
 *     "send-as-message" — they're just shortcuts for prompts the user types
 *     a lot. Settings page lets users disable individual built-ins, too.
 *
 * `mergeWithUserCommands()` fuses the two — that's what <ChatContainer> hands
 * down to <ChatInput>.
 */

import type { UserSlashCommandRecord } from "@/lib/slash-commands-api";

export type SlashCommandAction =
  | { kind: "client"; run: (ctx: SlashCommandContext) => void }
  | { kind: "send-as-message"; replaceWith: string };

export interface SlashCommand {
  /** No leading slash — e.g. "clear", "regen". */
  name: string;
  /** One-line description shown in the palette. */
  description: string;
  /** Optional alias slugs that also resolve to this command. */
  aliases?: string[];
  action: SlashCommandAction;
  /** Marks user-defined entries so the UI can label/edit them differently. */
  source?: "builtin" | "custom";
}

export interface SlashCommandContext {
  /** Clear all messages from the chat. */
  clearChat: () => void;
  /** Trigger a regeneration of the last assistant turn (no-op if none). */
  regenerateLast: () => void;
  /** Open the model picker / chat settings panel. */
  openSettings: () => void;
}

export const BUILTIN_COMMANDS: SlashCommand[] = [
  {
    name: "clear",
    description: "Clear the current chat (does not delete the conversation).",
    aliases: ["reset"],
    action: { kind: "client", run: (ctx) => ctx.clearChat() },
    source: "builtin",
  },
  {
    name: "regen",
    description: "Regenerate the last assistant response.",
    aliases: ["regenerate", "retry"],
    action: { kind: "client", run: (ctx) => ctx.regenerateLast() },
    source: "builtin",
  },
  {
    name: "settings",
    description: "Open chat settings (model, temperature, thinking).",
    action: { kind: "client", run: (ctx) => ctx.openSettings() },
    source: "builtin",
  },
  {
    name: "summarize",
    description: "Ask the agent to summarize the conversation so far.",
    action: {
      kind: "send-as-message",
      replaceWith:
        "Please give me a concise summary of our conversation so far — key topics, decisions, and any open questions.",
    },
    source: "builtin",
  },
  {
    name: "explain",
    description: "Ask the agent to explain its last response in simpler terms.",
    action: {
      kind: "send-as-message",
      replaceWith:
        "Explain your last response again, in simpler terms — assume I don't have technical background.",
    },
    source: "builtin",
  },
];

/**
 * Merge built-ins with the user's overrides + custom commands.
 *
 *   - Built-in disabled by user → dropped from the result.
 *   - User-defined custom command → appended (always "send-as-message").
 *   - Custom commands marked is_enabled=false → dropped.
 *
 * Pass an empty array for `userRecords` (e.g. before the API responds) to
 * get plain BUILTIN_COMMANDS.
 */
export function mergeWithUserCommands(userRecords: UserSlashCommandRecord[]): SlashCommand[] {
  const overridesByName = new Map<string, UserSlashCommandRecord>();
  const customs: SlashCommand[] = [];

  for (const r of userRecords) {
    if (r.prompt === null) {
      // Built-in override row — only the is_enabled flag matters.
      overridesByName.set(r.name, r);
    } else if (r.is_enabled) {
      customs.push({
        name: r.name,
        description: previewPrompt(r.prompt),
        action: { kind: "send-as-message", replaceWith: r.prompt },
        source: "custom",
      });
    }
  }

  const builtins = BUILTIN_COMMANDS.filter((c) => {
    const ovr = overridesByName.get(c.name);
    return ovr ? ovr.is_enabled : true;
  });

  return [...builtins, ...customs];
}

/** Truncate a stored prompt for the palette description line. */
function previewPrompt(prompt: string): string {
  const oneLine = prompt.replace(/\s+/g, " ").trim();
  return oneLine.length > 80 ? oneLine.slice(0, 77) + "…" : oneLine;
}

/**
 * Filter commands by a query — matches name + aliases by prefix, falls back
 * to substring on description.
 */
export function searchCommands(commands: SlashCommand[], query: string): SlashCommand[] {
  const q = query.toLowerCase().replace(/^\/+/, "");
  if (!q) return commands;
  const prefix = commands.filter((c) =>
    [c.name, ...(c.aliases ?? [])].some((s) => s.startsWith(q)),
  );
  if (prefix.length > 0) return prefix;
  return commands.filter(
    (c) =>
      c.name.includes(q) ||
      c.aliases?.some((a) => a.includes(q)) ||
      c.description.toLowerCase().includes(q),
  );
}
{% endraw %}
