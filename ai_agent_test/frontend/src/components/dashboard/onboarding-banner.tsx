"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles, X } from "lucide-react";

import { isOnboardingCompleted } from "@/components/onboarding/onboarding-state";
import { useAuth } from "@/hooks";

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
    <div className="border-brand/30 bg-brand/[0.08] flex items-start gap-4 rounded-2xl border p-5">
      <div className="bg-brand text-brand-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="flex-1">
        <p className="text-foreground font-display text-base font-semibold">
          Finish setting up your workspace
        </p>
        <p className="text-foreground/65 mt-0.5 text-sm">
          Pick an agent, connect data, and invite your team — under 2 minutes.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Link
          href="/onboarding/welcome"
          className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors"
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
          className="text-foreground/45 hover:text-foreground hover:bg-foreground/5 inline-flex h-9 w-9 items-center justify-center rounded-full transition-colors"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
