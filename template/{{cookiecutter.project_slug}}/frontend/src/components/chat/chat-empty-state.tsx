{% raw %}"use client";

import { ArrowUpRight, BookOpen, Code2, FileSearch, Sparkles } from "lucide-react";

import { useAuth } from "@/hooks";

const PROMPTS = [
  {
    icon: FileSearch,
    title: "Summarize my docs",
    prompt: "Summarize the key points from my latest indexed documents.",
  },
  {
    icon: BookOpen,
    title: "Explain a concept",
    prompt: "Explain how vector search and RAG work together — keep it under 200 words.",
  },
  {
    icon: Code2,
    title: "Write some code",
    prompt: "Write a Python function that hashes a password with bcrypt and verifies it.",
  },
  {
    icon: Sparkles,
    title: "Brainstorm",
    prompt: "Give me 5 ideas for an onboarding email sequence for a developer tool.",
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
    <div className="mx-auto w-full max-w-2xl px-4 py-12 md:py-16">
      <div className="text-center">
        <div className="bg-muted text-foreground mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl">
          <Sparkles className="h-5 w-5" />
        </div>
        <h2 className="text-foreground font-display text-2xl font-semibold tracking-tight md:text-3xl">
          {firstName ? `How can I help, ${firstName}?` : "How can I help today?"}
        </h2>
        <p className="text-muted-foreground mx-auto mt-2 max-w-md text-sm leading-relaxed">
          Ask anything — get streaming answers with tool calls and citations from your knowledge.
        </p>
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        {PROMPTS.map((p) => (
          <button
            key={p.title}
            type="button"
            onClick={() => onPick(p.prompt)}
            className="group border-border bg-card hover:border-foreground/30 hover:bg-accent flex items-start gap-3 rounded-xl border p-4 text-left transition-colors"
          >
            <span className="bg-muted text-muted-foreground group-hover:text-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors">
              <p.icon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-foreground text-sm font-medium">{p.title}</p>
              <p className="text-muted-foreground mt-0.5 line-clamp-2 text-xs leading-relaxed">
                {p.prompt}
              </p>
            </div>
            <ArrowUpRight className="text-muted-foreground/50 group-hover:text-foreground mt-0.5 h-4 w-4 shrink-0 transition-colors" />
          </button>
        ))}
      </div>

      <div className="text-muted-foreground mt-8 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-xs">
        <kbd className="border-border bg-card rounded px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
        <span>command palette</span>
        <span className="text-border">·</span>
        <kbd className="border-border bg-card rounded px-1.5 py-0.5 font-mono text-[10px]">/</kbd>
        <span>slash commands</span>
        <span className="text-border">·</span>
        <span className="text-muted-foreground/70">Powered by {agentLabel}</span>
      </div>
    </div>
  );
}
{% endraw %}
