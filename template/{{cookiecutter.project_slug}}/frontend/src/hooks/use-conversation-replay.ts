"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage } from "@/types";
import { canReplayMessage, END_HOLD_MS, playTurn, type ReplayToken } from "./use-step-replay";

/**
 * Whole-conversation "Watch again" for the public demo page.
 *
 * Replays an entire saved conversation sequentially — user messages pop in, assistant turns
 * build their tools + text live via the shared `playTurn` engine. Nothing is re-run against
 * the backend; all pacing is driven from the stored messages.
 *
 * `tick` bumps on every visual update so the page can keep the view auto-scrolled.
 */

const START_DELAY_MS = 250;
const USER_REVEAL_MS = 500;
const STEP_HOLD_MS = END_HOLD_MS;

interface ReplayPhase {
  playing: boolean;
  /** Number of fully-committed messages shown (never includes the currently-playing one). */
  revealed: number;
  /** Assistant turn being actively built — appended after `revealed` messages. */
  active: ChatMessage | null;
}

const IDLE: ReplayPhase = { playing: false, revealed: 0, active: null };

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export function useConversationReplay(messages: ChatMessage[]) {
  const [phase, setPhase] = useState<ReplayPhase>(IDLE);
  const [tick, setTick] = useState(0);
  const tokenRef = useRef<ReplayToken | null>(null);

  const bump = useCallback(() => setTick((t) => t + 1), []);

  const stop = useCallback(() => {
    if (tokenRef.current) tokenRef.current.cancelled = true;
    setPhase(IDLE);
  }, []);

  useEffect(() => () => stop(), [stop]);

  const start = useCallback(() => {
    if (tokenRef.current) tokenRef.current.cancelled = true;
    const token: ReplayToken = { cancelled: false };
    tokenRef.current = token;

    void (async () => {
      setPhase({ playing: true, revealed: 0, active: null });
      bump();
      await sleep(START_DELAY_MS);

      for (let i = 0; i < messages.length; i++) {
        if (token.cancelled) return;
        const msg = messages[i];
        if (!msg) continue;

        if (msg.role === "assistant" && canReplayMessage(msg)) {
          // Start with empty active message — revealed stays at i (doesn't include this turn).
          setPhase({
            playing: true,
            revealed: i,
            active: {
              ...msg,
              parts: [],
              content: "",
              thinking: undefined,
              toolCalls: [],
              isStreaming: true,
            },
          });
          bump();
          await playTurn(
            msg,
            (parts, isStreaming) => {
              // Keep content/toolCalls empty — MessageItem falls back to the legacy
              // path when parts=[] and would show the full stored text via msg.content.
              // Parts exclusively drive what's rendered during replay.
              setPhase((p) => ({
                ...p,
                active: { ...msg, parts, content: "", toolCalls: [], isStreaming },
              }));
              bump();
            },
            token,
          );
          if (token.cancelled) return;
          await sleep(STEP_HOLD_MS);
          if (token.cancelled) return;
          // Commit: move this turn into the revealed history, clear active.
          setPhase({ playing: true, revealed: i + 1, active: null });
          bump();
        } else {
          // User / system message — pop in immediately.
          setPhase((p) => ({ ...p, revealed: i + 1, active: null }));
          bump();
          await sleep(USER_REVEAL_MS);
        }
      }

      if (token.cancelled) return;
      setPhase(IDLE);
    })();
  }, [messages, bump]);

  const displayMessages = useMemo(() => {
    if (!phase.playing) return messages;
    const shown = messages.slice(0, phase.revealed);
    // Active message is appended — never replaces an existing entry — so no full-message flash.
    return phase.active ? [...shown, phase.active] : shown;
  }, [messages, phase]);

  return { isReplaying: phase.playing, displayMessages, tick, start, stop };
}
