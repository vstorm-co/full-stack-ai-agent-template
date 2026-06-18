"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check } from "lucide-react";

import { cn } from "@/lib/utils";

import { OnboardingShell } from "./onboarding-shell";

interface AgentOption {
  id: string;
  name: string;
  tagline: string;
  description: string;
  recommended?: boolean;
}

const AGENTS: AgentOption[] = [
  {
    id: "pydantic_ai",
    name: "PydanticAI",
    tagline: "Type-safe, fast, opinionated",
    description: "Best default — typed tools, structured outputs, Logfire telemetry.",
    recommended: true,
  },
  {
    id: "langgraph",
    name: "LangGraph",
    tagline: "Stateful graphs, complex flows",
    description: "Multi-step agents with branching logic and persistent state.",
  },
  {
    id: "deepagents",
    name: "DeepAgents",
    tagline: "Long-horizon planning",
    description: "Built for autonomous tasks that span many tool calls.",
  },
  {
    id: "crewai",
    name: "CrewAI",
    tagline: "Multi-agent collaboration",
    description: "Coordinated teams of specialized agents.",
  },
];

export function StepAgent() {
  const router = useRouter();
  const [selected, setSelected] = useState<string>(
    () => AGENTS.find((a) => a.recommended)?.id ?? AGENTS[0]!.id,
  );

  const handleNext = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("onboarding.agent", selected);
    }
    router.push("/onboarding/data");
  };

  return (
    <OnboardingShell
      step="agent"
      title="Pick your agent framework"
      description="Each comes wired with streaming, tool calls, and observability. You can switch later."
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {AGENTS.map((agent) => {
          const isSelected = selected === agent.id;
          return (
            <button
              key={agent.id}
              type="button"
              onClick={() => setSelected(agent.id)}
              className={cn(
                "lift relative flex flex-col gap-2 rounded-2xl border p-5 text-left transition-colors",
                isSelected
                  ? "border-brand bg-brand/[0.06]"
                  : "border-foreground/10 bg-card hover:border-foreground/30",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-foreground font-display text-base font-semibold">
                    {agent.name}
                  </p>
                  <p className="text-foreground/55 text-xs">{agent.tagline}</p>
                </div>
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                    isSelected
                      ? "border-brand bg-brand text-brand-foreground"
                      : "border-foreground/25",
                  )}
                >
                  {isSelected && <Check className="h-3 w-3" />}
                </span>
              </div>
              <p className="text-foreground/70 mt-1 text-sm leading-relaxed">{agent.description}</p>
              {agent.recommended && (
                <span className="bg-brand text-brand-foreground absolute -top-2 right-4 rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase">
                  Recommended
                </span>
              )}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={handleNext}
        className="bg-foreground text-background hover:bg-foreground/90 mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-full px-6 text-sm font-medium transition-colors"
      >
        Continue
        <ArrowRight className="h-4 w-4" />
      </button>
    </OnboardingShell>
  );
}
