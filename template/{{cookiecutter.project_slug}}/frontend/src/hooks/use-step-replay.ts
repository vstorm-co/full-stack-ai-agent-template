"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, MessagePart } from "@/types";

/**
 * "Watch again" replay engine.
 *
 * Re-plays the steps the agent already took — thinking, tool calls and text, in their
 * saved order — so it looks like the agent is doing it for the first time. The agent is
 * NOT re-run: the script is reconstructed from the stored message and the frontend
 * controls the pacing. That controlled pacing is the point — live, a tool's call+result
 * arrive almost together; in replay every tool gets a visible beat before its result lands.
 *
 * Two consumers share the same per-turn player (`playTurn`):
 *  - `useStepReplay` — replays a single assistant turn in place.
 *  - `useConversationReplay` — replays a whole conversation sequentially (used by the demo page).
 */

const GAP_MS = 180;
const TOOL_RUNNING_MS = 950;
const RICH_TOOL_MS = 2000;

/** Tools whose working view streams content — give them a longer beat so the reveal finishes. */
const RICH_TOOLS = new Set<string>([
  "run_python",
  "load_skill",
  "web_search_tool",
  "search_web",
  "search_knowledge_base",
  "search_documents",
  "fetch_url",
]);

const STREAM_TICK_MS = 55;
const TEXT_TOTAL_MS = 3200;
const THINK_TOTAL_MS = 1100;

export const END_HOLD_MS = 700;

function scriptFromMessage(message: ChatMessage): MessagePart[] {
  if (message.parts && message.parts.length > 0) return message.parts;
  const parts: MessagePart[] = [];
  if (message.thinking) parts.push({ id: "rp-think", type: "thinking", content: message.thinking });
  (message.toolCalls ?? []).forEach((tc, i) =>
    parts.push({ id: `rp-tool-${i}`, type: "tool", toolCall: tc }),
  );
  if (message.content) parts.push({ id: "rp-text", type: "text", content: message.content });
  return parts;
}

export function canReplayMessage(message: ChatMessage): boolean {
  if (message.role !== "assistant") return false;
  return (
    (message.parts?.length ?? 0) > 0 ||
    (message.toolCalls?.length ?? 0) > 0 ||
    Boolean(message.thinking) ||
    Boolean(message.content)
  );
}

export interface ReplayToken {
  cancelled: boolean;
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * Play one assistant turn, emitting the progressively-built `parts` array on every visual
 * update. Starts with an empty streaming turn, then reveals each step (tool "working" →
 * result, typewriter text/thinking) with controlled pacing. Resolves when fully built.
 */
export async function playTurn(
  message: ChatMessage,
  emit: (parts: MessagePart[], isStreaming: boolean) => void,
  token: ReplayToken,
): Promise<void> {
  const script = scriptFromMessage(message);
  const built: MessagePart[] = [];

  const commit = (isStreaming = true) => {
    if (token.cancelled) return;
    emit(built.map((p) => ({ ...p })), isStreaming);
  };

  const typeInto = async (idx: number, part: MessagePart, full: string, totalMs: number) => {
    const stops: number[] = [];
    const re = /\S+\s*/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(full)) !== null) stops.push(m.index + m[0].length);
    const lastStop = stops.at(-1);
    if (lastStop === undefined || lastStop !== full.length) stops.push(full.length);

    const maxTicks = Math.max(1, Math.round(totalMs / STREAM_TICK_MS));
    const frames: number[] =
      stops.length <= maxTicks
        ? stops
        : Array.from({ length: maxTicks }, (_, i) => {
            const at = Math.min(stops.length - 1, Math.ceil(((i + 1) / maxTicks) * stops.length) - 1);
            return stops[at] ?? full.length;
          });

    for (const stop of frames) {
      if (token.cancelled) return;
      built[idx] = { ...part, content: full.slice(0, stop) };
      commit();
      await sleep(STREAM_TICK_MS);
    }
    if (token.cancelled) return;
    built[idx] = { ...part, content: full };
    commit();
  };

  emit([], true);
  await sleep(GAP_MS);

  for (const part of script) {
    if (token.cancelled) return;
    await sleep(GAP_MS);
    if (token.cancelled) return;

    if (part.type === "tool" && part.toolCall) {
      const tc = part.toolCall;
      const rich = RICH_TOOLS.has(tc.name);
      const idx = built.push({ ...part, toolCall: { ...tc, status: "running" } }) - 1;
      commit();
      await sleep(rich ? RICH_TOOL_MS : TOOL_RUNNING_MS);
      if (token.cancelled) return;
      built[idx] = { ...part, toolCall: { ...tc } };
      commit();
    } else if (part.type === "text" && part.content) {
      const idx = built.push({ ...part, content: "" }) - 1;
      commit();
      await typeInto(idx, part, part.content, TEXT_TOTAL_MS);
    } else if (part.type === "thinking" && part.content) {
      const idx = built.push({ ...part, content: "" }) - 1;
      commit();
      await typeInto(idx, part, part.content, THINK_TOTAL_MS);
    }
  }

  if (token.cancelled) return;
  commit(false);
}

/**
 * Single-turn "Watch again". Returns a synthetic `replayMessage` that is built up over
 * time; the consumer renders it in place of the real message while `isReplaying` is true.
 */
export function useStepReplay(message: ChatMessage) {
  const [replayMessage, setReplayMessage] = useState<ChatMessage | null>(null);
  const tokenRef = useRef<ReplayToken | null>(null);

  const stop = useCallback(() => {
    if (tokenRef.current) tokenRef.current.cancelled = true;
    setReplayMessage(null);
  }, []);

  useEffect(() => () => stop(), [stop]);

  const start = useCallback(() => {
    if (tokenRef.current) tokenRef.current.cancelled = true;
    const token: ReplayToken = { cancelled: false };
    tokenRef.current = token;

    const emit = (parts: MessagePart[], isStreaming: boolean) => {
      setReplayMessage((prev) => {
        const base = prev ?? { ...message, content: "", thinking: undefined, toolCalls: [] };
        return { ...base, parts, isStreaming };
      });
    };

    void (async () => {
      await playTurn(message, emit, token);
      if (token.cancelled) return;
      await sleep(END_HOLD_MS);
      if (token.cancelled) return;
      setReplayMessage(null);
    })();
  }, [message]);

  return { isReplaying: replayMessage !== null, replayMessage, start, stop };
}
