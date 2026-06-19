import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { BrandIcon } from "./brand-icon";

type BrandName = Parameters<typeof BrandIcon>[0]["name"];

interface IntegrationsGridProps {
  cta?: { label: string; href: string };
}

const TOOLS: { name: string; brand: BrandName }[] = [
  { name: "Google Drive", brand: "gdrive" },
  { name: "Slack", brand: "slack" },
  { name: "Notion", brand: "notion" },
  { name: "GitHub", brand: "github" },
  { name: "Gmail", brand: "gmail" },
  { name: "Dropbox", brand: "dropbox" },
  { name: "Stripe", brand: "stripe" },
  { name: "Intercom", brand: "intercom" },
  { name: "Linear", brand: "linear" },
  { name: "Figma", brand: "figma" },
  { name: "Loom", brand: "loom" },
  { name: "Microsoft 365", brand: "microsoft" },
];

export function IntegrationsGrid({ cta }: IntegrationsGridProps) {
  return (
    <>
      <div className="mb-14 max-w-2xl">
        <div className="mb-5">
          <span className="eyebrow-badge">Integrations</span>
        </div>
        <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          Works with <em>your stack.</em>
        </h2>
        <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
          Connect the tools your team already lives in. New integrations ship every month — and the
          REST API covers the rest.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {TOOLS.map((t) => (
          <div
            key={t.name}
            className="group border-foreground/12 bg-card lift hover:border-foreground/25 flex items-center gap-4 rounded-2xl border p-5 transition-colors"
          >
            <span className="border-border bg-background text-foreground/80 group-hover:text-brand group-hover:border-brand/30 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition-colors">
              <BrandIcon name={t.brand} className="h-5 w-5" />
            </span>
            <span className="text-foreground font-display text-base font-semibold">{t.name}</span>
          </div>
        ))}
      </div>

      {cta && (
        <Link
          href={cta.href}
          className="border-foreground/20 hover:border-brand text-foreground mt-12 inline-flex items-center gap-2 border-b pb-1 text-base font-medium transition-colors"
        >
          {cta.label}
          <ArrowUpRight className="h-4 w-4" />
        </Link>
      )}
    </>
  );
}
