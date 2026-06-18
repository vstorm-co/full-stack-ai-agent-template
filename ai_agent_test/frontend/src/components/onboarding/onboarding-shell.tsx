"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";

import { APP_NAME, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

import { ONBOARDING_STEPS, type OnboardingStep, prevStep, stepIndex } from "./onboarding-state";

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

  return (
    <div className="bg-background text-foreground min-h-screen">
      <header className="border-foreground/10 sticky top-0 z-10 border-b backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link
            href={ROUTES.HOME}
            className="font-display text-foreground inline-flex items-center gap-2 text-base font-bold tracking-tight"
          >
            <span aria-hidden className="bg-brand inline-block h-2.5 w-2.5 rounded-full" />
            {APP_NAME}
          </Link>
          {!hideSkip && (
            <Link
              href={ROUTES.DASHBOARD}
              className="text-foreground/55 hover:text-foreground font-mono text-xs tracking-wider uppercase"
            >
              Skip for now →
            </Link>
          )}
        </div>

        {/* Step indicator */}
        <div className="mx-auto max-w-3xl px-6 pb-4">
          <ol className="flex items-center gap-1.5 sm:gap-3">
            {ONBOARDING_STEPS.map((s, i) => {
              const done = i < idx;
              const active = i === idx;
              return (
                <li key={s} className="flex flex-1 items-center gap-2">
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-semibold transition-colors",
                      done && "bg-foreground text-background",
                      active && "bg-brand text-brand-foreground",
                      !done && !active && "bg-foreground/8 text-foreground/55",
                    )}
                  >
                    {done ? <Check className="h-3 w-3" /> : i + 1}
                  </div>
                  <span
                    className={cn(
                      "hidden font-mono text-[11px] tracking-wider uppercase transition-colors sm:inline",
                      active || done ? "text-foreground" : "text-foreground/45",
                    )}
                  >
                    {STEP_LABELS[s]}
                  </span>
                  {i < total - 1 && (
                    <span
                      className={cn(
                        "h-px flex-1 transition-colors",
                        i < idx ? "bg-foreground" : "bg-foreground/15",
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
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Step {idx + 1} of {total}
          </p>
          <h1 className="text-display-lg text-foreground">{title}</h1>
          {description && (
            <p className="text-foreground/65 max-w-xl text-base leading-relaxed">{description}</p>
          )}
        </div>

        <div className="mt-10">{children}</div>

        {prevStep(step) && (
          <button
            type="button"
            onClick={() => router.push(`/onboarding/${prevStep(step)}`)}
            className="text-foreground/55 hover:text-foreground mt-10 inline-flex items-center gap-2 text-sm font-medium"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
        )}
      </main>
    </div>
  );
}
