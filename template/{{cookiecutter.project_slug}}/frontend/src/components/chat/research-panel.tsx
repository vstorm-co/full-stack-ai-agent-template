"use client";

import { useEffect, useRef, useState } from "react";
import { useResearchStore } from "@/stores";
import type { ResearchTodo, SubagentStatus } from "@/types";
import { Card, Badge, Progress } from "@/components/ui";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  CircleDashed,
  Gauge,
  Loader2,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Deep-research tool names hidden from the transcript and surfaced in the panel
 * instead. A research turn spans several step-messages, so these calls would
 * otherwise render as dozens of separate cards. `message-item.tsx` imports this
 * to drop them; this panel aggregates them into one live expander. Mirrors the
 * backend `RESEARCH_TOOL_NAMES` in `app/services/research.py`.
 */
export const RESEARCH_TOOL_NAMES = new Set([
  "add_todo",
  "update_todo_status",
  "write_todos",
  "remove_todo",
  "add_subtask",
  "set_dependency",
  "read_todos",
  "get_available_tasks",
  "task",
  "wait_tasks",
  "check_task",
  "list_active_tasks",
  "send_message_to_subagent",
  "answer_subagent",
]);

const EMPTY_TODOS: ResearchTodo[] = [];
const EMPTY_SUBAGENTS: SubagentStatus[] = [];

const TASK_DONE: ReadonlySet<SubagentStatus["status"]> = new Set([
  "completed",
  "failed",
  "cancelled",
]);
const TASK_ACTIVE: ReadonlySet<SubagentStatus["status"]> = new Set([
  "pending",
  "running",
  "retrying",
  "waiting_for_answer",
]);

/**
 * One live, collapsible expander for a deep-research turn: a header with a
 * spinner and a done/total counter, and (when expanded) the planner's
 * checklist, the delegated subagents with their statuses, and a context-window
 * meter. Rendered inline as an assistant message (Bot avatar + indented content)
 * where the run was invoked. Renders nothing until research state arrives.
 */
