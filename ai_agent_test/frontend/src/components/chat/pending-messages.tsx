"use client";

import { Clock, Paperclip, X } from "lucide-react";

import type { QueuedMessage } from "@/hooks/use-chat";
import { cn } from "@/lib/utils";

interface PendingMessagesProps {
  messages: QueuedMessage[];
  onCancel: (id: string) => void;
}

/**
 * Stack of "pending" entries shown above <ChatInput>.
 *
 * The hook queues a message when the agent is busy or the socket is offline,
 * surfaces it here so the user can see (and cancel) what's waiting, then the
 * drainer auto-sends each entry as soon as the agent goes idle.
 */
export function PendingMessages({ messages, onCancel }: PendingMessagesProps) {
  if (messages.length === 0) return null;

  return (
    <div className="border-foreground/10 bg-card/60 mb-2 rounded-2xl border px-3 py-2 backdrop-blur-sm">
      <div className="text-foreground/55 mb-1.5 flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase">
        <Clock className="h-3 w-3" />
        Queued · sends after current reply
      </div>
      <ul className="space-y-1.5">
        {messages.map((m, i) => (
          <li
            key={m.id}
            className={cn(
              "group flex items-start gap-2 rounded-lg px-2 py-1.5 text-sm",
              "bg-foreground/[0.03] hover:bg-foreground/[0.06] transition-colors",
            )}
          >
            <span className="text-foreground/45 mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center font-mono text-[10px]">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-foreground line-clamp-2 break-words">{m.content}</p>
              {m.files && m.files.length > 0 && (
                <p className="text-foreground/55 mt-0.5 inline-flex items-center gap-1 font-mono text-[10px] tracking-wider uppercase">
                  <Paperclip className="h-3 w-3" />
                  {m.files.length} file{m.files.length === 1 ? "" : "s"}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onCancel(m.id)}
              className="text-foreground/45 hover:bg-foreground/10 hover:text-destructive inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md transition-colors"
              title="Remove from queue"
              aria-label="Remove from queue"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
