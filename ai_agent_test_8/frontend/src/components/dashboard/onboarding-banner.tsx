"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles, X } from "lucide-react";

import { isOnboardingCompleted } from "@/components/onboarding/onboarding-state";
import { useAuth } from "@/hooks";
import { ROUTES } from "@/lib/constants";

const DISMISS_KEY = "onboarding.banner_dismissed";

export function OnboardingBanner() {
  const { user } = useAuth();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const dismissed = window.localStorage.getItem(DISMISS_KEY);
    setShow(!dismissed && !isOnboardingCompleted(user));
  }, [user]);

  if (!show) return null;

  return (
    <div className="border-border bg-card flex items-center gap-4 rounded-xl border p-4">
      <div className="bg-muted text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-lg">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-foreground text-sm font-semibold">Finish setting up your workspace</p>
        <p className="text-muted-foreground mt-0.5 text-sm">
          Pick an agent, connect data, and invite your team — under 2 minutes.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <Link
          href={ROUTES.ONBOARDING}
          className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors"
        >
          Continue
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <button
          type="button"
          onClick={() => {
            window.localStorage.setItem(DISMISS_KEY, "1");
            setShow(false);
          }}
          className="text-muted-foreground hover:text-foreground hover:bg-accent inline-flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
