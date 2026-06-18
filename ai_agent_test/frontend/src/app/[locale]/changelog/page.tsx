import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { MarketingPageLayout } from "@/components/marketing/marketing-page-layout";
import type { Locale } from "@/i18n";
import { CHANGELOG, type ChangeType } from "@/lib/changelog";
import { APP_NAME } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Changelog",
    description: `What's new in ${APP_NAME} — release notes and product updates.`,
    path: "/changelog",
    locale,
  });
}

const TYPE_STYLES: Record<ChangeType, string> = {
  feat: "bg-brand text-brand-foreground border-transparent",
  improvement: "border-foreground/20 text-foreground",
  fix: "bg-yellow-500/10 text-yellow-500 border-yellow-500/30",
  security: "bg-destructive/10 text-destructive border-destructive/30",
  chore: "border-foreground/10 text-foreground/55",
};

export default async function ChangelogPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations("marketing.changelog");
  const isPl = locale === "pl";

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(isPl ? "pl-PL" : "en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description", { appName: APP_NAME })}
      width="wide"
    >
      <div className="relative">
        {/* Vertical connector line — sits behind the version dots. */}
        <div
          aria-hidden
          className="bg-foreground/10 pointer-events-none absolute top-2 bottom-2 left-[18px] w-px md:left-[22px]"
        />

        <ol className="space-y-12">
          {CHANGELOG.map((entry) => (
            <li key={entry.version} className="relative pl-12 md:pl-16">
              {/* Version dot */}
              <span
                aria-hidden
                className="bg-brand border-background absolute top-1.5 left-0 inline-flex h-9 w-9 items-center justify-center rounded-full border-4 md:h-11 md:w-11"
              />
              <span
                aria-hidden
                className="text-brand-foreground absolute top-1.5 left-0 inline-flex h-9 w-9 items-center justify-center rounded-full font-mono text-[10px] font-bold tracking-wider md:h-11 md:w-11 md:text-xs"
              >
                v{entry.version.split(".")[0]}
              </span>

              <article className="border-foreground/10 bg-card rounded-3xl border p-6 md:p-8">
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <span className="bg-foreground text-background rounded-full px-3 py-1 font-mono text-[11px] font-semibold tracking-wider uppercase">
                    v{entry.version}
                  </span>
                  <time className="text-foreground/55 font-mono text-xs tracking-wider uppercase">
                    {formatDate(entry.date)}
                  </time>
                </div>
                <h2 className="text-display-md mb-3">{entry.title}</h2>
                {entry.description && (
                  <p className="text-foreground/70 mb-6 leading-relaxed">{entry.description}</p>
                )}
                <ul className="space-y-2.5">
                  {entry.changes.map((change, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm">
                      <span
                        className={`mt-0.5 inline-flex shrink-0 items-center rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase ${
                          TYPE_STYLES[change.type] ?? TYPE_STYLES.chore
                        }`}
                      >
                        {change.type}
                      </span>
                      <span className="text-foreground/85 leading-relaxed">{change.text}</span>
                    </li>
                  ))}
                </ul>
              </article>
            </li>
          ))}
        </ol>

        {/* End marker */}
        <div className="relative mt-2 pl-12 md:pl-16">
          <span
            aria-hidden
            className="border-foreground/20 bg-background absolute top-0 left-0 inline-flex h-9 w-9 items-center justify-center rounded-full border-2 border-dashed md:h-11 md:w-11"
          />
          <p className="text-foreground/45 font-mono text-[11px] tracking-wider uppercase md:py-2.5">
            {isPl ? "→ początek historii" : "→ start of history"}
          </p>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
