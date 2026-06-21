"use client";

import { Bot, FileText, Sparkles, User } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const SCRIPT = [
  {
    role: "user" as const,
    text: "Summarize this quarter's customer onboarding feedback.",
  },
  {
    role: "tool" as const,
    text: "rag.search · 4 documents · 12 chunks",
  },
  {
    role: "agent" as const,
    text: "Across 137 onboarding sessions, top three friction points are: (1) database setup confusion, (2) Stripe webhook configuration, (3) missing example projects. 58% of churned trials cited #1.",
  },
];

/** Scripted chat demo. All messages are always in the DOM at full length, so
 *  the card is a fixed height and never resizes — we only fade/slide each
 *  message in sequentially (opacity + transform don't affect layout), so the
 *  page never jumps as the loop plays. */
export function HeroDemo() {
  // SSR + no-JS render everything visible; the loop starts after mount.
  const [revealed, setRevealed] = useState(SCRIPT.length);

  useEffect(() => {
    const id = setInterval(() => {
      setRevealed((r) => (r >= SCRIPT.length ? 1 : r + 1));
    }, 1600);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="border-foreground/15 bg-card mx-auto w-full max-w-5xl overflow-hidden rounded-2xl border shadow-2xl">
      <div className="border-foreground/10 flex items-center gap-2 border-b px-4 py-3">
        <div className="flex gap-1.5">
          <span className="bg-foreground/20 h-2.5 w-2.5 rounded-full" />
          <span className="bg-foreground/20 h-2.5 w-2.5 rounded-full" />
          <span className="bg-foreground/20 h-2.5 w-2.5 rounded-full" />
        </div>
        <div className="text-foreground/50 ml-3 font-mono text-xs">app.example.com / chat</div>
      </div>

      <div className="space-y-4 p-5 md:p-8">
        {SCRIPT.map((msg, i) => {
          const shown = i < revealed;
          const reveal = cn(
            "transition-[opacity,transform] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]",
            shown ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
          );
          if (msg.role === "user") {
            return (
              <div key={i} className={cn("flex justify-end", reveal)}>
                <div className="bg-foreground text-background flex max-w-[80%] items-start gap-3 rounded-2xl rounded-tr-sm px-5 py-3.5 text-base">
                  <span className="leading-relaxed">{msg.text}</span>
                  <User className="mt-1 h-4 w-4 shrink-0 opacity-60" />
                </div>
              </div>
            );
          }
          if (msg.role === "tool") {
            return (
              <div key={i} className={cn("flex", reveal)}>
                <div className="border-brand/40 bg-brand/10 text-foreground/80 flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs">
                  <FileText className="h-3 w-3" />
                  <span>{msg.text}</span>
                </div>
              </div>
            );
          }
          return (
            <div key={i} className={cn("flex", reveal)}>
              <div className="bg-card border-foreground/10 max-w-[85%] rounded-2xl rounded-tl-sm border p-5">
                <div className="text-foreground/55 mb-2.5 flex items-center gap-2 text-xs">
                  <Bot className="h-3.5 w-3.5" />
                  <span className="eyebrow">Assistant</span>
                  {shown && i === revealed - 1 && (
                    <span className="bg-brand ml-auto inline-block h-2 w-2 animate-pulse rounded-full" />
                  )}
                </div>
                <p className="text-foreground text-base leading-relaxed">{msg.text}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-foreground/10 bg-background flex items-center gap-3 border-t px-5 py-4">
        <Sparkles className="text-foreground/40 h-4 w-4" />
        <span className="text-foreground/40 flex-1 text-sm">Ask anything…</span>
        <kbd className="border-foreground/15 text-foreground/50 inline-flex items-center gap-1 rounded border px-2 py-1 font-mono text-xs">
          ⌘ ↵
        </kbd>
      </div>
    </div>
  );
}
