import { apiClient } from "@/lib/api-client";
import type { User } from "@/types";

const STORAGE_KEY = "onboarding.completed_at";

export const ONBOARDING_STEPS = ["welcome", "agent", "data", "team", "done"] as const;
export type OnboardingStep = (typeof ONBOARDING_STEPS)[number];

/**
 * Source of truth for "is the user past onboarding":
 *   1. backend `user.onboarding_completed_at` (preferred — survives device swaps)
 *   2. localStorage flag (dev / pre-backend-wired fallback)
 *
 * Pass the `user` object when known (from `useAuth().user`); the helper falls
 * back to localStorage when called pre-auth or in places without user context.
 */
export function isOnboardingCompleted(user?: User | null): boolean {
  if (user && user.onboarding_completed_at) return true;
  if (typeof window === "undefined") return true;
  return Boolean(window.localStorage.getItem(STORAGE_KEY));
}

/**
 * Persist completion. Best-effort PATCHes `/users/me` so it's durable across
 * devices, AND writes localStorage so the banner hides immediately without a
 * round-trip. Both fail silently — the user-visible flow shouldn't block on
 * either side-effect.
 */
export async function markOnboardingCompleted(): Promise<void> {
  if (typeof window === "undefined") return;
  const now = new Date().toISOString();
  window.localStorage.setItem(STORAGE_KEY, now);
  try {
    await apiClient.patch<User>("/users/me", { onboarding_completed_at: now });
  } catch {
    // Backend column may not exist yet on older deploys — localStorage covers us.
  }
}

export function resetOnboarding(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function nextStep(current: OnboardingStep): OnboardingStep | null {
  const i = ONBOARDING_STEPS.indexOf(current);
  if (i < 0 || i >= ONBOARDING_STEPS.length - 1) return null;
  return ONBOARDING_STEPS[i + 1] ?? null;
}

export function prevStep(current: OnboardingStep): OnboardingStep | null {
  const i = ONBOARDING_STEPS.indexOf(current);
  if (i <= 0) return null;
  return ONBOARDING_STEPS[i - 1] ?? null;
}

export function stepIndex(step: OnboardingStep): number {
  return ONBOARDING_STEPS.indexOf(step);
}
