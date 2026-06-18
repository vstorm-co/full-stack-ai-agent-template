import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import matter from "gray-matter";

import { defaultLocale, type Locale } from "@/i18n";

const BLOG_DIR = path.join(process.cwd(), "content", "blog");

export interface BlogFrontmatter {
  title: string;
  excerpt: string;
  date: string; // ISO YYYY-MM-DD
  author: string;
  authorRole?: string;
  tags?: string[];
  cover?: string;
  readingTime?: string;
}

export interface BlogPostMeta extends BlogFrontmatter {
  slug: string;
}

export interface BlogPost extends BlogPostMeta {
  content: string;
}

/**
 * Per-locale MDX file resolution.
 *
 * For locale `pl` and slug `foo`, we try `content/blog/foo.pl.mdx` first;
 * if absent, fall back to `content/blog/foo.mdx` (the default-locale source).
 * This lets a single post show up in both languages by default, with optional
 * translation per locale by dropping a `.{locale}.mdx` file next to the source.
 */

function isValidFrontmatter(data: Record<string, unknown>): boolean {
  return (
    typeof data["title"] === "string" &&
    typeof data["excerpt"] === "string" &&
    typeof data["date"] === "string" &&
    typeof data["author"] === "string"
  );
}

function estimateReadingTime(content: string): string {
  const words = content.trim().split(/\s+/).length;
  const minutes = Math.max(1, Math.round(words / 220));
  return `${minutes} min read`;
}

async function readPostFromPath(slug: string, filePath: string): Promise<BlogPost> {
  const raw = await readFile(filePath, "utf8");
  const { data, content } = matter(raw);
  if (!isValidFrontmatter(data)) {
    throw new Error(`Invalid frontmatter in ${path.basename(filePath)}`);
  }
  const fm = data as BlogFrontmatter;
  return {
    slug,
    title: fm.title,
    excerpt: fm.excerpt,
    date: fm.date,
    author: fm.author,
    authorRole: fm.authorRole,
    tags: fm.tags,
    cover: fm.cover,
    readingTime: fm.readingTime ?? estimateReadingTime(content),
    content,
  };
}

async function resolvePostFile(slug: string, locale: Locale): Promise<string | null> {
  // Try locale-specific first, fall back to default. ENOENT => try next.
  const candidates = [
    locale !== defaultLocale ? path.join(BLOG_DIR, `${slug}.${locale}.mdx`) : null,
    path.join(BLOG_DIR, `${slug}.mdx`),
  ].filter((p): p is string => p !== null);

  for (const c of candidates) {
    try {
      await readFile(c, "utf8");
      return c;
    } catch {
      // try next
    }
  }
  return null;
}

/** Strip optional `.{locale}` suffix from a filename like `foo.pl.mdx` → `foo`. */
function slugFromFilename(filename: string): string {
  const noExt = filename.replace(/\.mdx$/, "");
  // If looks like `slug.{locale}` and the locale part matches a real locale,
  // strip it. Otherwise treat the whole thing as the slug.
  const parts = noExt.split(".");
  if (parts.length >= 2) {
    const last = parts[parts.length - 1];
    if (last === "pl" || last === "en") {
      return parts.slice(0, -1).join(".");
    }
  }
  return noExt;
}

export async function getAllBlogPosts(locale: Locale = defaultLocale): Promise<BlogPostMeta[]> {
  let files: string[];
  try {
    files = await readdir(BLOG_DIR);
  } catch {
    return [];
  }
  const slugs = Array.from(new Set(files.filter((f) => f.endsWith(".mdx")).map(slugFromFilename)));

  const posts = await Promise.all(
    slugs.map(async (slug) => {
      const file = await resolvePostFile(slug, locale);
      if (!file) return null;
      try {
        return await readPostFromPath(slug, file);
      } catch {
        return null;
      }
    }),
  );

  return posts
    .filter((p): p is BlogPost => p !== null)
    .map(({ content: _content, ...meta }) => meta)
    .sort((a, b) => b.date.localeCompare(a.date));
}

export async function getBlogPost(
  slug: string,
  locale: Locale = defaultLocale,
): Promise<BlogPost | null> {
  const file = await resolvePostFile(slug, locale);
  if (!file) return null;
  try {
    return await readPostFromPath(slug, file);
  } catch {
    return null;
  }
}

export async function getRelatedPosts(
  slug: string,
  locale: Locale = defaultLocale,
  limit = 2,
): Promise<BlogPostMeta[]> {
  const all = await getAllBlogPosts(locale);
  return all.filter((p) => p.slug !== slug).slice(0, limit);
}
