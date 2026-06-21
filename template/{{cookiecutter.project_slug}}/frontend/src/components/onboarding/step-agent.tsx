"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Check } from "lucide-react";

import { Button } from "@/components/ui";
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
                "bg-card relative flex flex-col gap-2 rounded-xl border p-5 text-left transition-colors",
                isSelected
                  ? "border-foreground"
                  : "border-border hover:border-foreground/30",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-foreground text-base font-semibold">{agent.name}</p>
                  <p className="text-muted-foreground text-xs">{agent.tagline}</p>
                </div>
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                    isSelected
                      ? "border-foreground bg-foreground text-background"
                      : "border-border",
                  )}
                >
                  {isSelected && <Check className="h-3 w-3" />}
                </span>
              </div>
              <p className="text-muted-foreground mt-1 text-sm leading-relaxed">
                {agent.description}
              </p>
              {agent.recommended && (
                <span className="bg-muted text-foreground border-border absolute -top-2 right-4 rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
                  Recommended
                </span>
              )}
            </button>
          );
        })}
      </div>

      <Button size="lg" className="mt-8" onClick={handleNext}>
        Continue
        <ArrowRight className="h-4 w-4" />
      </Button>
    </OnboardingShell>
  );
}
