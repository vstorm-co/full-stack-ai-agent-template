"use client";

import { ArrowUpRight, BookOpen, Code2, FileSearch, Sparkles } from "lucide-react";

import { useAuth } from "@/hooks";
import { cn } from "@/lib/utils";

const PROMPTS = [
  {
    icon: FileSearch,
    title: "Summarize my docs",
    prompt: "Summarize the key points from my latest indexed documents.",
    accent: "from-brand/30 to-brand/5",
  },
  {
    icon: BookOpen,
    title: "Explain a concept",
    prompt: "Explain how vector search and RAG work together — keep it under 200 words.",
    accent: "from-brand/30 to-brand/5",
  },
  {
    icon: Code2,
    title: "Write some code",
    prompt: "Write a Python function that hashes a password with bcrypt and verifies it.",
    accent: "from-brand/30 to-brand/5",
  },
  {
    icon: Sparkles,
    title: "Brainstorm",
    prompt: "Give me 5 ideas for an onboarding email sequence for a developer tool.",
    accent: "from-brand/30 to-brand/5",
  },
];

interface ChatEmptyStateProps {
  onPick: (prompt: string) => void;
  agentLabel?: string;
}

export function ChatEmptyState({ onPick, agentLabel = "pydantic_ai" }: ChatEmptyStateProps) {
  const { user } = useAuth();
  const firstName = user?.full_name?.split(" ")[0] || user?.email?.split("@")[0];

  return (
    <div className="relative mx-auto w-full max-w-3xl px-4 py-10 text-center md:py-16">
      {/* Brand halo behind the headline */}
      <div
        aria-hidden
        className="pointer-events-none absolute top-12 left-1/2 -z-10 h-[320px] w-[320px] -translate-x-1/2 rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.22), transparent 65%)",
        }}
      />

      <div className="flex flex-col items-center">
        <span className="eyebrow-badge mb-7 inline-flex items-center gap-2">
          <span
            aria-hidden
            className="bg-brand inline-block h-1.5 w-1.5 animate-pulse rounded-full"
            style={{ boxShadow: "0 0 8px var(--color-brand)" }}
          />
          Powered by {agentLabel}
        </span>

        <h2 className="font-display text-foreground [&_em]:font-accent text-4xl leading-[1.05] font-bold tracking-tight md:text-5xl [&_em]:font-normal [&_em]:italic">
          {firstName ? (
            <>
              Ready when you are, <em>{firstName}.</em>
            </>
          ) : (
            <>
              How can I <em>help today?</em>
            </>
          )}
        </h2>
        <p className="text-foreground/65 mt-4 max-w-md text-sm md:text-base">
          Streaming answers, tool calls, citations — try a prompt below or just start typing.
        </p>
      </div>

      <div className="mt-10 grid w-full gap-3 sm:grid-cols-2">
        {PROMPTS.map((p) => (
          <button
            key={p.title}
            type="button"
            onClick={() => onPick(p.prompt)}
            className={cn(
              "group border-foreground/10 bg-card/60 hover:border-brand/40 hover:bg-card relative isolate flex items-start gap-4 overflow-hidden rounded-2xl border p-5 text-left transition-all",
              "hover:shadow-[0_0_40px_-12px_oklch(from_var(--color-brand)_l_c_h/0.45)]",
            )}
          >
            {/* Per-card glow that fades in on hover */}
            <div
              aria-hidden
              className={cn(
                "pointer-events-none absolute -top-12 -right-12 -z-10 h-32 w-32 rounded-full opacity-0 blur-3xl transition-opacity duration-300 group-hover:opacity-100",
                "bg-gradient-to-br",
                p.accent,
              )}
            />

            <span
              aria-hidden
              className="bg-brand/15 text-foreground group-hover:bg-brand group-hover:text-brand-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors"
            >
              <p.icon className="h-4 w-4" />
            </span>

            <div className="min-w-0 flex-1">
              <p className="text-foreground text-sm font-semibold">{p.title}</p>
              <p className="text-foreground/55 mt-1 line-clamp-2 text-xs leading-relaxed">
                {p.prompt}
              </p>
            </div>

            <span
              aria-hidden
              className="bg-foreground/[0.04] text-foreground/45 group-hover:bg-foreground group-hover:text-background mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-all group-hover:rotate-45"
            >
              <ArrowUpRight className="h-3.5 w-3.5" />
            </span>
          </button>
        ))}
      </div>

      <div className="text-foreground/45 mt-10 inline-flex items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
        <span>Tip:</span>
        <kbd className="border-foreground/15 bg-card text-foreground/65 rounded-md border px-1.5 py-0.5 text-[10px]">
          ⌘K
        </kbd>
        <span>for command palette</span>
        <span className="text-foreground/20">·</span>
        <kbd className="border-foreground/15 bg-card text-foreground/65 rounded-md border px-1.5 py-0.5 text-[10px]">
          /
        </kbd>
        <span>for slash commands</span>
      </div>
    </div>
  );
}
