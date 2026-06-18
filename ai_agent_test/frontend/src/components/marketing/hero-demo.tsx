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

export function HeroDemo() {
  const [step, setStep] = useState(0);
  const [typed, setTyped] = useState("");

  useEffect(() => {
    const current = SCRIPT[step];
    if (!current) return;

    if (typed.length < current.text.length) {
      // Slower for user msg (looks deliberate), faster for tool/agent
      const charDelay = current.role === "agent" ? 8 : current.role === "tool" ? 6 : 14;
      const timer = setTimeout(() => setTyped(current.text.slice(0, typed.length + 1)), charDelay);
      return () => clearTimeout(timer);
    }

    // Pause depends on role: short after tool, longer after agent (let user read).
    const pauseMs = current.role === "agent" ? 1800 : current.role === "tool" ? 700 : 1100;
    const advance = setTimeout(() => {
      if (step < SCRIPT.length - 1) {
        setStep((s) => s + 1);
        setTyped("");
      } else {
        setStep(0);
        setTyped("");
      }
    }, pauseMs);
    return () => clearTimeout(advance);
  }, [step, typed]);

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
        {SCRIPT.slice(0, step + 1).map((msg, i) => {
          const isLast = i === step;
          const text = isLast ? typed : msg.text;
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div className="bg-foreground text-background flex max-w-[80%] items-start gap-3 rounded-2xl rounded-tr-sm px-5 py-3.5 text-base">
                  <span className="leading-relaxed">{text}</span>
                  <User className="mt-1 h-4 w-4 shrink-0 opacity-60" />
                </div>
              </div>
            );
          }
          if (msg.role === "tool") {
            return (
              <div key={i} className="flex">
                <div className="border-brand/40 bg-brand/10 text-foreground/80 flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-xs">
                  <FileText className="h-3 w-3" />
                  <span>{text}</span>
                </div>
              </div>
            );
          }
          return (
            <div key={i} className="flex">
              <div className="bg-card border-foreground/10 max-w-[85%] rounded-2xl rounded-tl-sm border p-5">
                <div className="text-foreground/55 mb-2.5 flex items-center gap-2 text-xs">
                  <Bot className="h-3.5 w-3.5" />
                  <span className="eyebrow">Assistant</span>
                  {isLast && (
                    <span className="bg-brand ml-auto inline-block h-2 w-2 animate-pulse rounded-full" />
                  )}
                </div>
                <p className="text-foreground text-base leading-relaxed">{text}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="border-foreground/10 bg-background flex items-center gap-3 border-t px-5 py-4">
        <Sparkles className="text-foreground/40 h-4 w-4" />
        <span className="text-foreground/40 flex-1 text-sm">Ask anything…</span>
        <kbd
          className={cn(
            "border-foreground/15 text-foreground/50 inline-flex items-center gap-1 rounded border px-2 py-1 font-mono text-xs",
          )}
        >
          ⌘ ↵
        </kbd>
      </div>
    </div>
  );
}
