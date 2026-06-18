import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";

import { EmptyState } from "@/components/states";
import { MarketingPageLayout } from "@/components/marketing/marketing-page-layout";
import type { Locale } from "@/i18n";
import { getAllBlogPosts } from "@/lib/blog";
import { APP_NAME } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Blog",
    description: `Build-in-public posts, engineering deep-dives, and product notes from the ${APP_NAME} team.`,
    path: "/blog",
    locale,
  });
}

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(locale === "pl" ? "pl-PL" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default async function BlogIndexPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations("marketing.blog");
  const tCommon = await getTranslations("marketing.common");
  const posts = await getAllBlogPosts(locale);
  const [hero, ...rest] = posts;

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      width="wide"
    >
      {posts.length === 0 ? (
        <EmptyState icon={BookOpen} title={t("noPostsTitle")} description={t("noPostsDesc")} />
      ) : (
        <div className="space-y-10">
          {/* Featured hero card */}
          {hero && (
            <Link
              href={`/blog/${hero.slug}`}
              className="lift border-foreground/10 hover:border-foreground/30 bg-card group relative grid gap-8 overflow-hidden rounded-3xl border p-7 transition-colors md:grid-cols-[1.1fr_0.9fr] md:p-10"
            >
              {/* Spotlight bg */}
              <div
                aria-hidden
                className="bg-brand/[0.08] pointer-events-none absolute -top-32 -right-32 h-80 w-80 rounded-full blur-[120px]"
              />
              <div
                aria-hidden
                className="bg-foreground/[0.04] pointer-events-none absolute -bottom-32 -left-32 h-72 w-72 rounded-full blur-[120px]"
              />

              <div className="relative flex flex-col gap-4">
                <span className="text-foreground/55 inline-flex items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
                  <span aria-hidden className="bg-brand h-1 w-1 rounded-full" />
                  {t("featured")}
                  <span aria-hidden className="text-foreground/30">
                    ·
                  </span>
                  {formatDate(hero.date, locale)}
                </span>
                <h2 className="font-display text-foreground text-3xl leading-tight font-bold tracking-tight md:text-4xl">
                  {hero.title}
                </h2>
                <p className="text-foreground/70 text-base leading-relaxed">{hero.excerpt}</p>
                <div className="text-foreground/55 mt-1 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-wider uppercase">
                  <span>{hero.author}</span>
                  {hero.readingTime && (
                    <>
                      <span aria-hidden>·</span>
                      <span>{hero.readingTime}</span>
                    </>
                  )}
                </div>
                <span className="text-foreground group-hover:text-foreground mt-2 inline-flex items-center gap-1.5 text-sm font-semibold">
                  {tCommon("readPost")}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
              </div>

              {/* Decorative panel — typographic mark instead of cover image */}
              <div className="border-foreground/10 bg-foreground/[0.02] relative hidden flex-col justify-between overflow-hidden rounded-2xl border p-6 md:flex">
                <div>
                  {hero.tags && hero.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {hero.tags.map((tag) => (
                        <span
                          key={tag}
                          className="border-foreground/15 text-foreground/65 inline-flex rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wider uppercase"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div
                  aria-hidden
                  className="font-display text-foreground/8 absolute -right-6 -bottom-12 text-[14rem] leading-none font-black tracking-tighter select-none"
                >
                  {String(hero.title.split(" ")[0] ?? "Notes").slice(0, 3)}
                </div>
              </div>
            </Link>
          )}

          {/* Rest — 3-col on desktop, 2 on tablet */}
          {rest.length > 0 && (
            <ul className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {rest.map((p) => (
                <li key={p.slug}>
                  <Link
                    href={`/blog/${p.slug}`}
                    className="lift border-foreground/10 hover:border-foreground/30 bg-card group flex h-full flex-col gap-4 rounded-2xl border p-6 transition-colors"
                  >
                    {/* Tag row */}
                    {p.tags && p.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {p.tags.slice(0, 2).map((tag) => (
                          <span
                            key={tag}
                            className="border-foreground/10 text-foreground/55 inline-flex rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <h3 className="text-foreground font-display text-xl leading-tight font-bold tracking-tight">
                      {p.title}
                    </h3>
                    <p className="text-foreground/65 line-clamp-3 flex-1 text-sm leading-relaxed">
                      {p.excerpt}
                    </p>
                    <div className="border-foreground/10 mt-1 flex items-center justify-between border-t pt-3">
                      <span className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                        {formatDate(p.date, locale)}
                        {p.readingTime && ` · ${p.readingTime}`}
                      </span>
                      <ArrowRight className="text-foreground/30 group-hover:text-foreground h-4 w-4 transition-all group-hover:translate-x-1" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </MarketingPageLayout>
  );
}
