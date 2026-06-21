/** Single source of truth for SEO metadata.
 *
 *  All public-page metadata helpers (root layout, per-page generateMetadata,
 *  sitemap, robots, manifest, OG image generator) pull from here. Edit one
 *  file to retheme the site's identity.
 *
 *  ENV: NEXT_PUBLIC_SITE_URL = canonical https origin (no trailing slash).
 *  Falls back to a sensible localhost default in dev.
 */

import type { Metadata } from "next";

import { APP_NAME } from "@/lib/constants";
import { defaultLocale, locales } from "@/i18n";

export const SITE = {
  name: APP_NAME,
  /** Tagline used in title templates + OG defaults. */
  tagline: "AI assistant for modern teams",
  /** One-paragraph default description (≤160 chars for SERP truncation). */
  description:
    "Plug in your docs, your tools, and your data. Ask anything — get answers grounded in everything your team has ever shipped.",
  /** Canonical absolute origin. NO trailing slash. */
  url:
    (process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") as string | undefined) ??
    "http://localhost:{{ cookiecutter.frontend_port }}",
  /** Twitter handle for `twitter:site` (with @). Empty string disables. */
  twitter: "",
  /** Theme color used in PWA manifest + browser chrome. */
  themeColor: "#0E0E0C",
  /** Long-form keywords. Light SEO weight today; useful for clarity. */
  keywords: [
    "AI assistant",
    "team knowledge",
    "AI agent",
    "RAG",
    "team productivity",
    "knowledge base",
    "internal search",
    "B2B SaaS",
  ],
  /** Locale defaults — pulls from your i18n config. */
  defaultLocale,
  locales: [...locales],
} as const;

/** Map our locale codes → BCP-47 / Open Graph locale strings. */
export const OG_LOCALE: Record<(typeof locales)[number], string> = {
  en: "en_US",
{%- if cookiecutter.enable_i18n %}
  pl: "pl_PL",
{%- endif %}
};

interface PageMetaInput {
  /** Page-specific title fragment. The template adds " | <brand>". */
  title: string;
  description: string;
  /** Path WITHOUT locale prefix (e.g. "/pricing", "/"). Used to build canonical + alternates. */
  path?: string;
  /** Active locale. Defaults to site default. */
  locale?: (typeof locales)[number];
  /** Disable indexing (e.g. drafts, internal pages). */
  noindex?: boolean;
  /** Override OG image. Defaults to dynamic /opengraph-image. */
  ogImage?: string;
}

/** Build a fully-formed Next.js Metadata object for a public page. */
export function pageMetadata(input: PageMetaInput): Metadata {
  const locale = input.locale ?? SITE.defaultLocale;
  const path = normalizePath(input.path ?? "/");
  const localizedPath = path === "/" ? `/${locale}` : `/${locale}${path}`;
  const canonical = `${SITE.url}${localizedPath}`;
  const title = input.title === SITE.name ? SITE.name : `${input.title} | ${SITE.name}`;
  const ogImageUrl = input.ogImage ?? `${SITE.url}/opengraph-image`;

  return {
    title,
    description: input.description,
    keywords: [...SITE.keywords],
    alternates: {
      canonical,
      languages: Object.fromEntries(
        SITE.locales.map((loc) => [
          loc,
          `${SITE.url}${path === "/" ? `/${loc}` : `/${loc}${path}`}`,
        ]),
      ),
    },
    openGraph: {
      title,
      description: input.description,
      url: canonical,
      siteName: SITE.name,
      type: "website",
      locale: OG_LOCALE[locale],
      alternateLocale: SITE.locales.filter((l) => l !== locale).map((l) => OG_LOCALE[l]),
      images: [
        {
          url: ogImageUrl,
          width: 1200,
          height: 630,
          alt: `${SITE.name} — ${SITE.tagline}`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description: input.description,
      images: [ogImageUrl],
      ...(SITE.twitter ? { site: SITE.twitter, creator: SITE.twitter } : {}),
    },
    robots: input.noindex
      ? { index: false, follow: false }
      : { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 },
  };
}

function normalizePath(p: string): string {
  if (!p.startsWith("/")) return `/${p}`;
  if (p.length > 1 && p.endsWith("/")) return p.slice(0, -1);
  return p;
}
