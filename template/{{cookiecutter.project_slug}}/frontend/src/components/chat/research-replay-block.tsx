{% raw %}"use client";

import { useEffect, useState } from "react";
import { Bot, CheckCircle2, Circle, Loader2, Telescope } from "lucide-react";
import type { ResearchReplay, ResearchTodoStatus } from "@/types";
import { Card, Progress } from "@/components/ui";
import { cn } from "@/lib/utils";

export const STEP_REVEAL_MS = 460;

function StatusIcon({ status }: { status: ResearchTodoStatus }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />;
    case "in_progress":
      return <Loader2 className="text-primary h-3.5 w-3.5 shrink-0 animate-spin" />;
    default:
      return <Circle className="text-muted-foreground/40 h-3.5 w-3.5 shrink-0" />;
  }
}

export function ResearchReplayBlock({
  research,
  animate = true,
  detailed = false,
}: {
  research: ResearchReplay;
  /** When false, render the finished state immediately (used by the static computer panel). */
  animate?: boolean;
  /** When true, expand each subagent card with its returned findings (computer deep-dive). */
  detailed?: boolean;
}) {
  const { todos, subagents } = research;
  const total = todos.length;
  const [completed, setCompleted] = useState(animate ? 0 : total);

  useEffect(() => {
    if (total === 0) return;
    if (!animate) {
      setCompleted(total);
      return;
    }
    setCompleted(0);
    let n = 0;
    const id = setInterval(() => {
      n += 1;
      setCompleted(n);
      if (n >= total) clearInterval(id);
    }, STEP_REVEAL_MS);
    return () => clearInterval(id);
  }, [total, animate]);

  const done = total > 0 && completed >= total;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  const statusFor = (i: number): ResearchTodoStatus =>
    i < completed ? "completed" : i === completed ? "in_progress" : "pending";

  return (
    <Card className="w-full overflow-hidden py-0">
      <div className="flex items-center gap-2 px-4 py-2.5">
        <Telescope
          className={cn("h-3.5 w-3.5 shrink-0", done ? "text-emerald-500" : "text-primary")}
        />
        <span className="text-sm font-semibold">Deep research</span>
        {done ? (
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
        ) : (
          <Loader2 className="text-primary h-3.5 w-3.5 shrink-0 animate-spin" />
        )}
        {total > 0 && (
          <span className="text-muted-foreground shrink-0 font-mono text-xs tabular-nums">
            {completed}/{total} steps
          </span>
        )}
        {total > 0 && <Progress value={pct} className="mx-1 h-1.5 min-w-0 flex-1" />}
      </div>

      <div className="space-y-1 px-4 pb-4">
        {todos.map((todo, i) => {
          const status = statusFor(i);
          return (
            <div
              key={todo.id}
              style={{ animation: `todo-enter 0.22s ease-out ${i * 40}ms both` }}
              className={cn(
                "flex items-start gap-2 rounded-md border-l-2 px-2 py-1 text-sm transition-colors duration-300",
                status === "completed"
                  ? "border-emerald-500/60"
                  : status === "in_progress"
                    ? "border-primary bg-primary/[0.05]"
                    : "border-border/50",
                todo.parent_id !== null && "ml-5",
              )}
            >
              <span className="mt-0.5 shrink-0">
                <StatusIcon status={status} />
              </span>
              <span
                className={cn(
                  "min-w-0 leading-snug",
                  status === "completed" && "text-muted-foreground line-through",
                  status === "in_progress" && "text-foreground font-medium",
                  status === "pending" && "text-muted-foreground",
                )}
              >
                {status === "in_progress" && todo.active_form ? todo.active_form : todo.content}
              </span>
            </div>
          );
        })}

        {subagents.length > 0 && (
          <div className="mt-3 space-y-1.5">
            <div className="text-muted-foreground mb-1 font-mono text-[10px] tracking-wider uppercase">
              Subagents
            </div>
            {subagents.map((s, i) => (
              <div
                key={s.task_id}
                style={{ animationDelay: `${i * 60}ms` }}
                className="step-card-in border-foreground/8 bg-foreground/[0.02] rounded-xl border px-3.5 py-2 text-sm"
              >
                <div className="flex items-center gap-2.5">
                  <Bot className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                  <span className="text-foreground/80 shrink-0 text-xs font-medium">
                    {s.subagent_name}
                  </span>
                  <span className="text-foreground/40 mx-0.5 shrink-0 text-xs">·</span>
                  <span
                    className={cn(
                      "text-muted-foreground min-w-0 flex-1 text-xs",
                      detailed ? "" : "truncate",
                    )}
                  >
                    {s.description}
                  </span>
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                </div>
                {detailed && s.result && (
                  <p className="text-foreground/60 border-border/40 mt-1.5 border-t pt-1.5 text-xs leading-relaxed whitespace-pre-wrap">
                    {s.result}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
{% endraw %}
