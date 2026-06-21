"use client";
import { Globe, Link } from "lucide-react";

interface WebHit {
  title: string;
  url: string;
  content: string;
  score?: number | null;
}

export interface WebSearchPayload {
  query: string;
  results: WebHit[];
}

/** Parse a structured `web_search` tool result, or null if it isn't one
 *  (error string / legacy text → caller falls back to the default renderer). */
export function parseWebSearch(result: string): WebSearchPayload | null {
  try {
    const p = JSON.parse(result);
    if (p && typeof p === "object" && p.kind === "web_search" && Array.isArray(p.results)) {
      return { query: String(p.query ?? ""), results: p.results as WebHit[] };
    }
  } catch {
    /* not JSON — fall back to the raw renderer */
  }
  return null;
}

function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function WebSearchResults({ data }: { data: WebSearchPayload }) {
  if (data.results.length === 0) {
    return (
      <div className="text-muted-foreground flex items-center gap-2 py-2 text-sm">
        <Globe className="h-4 w-4" />
        No web results found
      </div>
    );
  }

  return (
    <div className="space-y-3 py-1">
      <div className="text-foreground/55 flex items-center gap-2 font-mono text-[10px] tracking-wider uppercase">
        <Globe className="h-3 w-3" />
        <span>
          {data.results.length} web result{data.results.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="border-foreground/10 divide-foreground/8 divide-y overflow-hidden rounded-xl border">
        {data.results.map((hit, i) => (
          <a
            key={`${hit.url}-${i}`}
            href={hit.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:bg-foreground/[0.03] block px-3 py-2.5 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="bg-foreground/8 text-foreground/65 inline-flex h-5 min-w-[1.5rem] shrink-0 items-center justify-center rounded px-1 font-mono text-[10px] tabular-nums">
                {i + 1}
              </span>
              <p className="text-foreground truncate text-xs font-medium">{hit.title}</p>
            </div>
            <div className="text-primary mt-1 flex items-center gap-1 truncate pl-[calc(1.5rem+0.5rem)] text-[10px]">
              <Link className="h-2.5 w-2.5 shrink-0" />
              {domainOf(hit.url)}
            </div>
            {hit.content && (
              <p className="text-foreground/55 mt-1 line-clamp-2 pl-[calc(1.5rem+0.5rem)] text-[11px] leading-relaxed">
                {hit.content}
              </p>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
