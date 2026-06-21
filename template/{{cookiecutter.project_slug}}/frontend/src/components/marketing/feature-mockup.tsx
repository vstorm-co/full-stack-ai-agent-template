{% raw %}import { Bot, FileText, Search, TrendingUp, User, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";

type MockupKind = "agents" | "rag" | "billing";

interface FeatureMockupProps {
  kind: MockupKind;
  className?: string;
}

/** Stylized mini-UIs that hint at the actual product. Pure CSS/SVG, no real data. */
export function FeatureMockup({ kind, className }: FeatureMockupProps) {
  if (kind === "agents") return <AgentMockup className={className} />;
  if (kind === "rag") return <RagMockup className={className} />;
  return <BillingMockup className={className} />;
}

function MockFrame({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "border-foreground/15 bg-card relative w-full max-w-lg overflow-hidden rounded-2xl border shadow-2xl",
        className,
      )}
    >
      <div className="border-foreground/10 flex items-center gap-1.5 border-b px-4 py-2.5">
        <span className="bg-foreground/20 h-2 w-2 rounded-full" />
        <span className="bg-foreground/20 h-2 w-2 rounded-full" />
        <span className="bg-foreground/20 h-2 w-2 rounded-full" />
      </div>
      {children}
    </div>
  );
}

function AgentMockup({ className }: { className?: string }) {
  return (
    <MockFrame className={className}>
      <div className="space-y-3 p-4">
        <div className="flex justify-end">
          <div className="bg-foreground text-background flex max-w-[80%] items-center gap-2 rounded-2xl rounded-tr-sm px-3 py-2 text-xs">
            <span>Find churn signals in last quarter.</span>
            <User className="h-3 w-3 opacity-60" />
          </div>
        </div>

        <div className="flex">
          <div className="border-brand/40 bg-brand/15 flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px]">
            <Wrench className="h-3 w-3" />
            <span className="text-foreground/80">rag.search · 4 docs</span>
          </div>
        </div>

        <div className="flex">
          <div className="bg-card border-foreground/10 max-w-[88%] rounded-2xl rounded-tl-sm border p-3">
            <div className="text-foreground/55 mb-1.5 flex items-center gap-1.5">
              <Bot className="h-3 w-3" />
              <span className="font-mono text-[10px] tracking-wider uppercase">Assistant</span>
            </div>
            <p className="text-foreground text-xs leading-relaxed">
              137 sessions. Top friction: setup confusion (58%), Stripe webhooks (22%)…
            </p>
          </div>
        </div>

        <div className="border-foreground/10 mt-2 flex items-center gap-2 rounded-lg border px-3 py-2">
          <span className="text-foreground/40 flex-1 text-xs">Ask anything…</span>
          <kbd className="border-foreground/15 text-foreground/50 inline-flex items-center gap-0.5 rounded border px-1.5 py-0.5 font-mono text-[10px]">
            ⌘ ↵
          </kbd>
        </div>
      </div>
    </MockFrame>
  );
}

function RagMockup({ className }: { className?: string }) {
  const RESULTS = [
    {
      title: "onboarding-feedback-q1.pdf",
      snippet: "...users struggled with the database setup step in 58% of cases...",
      score: 0.94,
    },
    {
      title: "support-tickets-march.md",
      snippet: "...repeatedly mentioned Stripe webhook configuration was unclear...",
      score: 0.87,
    },
    {
      title: "exit-survey-summary.docx",
      snippet: "...top reason for trial churn cited as missing example projects...",
      score: 0.82,
    },
  ];
  return (
    <MockFrame className={className}>
      <div className="p-4">
        <div className="border-foreground/10 mb-3 flex items-center gap-2 rounded-lg border px-3 py-2">
          <Search className="text-foreground/40 h-3.5 w-3.5" />
          <span className="text-foreground text-xs">churn signals</span>
        </div>
        <ul className="space-y-2.5">
          {RESULTS.map((r) => (
            <li key={r.title} className="border-foreground/10 rounded-lg border p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <FileText className="text-foreground/50 h-3 w-3" />
                  <span className="text-foreground font-mono text-[11px]">{r.title}</span>
                </div>
                <span className="bg-brand text-brand-foreground rounded-full px-1.5 py-0.5 font-mono text-[10px] tabular-nums">
                  {r.score.toFixed(2)}
                </span>
              </div>
              <p className="text-foreground/65 mt-1.5 text-[11px] leading-snug">{r.snippet}</p>
            </li>
          ))}
        </ul>
      </div>
    </MockFrame>
  );
}

function BillingMockup({ className }: { className?: string }) {
  const bars = [22, 28, 32, 30, 38, 42, 48, 45, 52, 58, 64, 72];
  const max = Math.max(...bars);
  return (
    <MockFrame className={className}>
      <div className="space-y-4 p-4">
        <div>
          <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
            Monthly recurring
          </p>
          <p className="text-foreground font-display mt-1 text-3xl font-bold tracking-tight">
            $2,840
          </p>
          <p className="text-brand mt-0.5 flex items-center gap-1 text-xs font-medium">
            <TrendingUp className="h-3 w-3" />
            +18% vs last month
          </p>
        </div>

        <div className="flex h-20 items-end gap-1">
          {bars.map((b, i) => (
            <div
              key={i}
              className="bg-foreground/15 flex-1 rounded-sm"
              style={{ height: `${(b / max) * 100}%` }}
            >
              <div
                className="bg-brand h-1 w-full"
                style={{ display: i === bars.length - 1 ? "block" : "none" }}
              />
            </div>
          ))}
        </div>

        <div className="border-foreground/10 grid grid-cols-3 gap-2 border-t pt-3">
          <div>
            <p className="text-foreground/45 font-mono text-[10px] uppercase">Active</p>
            <p className="text-foreground font-mono text-sm font-medium">186</p>
          </div>
          <div>
            <p className="text-foreground/45 font-mono text-[10px] uppercase">Trials</p>
            <p className="text-foreground font-mono text-sm font-medium">42</p>
          </div>
          <div>
            <p className="text-foreground/45 font-mono text-[10px] uppercase">Churn</p>
            <p className="text-foreground font-mono text-sm font-medium">2.1%</p>
          </div>
        </div>
      </div>
    </MockFrame>
  );
}
{% endraw %}