export function ResearchPanel({ turnId }: { turnId: string }) {
  const turn = useResearchStore((s) => s.byTurn[turnId]);
  const todos = turn?.todos ?? EMPTY_TODOS;
  const subagents = turn?.subagents ?? EMPTY_SUBAGENTS;
  const contextUsage = turn?.contextUsage ?? null;
  const compactionCount = turn?.compactionCount ?? 0;

  const taskTotal = subagents.length;
  const taskDone = subagents.filter((s) => s.status === "completed").length;
  const todoTotal = todos.length;
  const todoDone = todos.filter((t) => t.status === "completed").length;

  const stopped = turn?.stopped ?? false;
  const anyTaskActive = subagents.some((s) => TASK_ACTIVE.has(s.status));
  const anyTodoActive = todos.some((t) => t.status === "in_progress" || t.status === "pending");
  const hasAnything = todoTotal > 0 || taskTotal > 0;
  const done = stopped || (hasAnything && !anyTaskActive && !anyTodoActive);
  const busy = !done;

  const [expanded, setExpanded] = useState(true);
  const wasDone = useRef(false);
  useEffect(() => {
    if (done && !wasDone.current) setExpanded(false);
    else if (!done && wasDone.current) setExpanded(true);
    wasDone.current = done;
  }, [done]);

  if (todoTotal === 0 && taskTotal === 0) return null;

  const [counterDone, counterTotal, counterLabel] =
    todoTotal > 0
      ? [todoDone, todoTotal, "steps"]
      : taskTotal > 0
        ? [taskDone, taskTotal, "tasks"]
        : [0, 0, ""];
  const counter = counterTotal > 0 ? `${counterDone}/${counterTotal} ${counterLabel}` : "Planning…";

  return (
    <div className="relative flex gap-2 overflow-visible py-3 sm:gap-4 sm:py-4">
      <div className="bg-orange-500/10 text-orange-500 z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-full sm:h-9 sm:w-9">
        <Bot className="h-4 w-4 sm:h-5 sm:w-5" />
      </div>
      <div className="min-w-0 max-w-[88%] flex-1 space-y-2 overflow-hidden sm:max-w-[85%]">
        <Card className="overflow-hidden py-0">
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            aria-expanded={expanded}
            className="hover:bg-foreground/[0.03] flex w-full items-center gap-2 px-4 py-3 text-left transition-colors"
          >
            <Sparkles className="text-primary h-4 w-4 shrink-0" />
            <span className="text-sm font-semibold">Deep research</span>
            {busy ? (
              <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
            )}
            <span className="text-muted-foreground shrink-0 font-mono text-xs tabular-nums">
              {counter}
            </span>
            {counterTotal > 0 && (
              <Progress
                value={Math.round((counterDone / counterTotal) * 100)}
                className="mx-1 h-1.5 min-w-0 flex-1"
              />
            )}
            <span className="flex-1" />
            {expanded ? (
              <ChevronUp className="text-muted-foreground h-4 w-4 shrink-0" />
            ) : (
              <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0" />
            )}
          </button>

          {expanded && (
            <div className="space-y-4 px-4 pb-4">
              <ResearchChecklist todos={todos} />
              {subagents.length > 0 && <SubagentList subagents={subagents} />}
              {contextUsage && (
                <ContextMeter
                  pct={contextUsage.pct}
                  current={contextUsage.current}
                  max={contextUsage.max}
                  compactionCount={compactionCount}
                />
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: ResearchTodo["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />;
    case "in_progress":
      return <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />;
    case "blocked":
      return <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />;
    default:
      return <Circle className="text-muted-foreground/50 h-4 w-4 shrink-0" />;
  }
}

function ResearchChecklist({ todos }: { todos: ResearchTodo[] }) {
  if (todos.length === 0) {
    return (
      <div className="text-muted-foreground flex items-center gap-2 text-xs">
        <CircleDashed className="h-3.5 w-3.5 animate-spin" />
        Planning…
      </div>
    );
  }

  const roots = todos.filter((t) => !t.parent_id);
  const childrenOf = (id: string) => todos.filter((t) => t.parent_id === id);

  const renderTodo = (todo: ResearchTodo, depth: number) => (
    <div key={todo.id} className="space-y-1.5">
      <div
        className={cn("flex items-center gap-2 text-sm", depth > 0 && "ml-6")}
        style={depth > 1 ? { marginLeft: `${depth * 1.5}rem` } : undefined}
      >
        <StatusIcon status={todo.status} />
        <span
          className={cn(
            "min-w-0 truncate",
            todo.status === "completed" && "text-muted-foreground line-through",
            todo.status === "in_progress" && "text-foreground font-medium",
          )}
        >
          {todo.status === "in_progress" && todo.active_form ? todo.active_form : todo.content}
        </span>
      </div>
      {childrenOf(todo.id).map((child) => renderTodo(child, depth + 1))}
    </div>
  );

  return (
    <div className="space-y-1.5">
      <div className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
        Plan
      </div>
      {roots.map((t) => renderTodo(t, 0))}
    </div>
  );
}

const SUBAGENT_STATUS_STYLES: Record<
  SubagentStatus["status"],
  { label: string; className: string }
> = {
  pending: { label: "Queued", className: "bg-muted text-muted-foreground" },
  running: { label: "Running", className: "bg-primary/15 text-primary" },
  waiting_for_answer: { label: "Waiting", className: "bg-amber-500/15 text-amber-600" },
  completed: { label: "Done", className: "bg-emerald-500/15 text-emerald-600" },
  failed: { label: "Failed", className: "bg-destructive/15 text-destructive" },
  cancelled: { label: "Cancelled", className: "bg-muted text-muted-foreground" },
  retrying: { label: "Retrying", className: "bg-amber-500/15 text-amber-600" },
};

function SubagentList({ subagents }: { subagents: SubagentStatus[] }) {
  const done = subagents.filter((s) => TASK_DONE.has(s.status)).length;
  return (
    <div className="space-y-1.5">
      <div className="text-muted-foreground flex items-center justify-between font-mono text-[10px] tracking-wider uppercase">
        <span>Subagents</span>
        <span className="tabular-nums">
          {done}/{subagents.length} done
        </span>
      </div>
      {subagents.map((s) => {
        const style = SUBAGENT_STATUS_STYLES[s.status] ?? SUBAGENT_STATUS_STYLES.pending;
        const isActive = s.status === "running" || s.status === "retrying";
        return (
          <div key={s.task_id} className="flex items-center gap-2 text-sm">
            {isActive ? (
              <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />
            ) : s.status === "completed" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
            ) : (
              <Bot className="text-muted-foreground h-4 w-4 shrink-0" />
            )}
            <span className="font-medium">{s.subagent_name}</span>
            <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs">
              {s.description}
            </span>
            <Badge className={cn("shrink-0 text-[10px]", style.className)}>{style.label}</Badge>
          </div>
        );
      })}
    </div>
  );
}

function ContextMeter({
  pct,
  current,
  max,
  compactionCount,
}: {
  pct: number;
  current: number;
  max: number;
  compactionCount: number;
}) {
  const percent = Math.min(100, Math.round(pct * 100));
  return (
    <div className="space-y-1.5">
      <div className="text-muted-foreground flex items-center justify-between font-mono text-[10px] tracking-wider uppercase">
        <span className="flex items-center gap-1.5">
          <Gauge className="h-3 w-3" />
          Context
        </span>
        <span className="flex items-center gap-2">
          <span>
            {current.toLocaleString()} / {max.toLocaleString()} · {percent}%
          </span>
          {compactionCount > 0 && (
            <Badge className="bg-primary/15 text-primary text-[10px]">
              compacted ×{compactionCount}
            </Badge>
          )}
        </span>
      </div>
      <Progress value={percent} className="h-1.5" />
    </div>
  );
}
