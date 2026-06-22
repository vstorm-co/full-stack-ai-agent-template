{% raw %}"use client";

import { useEffect, useRef, useState } from "react";
import { useResearchStore } from "@/stores";
import { useChatModeStore } from "@/stores";
import type { ResearchTodo } from "@/types";
import { Card, Progress } from "@/components/ui";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  CircleDashed,
  Loader2,
  Sparkles,
  Telescope,
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

/**
 * Sticky plan panel rendered above the chat input. Shows the current turn's
 * TODO checklist, subagent statuses, and context meter. Title reads
 * "Deep research" only when that persona is active; otherwise "Plan".
 */
export function ResearchPanel({ turnId }: { turnId: string }) {
  const turn = useResearchStore((s) => s.byTurn[turnId]);
  const deepResearch = useChatModeStore((s) => s.deepResearch);
  const todos = turn?.todos ?? EMPTY_TODOS;

  const todoTotal = todos.length;
  const todoDone = todos.filter((t) => t.status === "completed").length;

  const stopped = turn?.stopped ?? false;
  const anyTodoActive = todos.some((t) => t.status === "in_progress" || t.status === "pending");
  const done = stopped || (todoTotal > 0 && !anyTodoActive);
  const busy = !done;

  const [expanded, setExpanded] = useState(true);
  const wasDone = useRef(false);
  useEffect(() => {
    if (done && !wasDone.current) setExpanded(false);
    else if (!done && wasDone.current) setExpanded(true);
    wasDone.current = done;
  }, [done]);

  if (todoTotal === 0) return null;

  const counter = todoTotal > 0 ? `${todoDone}/${todoTotal} steps` : "Planning…";
  const pct = todoTotal > 0 ? Math.round((todoDone / todoTotal) * 100) : 0;

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
        {todoTotal > 0 && (
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
        <div className="px-4 pb-4">
          <ResearchChecklist todos={todos} />
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

{% endraw %}
