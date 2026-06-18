"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles } from "lucide-react";

import { ROUTES } from "@/lib/constants";

import { OnboardingShell } from "./onboarding-shell";
import { markOnboardingCompleted } from "./onboarding-state";

export function StepDone() {
  const router = useRouter();

  useEffect(() => {
    void markOnboardingCompleted();
  }, []);

  return (
    <OnboardingShell
      step="done"
      title="You're all set."
      description="Your workspace is ready. Try asking your assistant anything — it'll use the data you connected."
      hideSkip
    >
      <div className="border-foreground/10 bg-brand/[0.08] flex items-center gap-4 rounded-2xl border p-6">
        <div className="bg-brand text-brand-foreground flex h-12 w-12 items-center justify-center rounded-full">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <p className="text-foreground font-display text-base font-semibold">
            Open your first chat
          </p>
          <p className="text-foreground/65 mt-0.5 text-sm">
            We&apos;ll prefill a starter prompt so you see streaming + tools in action.
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => router.push(`${ROUTES.CHAT}?onboarding=1`)}
        className="bg-foreground text-background hover:bg-foreground/90 mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-full px-6 text-sm font-medium transition-colors"
      >
        Open chat
        <ArrowRight className="h-4 w-4" />
      </button>

      <button
        type="button"
        onClick={() => router.push(ROUTES.DASHBOARD)}
        className="text-foreground/55 hover:text-foreground ml-3 text-sm font-medium"
      >
        Go to dashboard
      </button>
    </OnboardingShell>
  );
}
