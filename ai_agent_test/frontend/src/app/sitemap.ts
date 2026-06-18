import type { MetadataRoute } from "next";

import { getAllBlogPosts } from "@/lib/blog";
import { SITE } from "@/lib/seo";

/** Public-only sitemap. Dashboard, chat, admin, billing, settings etc. are
 *  authenticated and should NOT be indexed (and are blocked in robots.ts). */
type Freq = MetadataRoute.Sitemap[number]["changeFrequency"];

const PUBLIC_PATHS: { path: string; changeFrequency: Freq; priority: number }[] = [
  { path: "/", changeFrequency: "weekly", priority: 1.0 },
  { path: "/pricing", changeFrequency: "weekly", priority: 0.9 },
  { path: "/about", changeFrequency: "monthly", priority: 0.7 },
  { path: "/blog", changeFrequency: "weekly", priority: 0.8 },
  { path: "/changelog", changeFrequency: "weekly", priority: 0.6 },
  { path: "/help", changeFrequency: "weekly", priority: 0.7 },
  { path: "/contact", changeFrequency: "monthly", priority: 0.6 },
  { path: "/security", changeFrequency: "monthly", priority: 0.6 },
  { path: "/community", changeFrequency: "monthly", priority: 0.6 },
  { path: "/legal/terms", changeFrequency: "yearly", priority: 0.3 },
  { path: "/legal/privacy", changeFrequency: "yearly", priority: 0.3 },
  { path: "/legal/cookies", changeFrequency: "yearly", priority: 0.3 },
  { path: "/login", changeFrequency: "yearly", priority: 0.3 },
  { path: "/register", changeFrequency: "yearly", priority: 0.5 },
];

function entryFor(
  path: string,
  changeFrequency: Freq,
  priority: number,
  lastModified: Date,
): MetadataRoute.Sitemap {
  const out: MetadataRoute.Sitemap = [];
  for (const locale of SITE.locales) {
    const tail = path === "/" ? "" : path;
    const url = `${SITE.url}/${locale}${tail}`;
    const languages: Record<string, string> = Object.fromEntries(
      SITE.locales.map((l) => [l, `${SITE.url}/${l}${tail}`]),
    );
    languages["x-default"] = `${SITE.url}/${SITE.defaultLocale}${tail}`;
    out.push({ url, lastModified, changeFrequency, priority, alternates: { languages } });
  }
  return out;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [];

  for (const { path, changeFrequency, priority } of PUBLIC_PATHS) {
    entries.push(...entryFor(path, changeFrequency, priority, now));
  }

  // Blog posts — one entry per post (per locale).
  const posts = await getAllBlogPosts();
  for (const post of posts) {
    const lastModified = new Date(post.date);
    entries.push(
      ...entryFor(
        `/blog/${post.slug}`,
        "monthly",
        0.7,
        Number.isNaN(lastModified.getTime()) ? now : lastModified,
      ),
    );
  }

  return entries;
}
