"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, Database, MessageSquare, Users } from "lucide-react";

import { useAuth } from "@/hooks";

import { OnboardingShell } from "./onboarding-shell";

const PERKS = [
  {
    icon: MessageSquare,
    title: "Pick your agent",
    description: "Choose the framework that powers your assistant.",
  },
  {
    icon: Database,
    title: "Connect your data",
    description: "Upload docs or sync from Drive — we'll index them.",
  },
  {
    icon: Users,
    title: "Invite your team",
    description: "Bring teammates so everyone's chats stay in sync.",
  },
];

export function StepWelcome() {
  const router = useRouter();
  const { user } = useAuth();

  return (
    <OnboardingShell
      step="welcome"
      title={user?.full_name ? `Welcome, ${user.full_name.split(" ")[0]}.` : "Welcome aboard."}
      description="Let's get you set up in under 2 minutes. You can skip any step and come back later."
    >
      <ul className="space-y-3">
        {PERKS.map((perk) => (
          <li
            key={perk.title}
            className="border-foreground/10 bg-card flex items-start gap-4 rounded-2xl border p-5"
          >
            <div className="bg-brand/15 flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
              <perk.icon className="text-foreground h-4 w-4" />
            </div>
            <div className="flex-1">
              <p className="text-foreground font-display text-base font-semibold">{perk.title}</p>
              <p className="text-foreground/65 mt-0.5 text-sm">{perk.description}</p>
            </div>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={() => router.push("/onboarding/agent")}
        className="bg-foreground text-background hover:bg-foreground/90 mt-8 inline-flex h-12 items-center justify-center gap-2 rounded-full px-6 text-sm font-medium transition-colors"
      >
        Let&apos;s go
        <ArrowRight className="h-4 w-4" />
      </button>
    </OnboardingShell>
  );
}
