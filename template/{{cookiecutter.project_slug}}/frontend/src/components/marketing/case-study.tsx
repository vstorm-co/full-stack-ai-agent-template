{% raw %}import { Quote } from "lucide-react";

import { AnimatedNumber } from "./animated-number";

interface CaseStudyProps {
  quote: string;
  name: string;
  role: string;
  company: string;
  metrics: { value: string; label: string }[];
}

export function CaseStudy({ quote, name, role, company, metrics }: CaseStudyProps) {
  return (
    <div className="border-foreground/12 bg-foreground/[0.02] relative isolate overflow-hidden rounded-3xl border p-8 md:p-14">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-20 -z-10 h-[460px] w-[460px] rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.28), transparent 65%)",
        }}
      />
      <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-50" />

      <div className="grid gap-12 md:grid-cols-[1.5fr_1fr] md:items-center">
        <div>
          <span className="eyebrow-badge mb-8">Case study</span>
          <Quote className="text-brand mb-5 h-9 w-9" />
          <blockquote className="text-display-md text-foreground/90 [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
            &ldquo;{quote}&rdquo;
          </blockquote>
          <div className="mt-8 flex items-center gap-3">
            <span
              aria-hidden
              className="text-brand-foreground flex h-11 w-11 items-center justify-center rounded-full font-mono text-xs font-semibold"
              style={{
                background:
                  "linear-gradient(135deg, var(--color-brand), oklch(from var(--color-brand) calc(l - 0.12) c h))",
              }}
            >
              {name
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")}
            </span>
            <div>
              <p className="text-foreground text-sm font-semibold">{name}</p>
              <p className="text-foreground/55 text-xs">
                {role} · {company}
              </p>
            </div>
          </div>
        </div>

        <dl className="divide-foreground/10 border-foreground/10 grid divide-y rounded-2xl border">
          {metrics.map((m) => (
            <div key={m.label} className="px-6 py-5">
              <dt className="text-foreground font-mono text-4xl font-medium tracking-tight tabular-nums">
                <AnimatedNumber value={m.value} />
              </dt>
              <dd className="text-foreground/55 mt-1 text-sm">{m.label}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
{% endraw %}
