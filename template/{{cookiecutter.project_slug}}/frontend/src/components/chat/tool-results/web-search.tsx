"use client";
import { useEffect, useState } from "react";
import { ChevronDown, Globe, Link, Loader2 } from "lucide-react";
import { parsePyLiteral } from "@/lib/py-literal";
import { cn } from "@/lib/utils";

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
 *  (error string / legacy text → caller falls back to the default renderer).
 *
 *  Handles two shapes:
 *   1. The app's Tavily tool → JSON `{ kind: "web_search", query, results: [{title,url,content}] }`.
 *   2. The pydantic-ai `duckduckgo_search` builtin → a *Python-repr* string
 *      `[{'title': …, 'href': …, 'body': …}]` (single-quoted keys, mixed quotes, True/False/None),
 *      which JSON.parse can't read. */
export function parseWebSearch(result: string): WebSearchPayload | null {
  try {
    const p = JSON.parse(result);
    if (p && typeof p === "object" && p.kind === "web_search" && Array.isArray(p.results)) {
      return { query: String(p.query ?? ""), results: p.results as WebHit[] };
    }
  } catch {
    /* not JSON — try the DuckDuckGo Python-repr shape below */
  }
  return parseDuckDuckGo(result);
}

/** DuckDuckGo builtin: a Python-repr list of `{title, href, body}` dicts. */
function parseDuckDuckGo(result: string): WebSearchPayload | null {
  if (!result.trimStart().startsWith("[")) return null;
  const parsed = parsePyLiteral(result.trim());
  if (!Array.isArray(parsed)) return null;
  const results: WebHit[] = [];
  for (const item of parsed) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    const o = item as Record<string, unknown>;
    const title = typeof o.title === "string" ? o.title : "";
    const url = typeof o.href === "string" ? o.href : typeof o.url === "string" ? o.url : "";
    const content = typeof o.body === "string" ? o.body : typeof o.content === "string" ? o.content : "";
    // Skip tracking-redirect junk (relative /clev?… links) — keep only real pages.
    if (!/^https?:\/\//.test(url)) continue;
    results.push({ title: title || url, url, content });
  }
  return results.length ? { query: "", results } : null;
}

function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function WebSearchResults({
  data,
  detailed = false,
  busy = false,
  activeIndex = null,
}: {
  data: WebSearchPayload;
  /** Deep-dive view (computer panel): show relevance scores and the full snippet. */
  detailed?: boolean;
  /** Live browsing: force the list open and walk a spinner down the pages the agent is opening.
   *  Set by the demo chat while a browse turn streams, so the card isn't frozen when the
   *  computer panel is closed. */
  busy?: boolean;
  /** Page index to highlight, mirrored from the panel animation for true sync (panel open).
   *  `null` → no external clock, so the card self-cycles a spinner (panel closed / fast mode). */
  activeIndex?: number | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const PREVIEW_COUNT = 3;

  // While browsing, a spinner sits on the page currently being opened. When the panel drives the
  // index (activeIndex), mirror it for lockstep sync; otherwise self-cycle through the pages.
  const busyCount = Math.min(PREVIEW_COUNT, data.results.length);
  const [activeRow, setActiveRow] = useState(0);
  const synced = activeIndex != null;
  useEffect(() => {
    if (!busy || busyCount === 0 || synced) return; // externally synced → don't run our own clock
    setActiveRow(0);
    const id = setInterval(() => setActiveRow((r) => (r + 1) % busyCount), 733);
    return () => clearInterval(id);
  }, [busy, busyCount, synced]);
  const spinRow = synced ? Math.min(Math.max(activeIndex, 0), Math.max(0, busyCount - 1)) : activeRow;

  if (data.results.length === 0) {
    return (
      <div className="text-muted-foreground flex items-center gap-2 py-2 text-sm">
        <Globe className="h-4 w-4" />
        No web results found
      </div>
    );
  }

  const hasMore = data.results.length > PREVIEW_COUNT;
  // Browsing shows exactly the pages being opened; otherwise the usual first-N-then-collapse.
  const visible = busy
    ? data.results.slice(0, busyCount)
    : expanded
      ? data.results
      : data.results.slice(0, PREVIEW_COUNT);
  const rest = data.results.length - PREVIEW_COUNT;

  return (
    <div className="space-y-3 py-1">
      <div className="text-foreground/55 flex items-center gap-2 font-mono text-[10px] tracking-wider uppercase">
        <Globe className={cn("h-3 w-3", busy && "text-brand animate-pulse")} />
        <span>
          {data.results.length} web result{data.results.length !== 1 ? "s" : ""}
        </span>
        {detailed && data.query && (
          <span className="text-foreground/40 truncate normal-case">· “{data.query}”</span>
        )}
      </div>

      <div className="border-foreground/10 divide-foreground/8 divide-y overflow-hidden rounded-xl border">
        {visible.map((hit, i) => (
          <a
            key={`${hit.url}-${i}`}
            href={hit.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:bg-foreground/[0.03] block px-3 py-2.5 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="bg-foreground/8 text-foreground/65 inline-flex h-5 min-w-[1.5rem] shrink-0 items-center justify-center rounded px-1 font-mono text-[10px] tabular-nums">
                {busy && i === spinRow ? (
                  <Loader2 className="text-brand h-3 w-3 animate-spin" />
                ) : (
                  i + 1
                )}
              </span>
              <p className="text-foreground min-w-0 flex-1 truncate text-xs font-medium">{hit.title}</p>
              {detailed && typeof hit.score === "number" && (
                <span className="bg-brand/10 text-brand shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] tabular-nums">
                  {(hit.score * 100).toFixed(0)}%
                </span>
              )}
            </div>
            <div className="text-primary mt-1 flex items-center gap-1 truncate pl-[calc(1.5rem+0.5rem)] text-[10px]">
              <Link className="h-2.5 w-2.5 shrink-0" />
              {domainOf(hit.url)}
            </div>
            {hit.content && (
              <p
                className={cn(
                  "text-foreground/55 mt-1 pl-[calc(1.5rem+0.5rem)] text-[11px] leading-relaxed",
                  detailed ? "whitespace-pre-wrap" : "line-clamp-2",
                )}
              >
                {hit.content}
              </p>
            )}
          </a>
        ))}
      </div>

      {busy ? (
        <div className="text-foreground/55 flex w-full items-center justify-center gap-1.5 py-1 text-[11px] font-medium">
          <Loader2 className="text-brand h-3.5 w-3.5 animate-spin" />
          Opening pages…
        </div>
      ) : (
        hasMore && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="border-foreground/15 text-foreground/60 hover:text-foreground hover:border-foreground/30 flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed py-1.5 text-[11px] font-medium transition-colors"
          >
            <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
            {expanded ? "Show fewer results" : `+${rest} more result${rest !== 1 ? "s" : ""}`}
          </button>
        )
      )}
    </div>
  );
}
