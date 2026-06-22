"use client";

import { create } from "zustand";
import type { ContextUsage, ResearchTodo, SubagentMessage, SubagentStatus } from "@/types";

/**
 * Per-turn state of deep-research runs: the planner's
 * subagents' statuses, and the context-window meter. Populated from the
 * `todo_event` / `subagent_status` / `context_usage` / `context_compacted`
 * WebSocket frames and rendered by the research panel. Keyed by the id of the
 * user message that started the turn so each turn keeps its own panel.
 */
export interface TurnResearch {
  todos: ResearchTodo[];
  subagents: SubagentStatus[];
  subagentMessages: Record<string, SubagentMessage[]>;
  contextUsage: ContextUsage | null;
  compactionCount: number;
  stopped: boolean;
}

interface ResearchState {
  byTurn: Record<string, TurnResearch>;
  currentTurnId: string | null;
  selectedSubagentId: string | null;

  beginTurn: (turnId: string) => void;
  applyTodoEvent: (eventType: string, todo: ResearchTodo) => void;
  upsertSubagent: (status: SubagentStatus) => void;
  addSubagentMessage: (msg: SubagentMessage) => void;
  setSelectedSubagent: (id: string | null) => void;
  setContextUsage: (usage: ContextUsage) => void;
  incrementCompaction: () => void;
  markCurrentTurnStopped: () => void;
  resetAll: () => void;
}

const EMPTY_TURN: TurnResearch = {
  todos: [],
  subagents: [],
  subagentMessages: {},
  contextUsage: null,
  compactionCount: 0,
  stopped: false,
};

function updateCurrent(
  state: ResearchState,
  fn: (turn: TurnResearch) => TurnResearch,
): Partial<ResearchState> {
  const id = state.currentTurnId;
  if (!id) return {};
  const current = state.byTurn[id] ?? EMPTY_TURN;
  return { byTurn: { ...state.byTurn, [id]: fn(current) } };
}

export const useResearchStore = create<ResearchState>((set) => ({
  byTurn: {},
  currentTurnId: null,
  selectedSubagentId: null,

  beginTurn: (turnId) =>
    set((state) => ({
      currentTurnId: turnId,
      byTurn: { ...state.byTurn, [turnId]: { ...EMPTY_TURN } },
    })),

  applyTodoEvent: (eventType, todo) =>
    set((state) =>
      updateCurrent(state, (turn) => {
        if (eventType === "deleted") {
          return { ...turn, todos: turn.todos.filter((t) => t.id !== todo.id) };
        }
        const idx = turn.todos.findIndex((t) => t.id === todo.id);
        if (idx === -1) return { ...turn, todos: [...turn.todos, todo] };
        const next = [...turn.todos];
        next[idx] = todo;
        return { ...turn, todos: next };
      }),
    ),

  upsertSubagent: (status) =>
    set((state) =>
      updateCurrent(state, (turn) => {
        const idx = turn.subagents.findIndex((s) => s.task_id === status.task_id);
        if (idx === -1) return { ...turn, subagents: [...turn.subagents, status] };
        const next = [...turn.subagents];
        next[idx] = status;
        return { ...turn, subagents: next };
      }),
    ),

  addSubagentMessage: (msg) =>
    set((state) =>
      updateCurrent(state, (turn) => {
        const prev = turn.subagentMessages[msg.task_id] ?? [];
        return {
          ...turn,
          subagentMessages: {
            ...turn.subagentMessages,
            [msg.task_id]: [...prev, msg],
          },
        };
      }),
    ),

  setSelectedSubagent: (id) => set({ selectedSubagentId: id }),

  setContextUsage: (usage) =>
    set((state) => updateCurrent(state, (turn) => ({ ...turn, contextUsage: usage }))),

  incrementCompaction: () =>
    set((state) =>
      updateCurrent(state, (turn) => ({ ...turn, compactionCount: turn.compactionCount + 1 })),
    ),

  markCurrentTurnStopped: () =>
    set((state) => updateCurrent(state, (turn) => ({ ...turn, stopped: true }))),

  resetAll: () => set({ byTurn: {}, currentTurnId: null, selectedSubagentId: null }),
}));
