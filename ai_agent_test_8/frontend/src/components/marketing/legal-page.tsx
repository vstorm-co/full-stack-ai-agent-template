import Link from "next/link";
import type { ReactNode } from "react";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n";
import { ROUTES } from "@/lib/constants";

import { MarketingPageLayout } from "./marketing-page-layout";

interface LegalPageProps {
  title: string;
  summary?: string;
  /** ISO date string of last update — e.g. "2026-05-08". */
  lastUpdated: string;
  /** Locale for date formatting + see-also labels. */
  locale: Locale;
  children: ReactNode;
}

export async function LegalPage({ title, summary, lastUpdated, locale, children }: LegalPageProps) {
  const tLegal = await getTranslations("marketing.legal");
  const tCommon = await getTranslations("marketing.common");

  const related = [
    { label: tLegal("terms.title"), href: ROUTES.LEGAL_TERMS },
    { label: tLegal("privacy.title"), href: ROUTES.LEGAL_PRIVACY },
    { label: tLegal("cookies.title"), href: ROUTES.LEGAL_COOKIES },
  ];

  const formattedDate = formatDate(lastUpdated, locale);

  return (
    <MarketingPageLayout
      eyebrow={tLegal("eyebrow")}
      title={title}
      description={summary}
      meta={tCommon("lastUpdated", { date: formattedDate })}
      width="narrow"
    >
      <article className="prose-marketing">{children}</article>

      <nav className="border-foreground/10 mt-16 flex flex-wrap items-center gap-3 border-t pt-8">
        <p className="text-foreground/45 font-mono text-[11px] tracking-wider uppercase">
          {tCommon("seeAlso")}
        </p>
        {related.map((r) => (
          <Link
            key={r.href}
            href={r.href}
            className="border-foreground/15 hover:border-foreground/40 text-foreground/70 hover:text-foreground inline-flex rounded-full border px-3 py-1 text-xs font-medium transition-colors"
          >
            {r.label}
          </Link>
        ))}
      </nav>
    </MarketingPageLayout>
  );
}

function formatDate(iso: string, locale: Locale): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(locale === "pl" ? "pl-PL" : "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}
