"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getResumeStep } from "@/components/onboarding/onboarding-state";

/**
 * Resume-aware entry point: send the user to the furthest step they reached
 * (falls back to the first step). Runs client-side because the furthest step
 * lives in localStorage.
 */
export default function OnboardingIndex() {
  const router = useRouter();

  useEffect(() => {
    router.replace(`/onboarding/${getResumeStep()}`);
  }, [router]);

  return null;
}
