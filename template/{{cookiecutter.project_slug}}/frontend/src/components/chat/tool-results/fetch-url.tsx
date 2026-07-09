"use client";
import { ExternalLink, Globe } from "lucide-react";
import { MarkdownContent } from "../markdown-content";

/** Renders a `fetch_url` result as a page card: clickable source link + the fetched content. */
export function FetchUrlResult({ url, content }: { url: string; content: string }) {
  let host = url;
  try {
    host = new URL(url).hostname.replace(/^www\./, "");
  } catch {
    // keep the raw url as the label
  }
  return (
    <div className="space-y-2.5">
      <a
        href={url}
        target="_blank"
        rel="noreferrer noopener"
        className="group border-border/60 bg-muted/40 hover:border-brand/50 flex items-center gap-2.5 rounded-lg border p-2.5 transition-colors"
      >
        <span className="border-border/60 bg-background flex h-8 w-8 shrink-0 items-center justify-center rounded-md border">
          <Globe className="text-foreground/60 h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="text-foreground block truncate text-sm font-medium">{host}</span>
          <span className="text-foreground/45 block truncate text-xs">{url}</span>
        </span>
        <ExternalLink className="text-foreground/40 group-hover:text-brand h-4 w-4 shrink-0" />
      </a>
      {content ? (
        <div className="border-border/60 overflow-hidden rounded-lg border">
          <div className="text-foreground/45 border-border/60 flex items-center gap-2 border-b px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
            <span>{host}</span>
            <span>·</span>
            <span>{content.length.toLocaleString()} chars fetched</span>
          </div>
          <div className="max-h-80 overflow-y-auto p-3">
            <div className="prose-sm max-w-none text-sm">
              <MarkdownContent content={content} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
