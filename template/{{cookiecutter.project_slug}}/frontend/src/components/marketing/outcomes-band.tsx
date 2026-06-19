import { Clock, MessageSquare, Search, Zap, type LucideIcon } from "lucide-react";

import { AnimatedNumber } from "./animated-number";

const CARD =
  "group border-foreground/12 bg-card lift hover:border-foreground/25 rounded-2xl border p-7 transition-colors";

const METRICS: { icon: LucideIcon; value: string; label: string }[] = [
  { icon: Clock, value: "10 hrs", label: "saved per person every week" },
  { icon: Zap, value: "3×", label: "faster team onboarding" },
  { icon: MessageSquare, value: "92%", label: "of questions answered instantly" },
  { icon: Search, value: "40%", label: "less time spent searching" },
];

export function OutcomesBand() {
  return (
    <>
      <div className="mb-14 max-w-2xl">
        <div className="mb-5">
          <span className="eyebrow-badge">Outcomes</span>
        </div>
        <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          Real results, <em>not just features.</em>
        </h2>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {METRICS.map((m) => (
          <div key={m.label} className={CARD}>
            <span
              aria-hidden
              className="bg-brand/12 text-brand ring-brand/20 inline-flex h-11 w-11 items-center justify-center rounded-xl ring-1"
            >
              <m.icon className="h-5 w-5" strokeWidth={2} />
            </span>
            <div className="text-foreground mt-6 font-mono text-5xl font-medium tracking-tight tabular-nums">
              <AnimatedNumber value={m.value} />
            </div>
            <p className="text-foreground/60 mt-2 text-sm leading-relaxed">{m.label}</p>
          </div>
        ))}
      </div>
    </>
  );
}
