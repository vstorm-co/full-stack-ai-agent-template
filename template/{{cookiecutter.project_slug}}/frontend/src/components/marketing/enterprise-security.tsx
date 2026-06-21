{% raw %}import Link from "next/link";
import {
  ArrowUpRight,
  Fingerprint,
  KeyRound,
  Lock,
  ScrollText,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface EnterpriseSecurityProps {
  cta?: { label: string; href: string };
}

const CARD =
  "group border-foreground/12 bg-card lift hover:border-foreground/25 relative overflow-hidden rounded-2xl border transition-colors";

const FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: KeyRound,
    title: "SSO & SAML",
    body: "One-click sign-in with Okta, Google, Azure AD and any SAML provider.",
  },
  {
    icon: Fingerprint,
    title: "Role-based access",
    body: "Granular roles and permissions so people see only what they should.",
  },
  {
    icon: Lock,
    title: "Encrypted end to end",
    body: "AES-256 at rest, TLS 1.3 in transit. Your keys, your data.",
  },
  {
    icon: ScrollText,
    title: "Audit logs",
    body: "Every action recorded and exportable for compliance reviews.",
  },
];

const COMPLIANCE = ["SOC 2 Type II", "GDPR", "ISO 27001", "HIPAA"];

export function EnterpriseSecurity({ cta }: EnterpriseSecurityProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:auto-rows-[200px] md:grid-cols-4">
      <div className={cn(CARD, "md:col-span-2 md:row-span-2", "flex flex-col p-8")}>
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 -right-24 -z-0 h-72 w-72 rounded-full blur-3xl"
          style={{ background: "oklch(from var(--color-brand) l c h / 0.18)" }}
        />
        <div className="relative z-10 flex h-full flex-col">
          <span className="eyebrow-badge mb-6 self-start">Enterprise-ready</span>
          <h2 className="text-display-md text-foreground [&_em]:font-accent [&_em]:text-foreground/85 [&_em]:font-normal [&_em]:italic">
            Security and control, <em>built in.</em>
          </h2>
          <p className="text-foreground/70 mt-4 max-w-md text-base leading-relaxed">
            From day one your data is encrypted, access-controlled and audited. Enterprise teams get
            SSO, data residency and a dedicated success manager.
          </p>

          <div className="mt-auto pt-8">
            <div className="flex flex-wrap gap-2">
              {COMPLIANCE.map((c) => (
                <span
                  key={c}
                  className="border-foreground/15 bg-background/40 text-foreground/80 inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 font-mono text-xs"
                >
                  <ShieldCheck className="text-brand h-3.5 w-3.5" />
                  {c}
                </span>
              ))}
            </div>
            {cta && (
              <Link
                href={cta.href}
                className="text-foreground hover:text-brand group/cta mt-6 inline-flex items-center gap-1.5 text-sm font-medium"
              >
                {cta.label}
                <ArrowUpRight className="h-4 w-4 transition-transform group-hover/cta:translate-x-0.5 group-hover/cta:-translate-y-0.5" />
              </Link>
            )}
          </div>
        </div>
      </div>

      {FEATURES.map((f) => (
        <div key={f.title} className={cn(CARD, "flex flex-col justify-center p-6")}>
          <span
            aria-hidden
            className="bg-brand/12 text-brand ring-brand/20 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1"
          >
            <f.icon className="h-5 w-5" strokeWidth={2} />
          </span>
          <p className="text-foreground font-display mt-4 text-base font-bold">{f.title}</p>
          <p className="text-foreground/65 mt-1 text-sm leading-relaxed">{f.body}</p>
        </div>
      ))}
    </div>
  );
}
{% endraw %}
