import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { MDXRemote } from "next-mdx-remote/rsc";

import { blogMdxComponents } from "@/components/blog/mdx-components";
import {
  buildFooterColumns,
  buildFooterLegal,
  buildMarketingNavLinks,
} from "@/components/marketing/footer-config";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { PillNav } from "@/components/marketing/pill-nav";
import { Section } from "@/components/marketing/section";
import type { Locale } from "@/i18n";
import { getAllBlogPosts, getBlogPost, getRelatedPosts } from "@/lib/blog";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateStaticParams() {
  const posts = await getAllBlogPosts();
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const post = await getBlogPost(slug, locale);
  if (!post) {
    return pageMetadata({
      title: "Post not found",
      description: "This blog post doesn't exist.",
      path: `/blog/${slug}`,
      locale,
      noindex: true,
    });
  }
  return pageMetadata({
    title: post.title,
    description: post.excerpt,
    path: `/blog/${slug}`,
    locale,
  });
}

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(locale === "pl" ? "pl-PL" : "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ locale: Locale; slug: string }>;
}) {
  const { locale, slug } = await params;
  const post = await getBlogPost(slug, locale);
  if (!post) notFound();
  const related = await getRelatedPosts(slug, locale, 2);

  const tNav = await getTranslations("marketing");
  const tCommon = await getTranslations("marketing.common");

  const navLinks = buildMarketingNavLinks((k) => tNav(k));
  const footerColumns = buildFooterColumns((k) => tNav(k));
  const footerLegal = buildFooterLegal((k) => tNav(k));

  const initials = post.author
    .split(" ")
    .map((n) => n[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <>
      <PillNav
        brand={APP_NAME}
        links={navLinks}
        ctaLabel={tNav("nav.getStarted")}
        ctaHref={ROUTES.REGISTER}
        secondaryCta={{ label: tNav("nav.signIn"), href: ROUTES.LOGIN }}
      />

      <main id="main">
        {/* Hero — wider container so meta + title don't feel cramped */}
        <Section theme="light" padding="pt-40 pb-12 md:pt-48 md:pb-16">
          <div className="mx-auto max-w-4xl">
            <Link
              href="/blog"
              className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider uppercase"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {tCommon("backToBlog")}
            </Link>

            <div className="text-foreground/55 mt-8 flex flex-wrap items-center gap-3 font-mono text-[11px] tracking-wider uppercase">
              {post.tags?.map((tag) => (
                <span
                  key={tag}
                  className="border-foreground/15 inline-flex rounded-full border px-2.5 py-0.5"
                >
                  {tag}
                </span>
              ))}
              <span>{formatDate(post.date, locale)}</span>
              {post.readingTime && (
                <>
                  <span aria-hidden>·</span>
                  <span>{post.readingTime}</span>
                </>
              )}
            </div>

            <h1 className="font-display text-display-xl mt-5 tracking-tight">{post.title}</h1>
            <p className="text-foreground/70 mt-5 max-w-3xl text-lg leading-relaxed">
              {post.excerpt}
            </p>

            <div className="border-foreground/10 mt-8 flex items-center gap-3 border-t pt-6">
              <span className="bg-foreground text-background flex h-10 w-10 items-center justify-center rounded-full font-mono text-xs font-semibold">
                {initials || "?"}
              </span>
              <div>
                <p className="text-foreground text-sm font-semibold">{post.author}</p>
                {post.authorRole && (
                  <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                    {post.authorRole}
                  </p>
                )}
              </div>
            </div>
          </div>
        </Section>

        {/* Body — narrower for prose readability */}
        <Section theme="light" padding="pb-24 md:pb-32">
          <div className="mx-auto max-w-3xl">
            <article className="prose-marketing">
              <MDXRemote source={post.content} components={blogMdxComponents} />
            </article>

            {/* End of post separator */}
            <div className="border-foreground/10 mt-16 flex items-center gap-4 border-t pt-8">
              <span aria-hidden className="bg-brand h-1 w-1 rounded-full" />
              <span className="text-foreground/45 font-mono text-[11px] tracking-wider uppercase">
                {locale === "pl" ? "koniec wpisu" : "end of post"}
              </span>
              <span aria-hidden className="bg-foreground/10 h-px flex-1" />
              <Link
                href="/blog"
                className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider uppercase"
              >
                {tCommon("backToBlog")} →
              </Link>
            </div>

            {related.length > 0 && (
              <aside className="mt-16">
                <p className="text-foreground/55 mb-5 font-mono text-[11px] tracking-wider uppercase">
                  {tCommon("keepReading")}
                </p>
                <ul className="grid gap-4 md:grid-cols-2">
                  {related.map((r) => (
                    <li key={r.slug}>
                      <Link
                        href={`/blog/${r.slug}`}
                        className="lift border-foreground/10 hover:border-foreground/30 bg-card group flex h-full flex-col gap-3 rounded-2xl border p-6 transition-colors"
                      >
                        <span className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
                          {formatDate(r.date, locale)}
                          {r.readingTime && ` · ${r.readingTime}`}
                        </span>
                        <h3 className="text-foreground font-display text-base leading-snug font-semibold">
                          {r.title}
                        </h3>
                        <p className="text-foreground/65 line-clamp-2 text-sm leading-relaxed">
                          {r.excerpt}
                        </p>
                        <span className="text-foreground/55 group-hover:text-foreground mt-auto inline-flex items-center gap-1 text-xs font-semibold">
                          {tCommon("read")}
                          <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </aside>
            )}
          </div>
        </Section>
      </main>

      <MarketingFooter
        brand={APP_NAME}
        tagline={tNav("footer.tagline")}
        operationalLabel={tNav("footer.operational")}
        columns={footerColumns}
        legal={footerLegal}
      />
    </>
  );
}
