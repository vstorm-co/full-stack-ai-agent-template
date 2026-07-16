"use client";
import { ExternalLink, Globe } from "lucide-react";
import { cleanPageText, parseFetchedPage } from "@/lib/py-literal";
import { MarkdownContent } from "../markdown-content";

/** Renders a `web_fetch` / `fetch_url` result as a page card: clickable source link + the fetched
 *  content. The pydantic-ai `web_fetch` builtin returns a Python-repr `{url,title,content}` dict —
 *  we parse it and render just the readable page text (JS/CSS boilerplate stripped) instead of the
 *  raw repr blob. When a real page screenshot is available, it's shown (scrollable) instead. */
export function FetchUrlResult({
  url,
  content,
  screenshot,
}: {
  url: string;
  content: string;
  screenshot?: string;
}) {
  // The result may be a Python-repr/JSON `{url,title,content}` dict, or already plain page text.
  const page = parseFetchedPage(content);
  const sourceUrl = page?.url || url;
  const title = page?.title?.trim() || "";
  const body = cleanPageText(page ? page.content : content);

  let host = sourceUrl;
  try {
    host = new URL(sourceUrl).hostname.replace(/^www\./, "");
  } catch {
    // keep the raw url as the label
  }
  return (
    <div className="space-y-2.5">
      <a
        href={sourceUrl}
        target="_blank"
        rel="noreferrer noopener"
        className="group border-border/60 bg-muted/40 hover:border-brand/50 flex items-center gap-2.5 rounded-lg border p-2.5 transition-colors"
      >
        <span className="border-border/60 bg-background flex h-8 w-8 shrink-0 items-center justify-center rounded-md border">
          <Globe className="text-foreground/60 h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="text-foreground block truncate text-sm font-medium">{title || host}</span>
          <span className="text-foreground/45 block truncate text-xs">{sourceUrl}</span>
        </span>
        <ExternalLink className="text-foreground/40 group-hover:text-brand h-4 w-4 shrink-0" />
      </a>
      {screenshot ? (
        <div className="border-border/60 overflow-hidden rounded-lg border">
          <div className="text-foreground/45 border-border/60 flex items-center gap-2 border-b px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
            <span>{host}</span>
            <span>·</span>
            <span>page snapshot</span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={screenshot} alt={host} className="block w-full select-none" draggable={false} />
          </div>
        </div>
      ) : body ? (
        <div className="border-border/60 overflow-hidden rounded-lg border">
          <div className="text-foreground/45 border-border/60 flex items-center gap-2 border-b px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
            <span>{host}</span>
            <span>·</span>
            <span>{body.length.toLocaleString()} chars read</span>
          </div>
          <div className="max-h-80 overflow-y-auto p-3">
            <div className="prose-sm max-w-none text-sm">
              <MarkdownContent content={body} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
