"use client";

import { useEffect } from "react";
import { Bot, CheckCircle2, Loader2, MessageSquare, X, XCircle } from "lucide-react";
import { useResearchStore } from "@/stores";
import type { SubagentMessage, SubagentMessageType } from "@/types";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  pending: { label: "Queued", color: "text-muted-foreground" },
  running: { label: "Running", color: "text-primary" },
  waiting_for_answer: { label: "Waiting", color: "text-amber-500" },
  completed: { label: "Done", color: "text-emerald-500" },
  failed: { label: "Failed", color: "text-destructive" },
  cancelled: { label: "Cancelled", color: "text-muted-foreground" },
  retrying: { label: "Retrying", color: "text-amber-500" },
};

const EMPTY_MESSAGES: SubagentMessage[] = [];

const MSG_STYLES: Record<SubagentMessageType, { label: string; color: string; bg: string }> = {
  info: { label: "Info", color: "text-foreground/50", bg: "bg-foreground/[0.04]" },
  steering: { label: "Steering", color: "text-primary", bg: "bg-primary/8" },
  question: { label: "Question", color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/8" },
  result: { label: "Result", color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/8" },
  error: { label: "Error", color: "text-destructive", bg: "bg-destructive/8" },
};

function MessageRow({ msg }: { msg: SubagentMessage }) {
  const style = MSG_STYLES[msg.type];
  const time = new Date(msg.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className={cn("rounded-lg p-3", style.bg)}>
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className={cn("text-[10px] font-semibold tracking-wider uppercase", style.color)}>
          {style.label}
        </span>
        <span className="text-foreground/35 font-mono text-[10px]">{time}</span>
      </div>
      <p className="text-foreground/80 text-xs leading-relaxed whitespace-pre-wrap break-words">
        {msg.text}
      </p>
    </div>
  );
}

export function SubagentPanel() {
  const selectedId = useResearchStore((s) => s.selectedSubagentId);
  const setSelected = useResearchStore((s) => s.setSelectedSubagent);
  const currentTurnId = useResearchStore((s) => s.currentTurnId);

  const subagent = useResearchStore((s) => {
    if (!s.selectedSubagentId || !s.currentTurnId) return null;
    return s.byTurn[s.currentTurnId]?.subagents.find(
      (a) => a.task_id === s.selectedSubagentId,
    ) ?? null;
  });

  const messages =
    useResearchStore((s) => {
      if (!s.selectedSubagentId || !s.currentTurnId) return null;
      return s.byTurn[s.currentTurnId]?.subagentMessages[s.selectedSubagentId] ?? null;
    }) ?? EMPTY_MESSAGES;

  useEffect(() => {
    if (!selectedId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, setSelected]);

  // Close when the turn changes (new conversation started)
  useEffect(() => {
    setSelected(null);
  }, [currentTurnId, setSelected]);

  if (!selectedId || !subagent) return null;

  const statusStyle = STATUS_STYLES[subagent.status] ?? { label: subagent.status, color: "text-muted-foreground" };
  const isRunning = subagent.status === "running" || subagent.status === "retrying";
  const isDone = subagent.status === "completed";
  const isFailed = subagent.status === "failed";

  return (
    <div className="bg-background border-border fixed top-0 right-0 z-50 flex h-full w-[400px] flex-col border-l shadow-xl">
      {/* Header */}
      <div className="border-foreground/8 flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          {isRunning ? (
            <Loader2 className="text-primary h-4 w-4 shrink-0 animate-spin" />
          ) : isDone ? (
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
          ) : isFailed ? (
            <XCircle className="text-destructive h-4 w-4 shrink-0" />
          ) : (
            <Bot className="text-muted-foreground h-4 w-4 shrink-0" />
          )}
          <div className="min-w-0">
            <p className="text-foreground truncate text-sm font-semibold">
              {subagent.subagent_name}
            </p>
            <p className={cn("text-[11px] font-medium", statusStyle.color)}>
              {statusStyle.label}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setSelected(null)}
          aria-label="Close subagent panel"
          className="text-foreground/50 hover:text-foreground hover:bg-foreground/8 mt-0.5 shrink-0 rounded-md p-1 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Description */}
      <div className="border-foreground/8 border-b px-4 py-2.5">
        <p className="text-foreground/60 text-xs leading-relaxed">{subagent.description}</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          isRunning ? (
            <div className="text-muted-foreground flex flex-col items-center gap-2 py-10 text-center">
              <Loader2 className="text-primary h-8 w-8 animate-spin opacity-60" />
              <p className="text-sm font-medium">Subagent is working…</p>
              <p className="text-xs opacity-60">
                Messages will appear when the task progresses
              </p>
            </div>
          ) : (
            <div className="text-muted-foreground flex flex-col items-center gap-2 py-10 text-center">
              <MessageSquare className="h-8 w-8 opacity-30" />
              <p className="text-sm">No messages captured</p>
            </div>
          )
        ) : (
          <div className="space-y-2">
            {messages.map((msg, i) => (
              <MessageRow key={`${msg.task_id}-${i}`} msg={msg} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
