import { MessageSquare, UploadCloud, UserPlus } from "lucide-react";

const STEPS = [
  {
    icon: UserPlus,
    title: "Sign up in seconds",
    body: "Create your account, invite your team, and pick the plan that fits. No credit card required for the trial.",
  },
  {
    icon: UploadCloud,
    title: "Connect your data",
    body: "Upload documents or sync from Google Drive, S3, or Notion. Your assistant learns from everything you bring.",
  },
  {
    icon: MessageSquare,
    title: "Start working with AI",
    body: "Ask questions, run workflows, and let the agent take action — across web, mobile, and your favourite chat tools.",
  },
];

export function HowItWorks() {
  return (
    <div className="grid gap-6 md:grid-cols-3 md:gap-8">
      {STEPS.map((step, i) => (
        <div
          key={step.title}
          className="border-foreground/15 bg-card lift relative overflow-hidden rounded-2xl border p-8"
        >
          <div className="text-foreground/30 absolute top-6 right-6 font-mono text-sm tabular-nums">
            0{i + 1}
          </div>
          <div className="bg-brand text-brand-foreground inline-flex h-11 w-11 items-center justify-center rounded-xl">
            <step.icon className="h-5 w-5" />
          </div>
          <h3 className="text-foreground font-display mt-6 text-xl font-bold">{step.title}</h3>
          <p className="text-foreground/65 mt-3 text-sm leading-relaxed">{step.body}</p>
          {i < STEPS.length - 1 && (
            <div
              aria-hidden
              className="border-foreground/15 absolute top-1/2 right-[-12px] hidden h-px w-6 border-t md:block"
            />
          )}
        </div>
      ))}
    </div>
  );
}
