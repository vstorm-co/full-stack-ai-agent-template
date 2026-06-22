"use client";

import { useEffect, useRef, useState } from "react";
import { useResearchStore } from "@/stores";
import { useChatModeStore } from "@/stores";
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
  Loader2,
  Sparkles,
  Telescope,
  XCircle,
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
 * Sticky plan panel rendered above the chat input. Shows the current turn's
 * TODO checklist, subagent statuses, and context meter. Title reads
 * "Deep research" only when that persona is active; otherwise "Plan".
 */
export function ResearchPanel({ turnId }: { turnId: string }) {
  const turn = useResearchStore((s) => s.byTurn[turnId]);
  const deepResearch = useChatModeStore((s) => s.deepResearch);
  const todos = turn?.todos ?? EMPTY_TODOS;
  const subagents = turn?.subagents ?? EMPTY_SUBAGENTS;

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
  const pct = counterTotal > 0 ? Math.round((counterDone / counterTotal) * 100) : 0;

  const TitleIcon = deepResearch ? Telescope : Sparkles;
  const title = deepResearch ? "Deep research" : "Plan";

  return (
    <Card className="overflow-hidden py-0">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
        className="hover:bg-foreground/[0.03] flex w-full items-center gap-2 px-4 py-2.5 text-left transition-colors"
      >
        <TitleIcon
          className={cn(
            "h-3.5 w-3.5 shrink-0 transition-colors",
            busy ? "text-primary" : "text-emerald-500",
          )}
        />
        <span className="text-sm font-semibold">{title}</span>
        {busy ? (
          <Loader2 className="text-primary h-3.5 w-3.5 shrink-0 animate-spin" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
        )}
        <span className="text-muted-foreground shrink-0 font-mono text-xs tabular-nums">
          {counter}
        </span>
        {counterTotal > 0 && (
          <Progress value={pct} className="mx-1 h-1.5 min-w-0 flex-1" />
        )}
        <span className="flex-1" />
        {expanded ? (
          <ChevronUp className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
        ) : (
          <ChevronDown className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="space-y-3 px-4 pb-4">
          <ResearchChecklist todos={todos} />
          {subagents.length > 0 && <SubagentList subagents={subagents} />}
        </div>
      )}
    </Card>
  );
}

const TODO_STATUS_BORDER: Record<ResearchTodo["status"], string> = {
  pending: "border-border/50",
  in_progress: "border-primary",
  completed: "border-emerald-500/60",
  blocked: "border-amber-500",
};

function StatusIcon({ status }: { status: ResearchTodo["status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />;
    case "in_progress":
      return <Loader2 className="text-primary h-3.5 w-3.5 shrink-0 animate-spin" />;
    case "blocked":
      return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" />;
    default:
      return <Circle className="text-muted-foreground/40 h-3.5 w-3.5 shrink-0" />;
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

  const renderTodo = (todo: ResearchTodo, depth: number, index: number) => (
    <div
      key={todo.id}
      style={{ animation: `todo-enter 0.22s ease-out ${index * 40}ms both` }}
    >
      <div
        className={cn(
          "flex items-start gap-2 rounded-md border-l-2 px-2 py-1 text-sm transition-colors duration-300",
          TODO_STATUS_BORDER[todo.status],
          todo.status === "in_progress" && "bg-primary/[0.05]",
          depth > 0 && "ml-5",
        )}
        style={depth > 1 ? { marginLeft: `${depth * 1.25}rem` } : undefined}
      >
        <span className="mt-0.5 shrink-0">
          <StatusIcon status={todo.status} />
        </span>
        <span
          className={cn(
            "min-w-0 leading-snug",
            todo.status === "completed" && "text-muted-foreground line-through",
            todo.status === "in_progress" && "text-foreground font-medium",
            todo.status === "blocked" && "text-amber-700 dark:text-amber-400",
            todo.status === "pending" && "text-muted-foreground",
          )}
        >
          {todo.status === "in_progress" && todo.active_form ? todo.active_form : todo.content}
        </span>
      </div>
      {childrenOf(todo.id).map((child, ci) => renderTodo(child, depth + 1, index * 10 + ci))}
    </div>
  );

  const completedCount = todos.filter((t) => t.status === "completed").length;
  const totalCount = todos.length;

  return (
    <div className="space-y-1">
      <div className="text-muted-foreground mb-2 flex items-center justify-between font-mono text-[10px] tracking-wider uppercase">
        <span>Plan</span>
        <span className="tabular-nums">
          {completedCount}/{totalCount}
        </span>
      </div>
      {roots.map((t, i) => renderTodo(t, 0, i))}
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
      {subagents.map((s, i) => {
        const style = SUBAGENT_STATUS_STYLES[s.status] ?? SUBAGENT_STATUS_STYLES.pending;
        const isRunning = s.status === "running" || s.status === "retrying";
        const isFailed = s.status === "failed";
        return (
          <div
            key={s.task_id}
            className={cn(
              "rounded-md border px-3 py-2 transition-colors duration-300",
              isRunning && "border-primary/20 bg-primary/[0.03]",
              isFailed && "border-destructive/20 bg-destructive/[0.03]",
              !isRunning && !isFailed && "border-transparent",
            )}
            style={{ animation: `todo-enter 0.22s ease-out ${i * 50}ms both` }}
          >
            <div className="flex items-center gap-2 text-sm">
              {isRunning ? (
                <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />
              ) : s.status === "completed" ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
              ) : isFailed ? (
                <XCircle className="text-destructive h-4 w-4 shrink-0" />
              ) : (
                <Bot className="text-muted-foreground h-4 w-4 shrink-0" />
              )}
              <span className="font-medium">{s.subagent_name}</span>
              <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs">
                {s.description}
              </span>
              <Badge className={cn("shrink-0 text-[10px]", style.className)}>{style.label}</Badge>
            </div>
            {isFailed && s.error && (
              <p className="text-destructive mt-1 pl-6 text-xs opacity-80">{s.error}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
