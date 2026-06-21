"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";

import { Progress } from "@/components/ui";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

import {
  ONBOARDING_STEPS,
  type OnboardingStep,
  markStepReached,
  prevStep,
  stepIndex,
} from "./onboarding-state";

interface OnboardingShellProps {
  step: OnboardingStep;
  title: string;
  description?: string;
  children: React.ReactNode;
  /** Hide skip link, e.g. on `done`. */
  hideSkip?: boolean;
}

const STEP_LABELS: Record<OnboardingStep, string> = {
  welcome: "Welcome",
  agent: "Pick agent",
  data: "Connect data",
  team: "Invite team",
  done: "Done",
};

export function OnboardingShell({
  step,
  title,
  description,
  children,
  hideSkip,
}: OnboardingShellProps) {
  const router = useRouter();
  const idx = stepIndex(step);
  const total = ONBOARDING_STEPS.length;
  // Last step is 1-indexed `idx + 1`; fill the bar proportionally.
  const progressValue = Math.round(((idx + 1) / total) * 100);

  // Persist the furthest step reached so `/onboarding` can resume here later.
  useEffect(() => {
    markStepReached(step);
  }, [step]);

  return (
    <div className="bg-background text-foreground min-h-screen">
      <header className="border-border bg-background sticky top-0 z-10 border-b">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link
            href={ROUTES.HOME}
            className="text-foreground inline-flex items-center gap-2 text-base font-semibold tracking-tight"
          >
            <span aria-hidden className="bg-brand inline-block h-2.5 w-2.5 rounded-full" />
            {APP_NAME}
          </Link>
          {!hideSkip && (
            <Link
              href={ROUTES.DASHBOARD}
              className="text-muted-foreground hover:text-foreground text-xs font-medium tracking-wide uppercase"
            >
              Skip for now →
            </Link>
          )}
        </div>

        <div className="mx-auto max-w-3xl space-y-3 px-6 pb-4">
          <Progress
            value={progressValue}
            className="h-1"
            aria-label={`Onboarding progress: step ${idx + 1} of ${total}`}
          />
          <ol className="flex items-center gap-1.5 sm:gap-3">
            {ONBOARDING_STEPS.map((s, i) => {
              const done = i < idx;
              const active = i === idx;
              return (
                <li key={s} className="flex flex-1 items-center gap-2">
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold transition-colors",
                      (done || active) && "bg-foreground text-background",
                      !done && !active && "bg-muted text-muted-foreground",
                    )}
                  >
                    {done ? <Check className="h-3 w-3" /> : i + 1}
                  </div>
                  <span
                    className={cn(
                      "hidden text-[11px] font-medium tracking-wide uppercase transition-colors sm:inline",
                      active || done ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {STEP_LABELS[s]}
                  </span>
                  {i < total - 1 && (
                    <span
                      className={cn(
                        "h-px flex-1 transition-colors",
                        i < idx ? "bg-foreground" : "bg-border",
                      )}
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12 md:py-20">
        <div className="space-y-3">
          <p className="text-muted-foreground text-[11px] font-medium tracking-wide uppercase">
            Step {idx + 1} of {total}
          </p>
          <h1 className="text-display-lg text-foreground">{title}</h1>
          {description && (
            <p className="text-muted-foreground max-w-xl text-base leading-relaxed">{description}</p>
          )}
        </div>

        <div className="mt-10">{children}</div>

        {prevStep(step) && (
          <button
            type="button"
            onClick={() => router.push(`/onboarding/${prevStep(step)}`)}
            className="text-muted-foreground hover:text-foreground mt-10 inline-flex items-center gap-2 text-sm font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
        )}
      </main>
    </div>
  );
}
