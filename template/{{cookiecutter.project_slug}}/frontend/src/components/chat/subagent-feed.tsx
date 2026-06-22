"use client";

import { Bot, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useResearchStore } from "@/stores";
import type { SubagentStatus } from "@/types";
import { cn } from "@/lib/utils";

const EMPTY: SubagentStatus[] = [];

function SubagentCard({
  subagent,
  selected,
  messageCount,
  onClick,
}: {
  subagent: SubagentStatus;
  selected: boolean;
  messageCount: number;
  onClick: () => void;
}) {
  const isRunning = subagent.status === "running" || subagent.status === "retrying";
  const isDone = subagent.status === "completed";
  const isFailed = subagent.status === "failed";
  const isWaiting = subagent.status === "waiting_for_answer";

  const statusText = isRunning
    ? subagent.description
    : isWaiting
      ? "Waiting for answer…"
      : isDone
        ? `${messageCount} message${messageCount !== 1 ? "s" : ""}`
        : isFailed
          ? subagent.error ?? "Failed"
          : subagent.description;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-xl border px-3.5 py-2 text-left text-sm transition-colors",
        selected
          ? "border-foreground/20 bg-foreground/[0.06]"
          : "border-foreground/8 bg-foreground/[0.02] hover:border-foreground/15 hover:bg-foreground/[0.04]",
      )}
    >
      {isRunning || subagent.status === "retrying" ? (
        <Loader2 className="text-primary h-3.5 w-3.5 shrink-0 animate-spin" />
      ) : isDone ? (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
      ) : isFailed ? (
        <XCircle className="text-destructive h-3.5 w-3.5 shrink-0" />
      ) : (
        <Bot className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
      )}

      <span className="text-foreground/80 shrink-0 text-xs font-medium">
        {subagent.subagent_name}
      </span>
      <span className="text-foreground/40 mx-0.5 shrink-0 text-xs">·</span>
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-xs",
          isRunning || subagent.status === "pending"
            ? "text-muted-foreground"
            : isDone
              ? "text-muted-foreground"
              : isFailed
                ? "text-destructive/70"
                : isWaiting
                  ? "text-amber-500"
                  : "text-muted-foreground",
        )}
      >
        {statusText}
      </span>

      {isRunning && (
        <span className="text-primary shrink-0 font-mono text-[10px] tracking-wider">LIVE</span>
      )}
      {isDone && messageCount > 0 && (
        <span className="text-muted-foreground shrink-0 text-[10px]">→</span>
      )}
    </button>
  );
}

export function SubagentFeed({ turnId }: { turnId: string }) {
  const subagents = useResearchStore((s) => s.byTurn[turnId]?.subagents ?? EMPTY);
  const selectedId = useResearchStore((s) => s.selectedSubagentId);
  const setSelected = useResearchStore((s) => s.setSelectedSubagent);
  const messagesByTask = useResearchStore((s) => s.byTurn[turnId]?.subagentMessages);

  if (subagents.length === 0) return null;

  return (
    <div className="mt-4 space-y-1.5 px-2 sm:px-4">
      {subagents.map((s) => (
        <SubagentCard
          key={s.task_id}
          subagent={s}
          selected={selectedId === s.task_id}
          messageCount={messagesByTask?.[s.task_id]?.length ?? 0}
          onClick={() => setSelected(selectedId === s.task_id ? null : s.task_id)}
        />
      ))}
    </div>
  );
}
