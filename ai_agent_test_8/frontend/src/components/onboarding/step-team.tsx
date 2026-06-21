"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Plus, X } from "lucide-react";
import { toast } from "sonner";

import { Button, Input } from "@/components/ui";

import { OnboardingShell } from "./onboarding-shell";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function StepTeam() {
  const router = useRouter();
  const [emails, setEmails] = useState<string[]>(["", "", ""]);

  const updateEmail = (i: number, value: string) =>
    setEmails((prev) => prev.map((e, idx) => (idx === i ? value : e)));

  const addRow = () => setEmails((prev) => [...prev, ""]);
  const removeRow = (i: number) => setEmails((prev) => prev.filter((_, idx) => idx !== i));

  const validInvites = emails.filter((e) => e && EMAIL_RE.test(e));
  const invalid = emails.some((e) => e && !EMAIL_RE.test(e));

  const handleContinue = () => {
    if (invalid) {
      toast.error("One of the emails looks invalid");
      return;
    }
    if (validInvites.length > 0) {
      toast.success(
        `Invites queued for ${validInvites.length} ${validInvites.length === 1 ? "person" : "people"}`,
      );
    }
    router.push("/onboarding/done");
  };

  return (
    <OnboardingShell
      step="team"
      title="Bring your team along"
      description="Invite up to 5 teammates now — they'll get an email with a magic-link to join."
    >
      <div className="space-y-2">
        {emails.map((email, i) => (
          <div key={i} className="flex items-center gap-2">
            <Input
              type="email"
              placeholder="teammate@company.com"
              value={email}
              onChange={(e) => updateEmail(i, e.target.value)}
              autoComplete="email"
              className="h-11 flex-1 rounded-xl"
            />
            {emails.length > 1 && (
              <button
                type="button"
                onClick={() => removeRow(i)}
                className="text-muted-foreground hover:text-foreground hover:bg-muted h-9 w-9 shrink-0 rounded-md transition-colors"
                aria-label="Remove invite"
              >
                <X className="mx-auto h-4 w-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      {emails.length < 5 && (
        <button
          type="button"
          onClick={addRow}
          className="text-muted-foreground hover:text-foreground mt-3 inline-flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase"
        >
          <Plus className="h-3.5 w-3.5" />
          Add another
        </button>
      )}

      <div className="mt-8 flex items-center gap-3">
        <Button size="lg" onClick={handleContinue}>
          {validInvites.length > 0
            ? `Send ${validInvites.length} invite${validInvites.length === 1 ? "" : "s"}`
            : "Continue"}
          <ArrowRight className="h-4 w-4" />
        </Button>
        <Button size="lg" variant="ghost" onClick={() => router.push("/onboarding/done")}>
          Skip
        </Button>
      </div>
    </OnboardingShell>
  );
}
