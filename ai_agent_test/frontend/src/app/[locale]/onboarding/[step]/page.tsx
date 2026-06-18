import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AuthGuard } from "@/components/layout/auth-guard";
import { StepAgent } from "@/components/onboarding/step-agent";
import { StepData } from "@/components/onboarding/step-data";
import { StepDone } from "@/components/onboarding/step-done";
import { StepTeam } from "@/components/onboarding/step-team";
import { StepWelcome } from "@/components/onboarding/step-welcome";
import { ONBOARDING_STEPS, type OnboardingStep } from "@/components/onboarding/onboarding-state";
import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

export const dynamic = "force-static";

export function generateStaticParams() {
  return ONBOARDING_STEPS.map((step) => ({ step }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale; step: string }>;
}): Promise<Metadata> {
  const { locale, step } = await params;
  return pageMetadata({
    title: "Get started",
    description: "Set up your workspace.",
    path: `/onboarding/${step}`,
    locale,
    noindex: true,
  });
}

interface PageProps {
  params: Promise<{ step: string }>;
}

export default async function OnboardingStepPage({ params }: PageProps) {
  const { step } = await params;
  if (!ONBOARDING_STEPS.includes(step as OnboardingStep)) {
    notFound();
  }

  return (
    <AuthGuard>
      {step === "welcome" && <StepWelcome />}
      {step === "agent" && <StepAgent />}
      {step === "data" && <StepData />}
      {step === "team" && <StepTeam />}
      {step === "done" && <StepDone />}
    </AuthGuard>
  );
}
