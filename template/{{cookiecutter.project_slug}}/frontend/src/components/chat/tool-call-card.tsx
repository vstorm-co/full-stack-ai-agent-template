"use client";

{%- if cookiecutter.enable_charts %}
import { useEffect, useMemo, useState, type MouseEvent } from "react";
{%- elif cookiecutter.enable_antv_charts %}
import { useEffect, useState, type MouseEvent } from "react";
{%- else %}
import { useState, type MouseEvent } from "react";
{%- endif %}
import { Card, CardContent, Button } from "@/components/ui";
import type { ToolCall } from "@/types";
import {
  Wrench,
  Clock,
  Calendar,
  FileText,
  Search,
  Globe,
  Link,
  ChevronDown,
  ChevronUp,
  Code2,
  MessageCircleQuestion,
{%- if cookiecutter.enable_charts or cookiecutter.enable_antv_charts %}
  BarChart3,
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
  MapPin,
{%- endif %}
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CopyButton } from "./copy-button";
{%- if cookiecutter.enable_charts %}
import { ChartMessage, parseChartResult } from "./chart-message";
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
import { MapMessage, parseMapResult } from "./map-message";
{%- endif %}

interface ToolCallCardProps {
  toolCall: ToolCall;
}

// --- Specialized renderers ---

function DateTimeResult({ result }: { result: string }) {
  // Parse "Current date: YYYY-MM-DD, Current time: HH:MM:SS"
  const dateMatch = result.match(/Current date:\s*(\d{4}-\d{2}-\d{2})/);
  const timeMatch = result.match(/Current time:\s*(\d{2}:\d{2}:\d{2})/);

  return (
    <div className="flex items-center gap-4 py-2">
      {dateMatch && (
        <div className="flex items-center gap-2">
          <Calendar className="text-primary h-5 w-5" />
          <div>
            <p className="text-muted-foreground text-xs">Date</p>
            <p className="text-sm font-semibold">{dateMatch[1]}</p>
          </div>
        </div>
      )}
      {timeMatch && (
        <div className="flex items-center gap-2">
          <Clock className="text-primary h-5 w-5" />
          <div>
            <p className="text-muted-foreground text-xs">Time</p>
            <p className="text-sm font-semibold">{timeMatch[1]}</p>
          </div>
        </div>
      )}
      {!dateMatch && !timeMatch && <p className="text-sm">{result}</p>}
    </div>
  );
}

interface RAGResultItem {
  index: number;
  source: string;
  page?: string;
  chunk?: string;
  collection?: string;
  score: string;
  content: string;
}

function parseRAGResults(result: string): RAGResultItem[] {
  const items: RAGResultItem[] = [];
  // Match: [1] Source: filename, page X, chunk Y [collection] (score: 0.xxx)\ncontent
  const pattern =
    /\[(\d+)\]\s*Source:\s*([^,\n]+?)(?:,\s*page\s*(\d+))?(?:,\s*chunk\s*(\d+))?(?:\s*\[([^\]]+)\])?\s*\(score:\s*([\d.]+)\)\n([\s\S]*?)(?=\n\[\d+\]|$)/g;
  let match;
  while ((match = pattern.exec(result)) !== null) {
    items.push({
      index: parseInt(match[1] ?? "0"),
      source: (match[2] ?? "").trim(),
      page: match[3],
      chunk: match[4],
      collection: match[5],
      score: match[6] ?? "",
      content: (match[7] ?? "").trim(),
    });
  }
  return items;
}

function RAGSearchResults({ result }: { result: string }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const items = parseRAGResults(result);

  if (items.length === 0) {
    if (result.includes("No relevant documents")) {
      return (
        <div className="text-muted-foreground flex items-center gap-2 py-2 text-sm">
          <Search className="h-4 w-4" />
          No relevant documents found
        </div>
      );
    }
    return null; // fallback to default renderer
  }

  // Group chunks by source filename so the same file doesn't render as N
  // duplicate cards. Preserve insertion order so the indices stay readable.
  const grouped = items.reduce<Map<string, RAGResultItem[]>>((acc, item) => {
    const key = item.source || "Unknown";
    const list = acc.get(key) ?? [];
    list.push(item);
    acc.set(key, list);
    return acc;
  }, new Map());
  const sourceCount = grouped.size;

  return (
    <div className="space-y-3 py-1">
      <div className="text-foreground/55 flex items-center gap-2 font-mono text-[10px] tracking-wider uppercase">
        <Search className="h-3 w-3" />
        <span>
          {items.length} chunk{items.length !== 1 ? "s" : ""}
        </span>
        <span>·</span>
        <span>
          {sourceCount} source{sourceCount !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="border-foreground/10 divide-foreground/8 overflow-hidden rounded-xl border divide-y">
        {Array.from(grouped.entries()).map(([source, chunks]) => (
          <RAGSourceGroup
            key={source}
            source={source}
            chunks={chunks}
            expandedIdx={expandedIdx}
            onToggle={(idx) => setExpandedIdx(expandedIdx === idx ? null : idx)}
          />
        ))}
      </div>
    </div>
  );
}

function RAGSourceGroup({
  source,
  chunks,
  expandedIdx,
  onToggle,
}: {
  source: string;
  chunks: RAGResultItem[];
  expandedIdx: number | null;
  onToggle: (idx: number) => void;
}) {
  const collection = chunks[0]?.collection;
  const bestScore = Math.max(...chunks.map((c) => parseFloat(c.score) || 0));
  return (
    <div>
      {/* Source header */}
      <div className="bg-foreground/[0.02] flex items-center gap-2 px-3 py-2">
        <FileText className="text-foreground/55 h-3.5 w-3.5 shrink-0" />
        <span className="text-foreground truncate text-xs font-medium" title={source}>
          {source}
        </span>
        <span className="text-foreground/45 ml-auto font-mono text-[10px] tracking-wider uppercase">
          {chunks.length} chunk{chunks.length !== 1 ? "s" : ""}
        </span>
        <ScoreDot score={bestScore} />
        {collection && (
          <span
            className="border-foreground/15 text-foreground/55 hidden shrink-0 rounded-full border px-1.5 py-0.5 font-mono text-[9px] tracking-wider uppercase sm:inline"
            title={`Collection: ${collection}`}
          >
            {collection}
          </span>
        )}
      </div>
      {/* Chunks */}
      <ul>
        {chunks.map((chunk) => {
          const isOpen = expandedIdx === chunk.index;
          return (
            <li key={chunk.index} className="border-foreground/8 border-t first:border-t-0">
              <button
                type="button"
                onClick={() => onToggle(chunk.index)}
                className="hover:bg-foreground/[0.02] flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors"
              >
                <span className="bg-foreground/8 text-foreground/65 mt-0.5 inline-flex h-5 min-w-[1.5rem] shrink-0 items-center justify-center rounded px-1 font-mono text-[10px] tabular-nums">
                  {chunk.index}
                </span>
                <div className="min-w-0 flex-1">
                  <p
                    className={cn(
                      "text-foreground/80 text-xs leading-relaxed",
                      !isOpen && "line-clamp-2",
                    )}
                  >
                    {chunk.content}
                  </p>
                  {(chunk.page || chunk.chunk) && (
                    <div className="text-foreground/45 mt-1 flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase">
                      {chunk.page && <span>p.{chunk.page}</span>}
                      {chunk.chunk && (
                        <>
                          {chunk.page && <span>·</span>}
                          <span>chunk {chunk.chunk}</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-0.5 flex shrink-0 items-center gap-1.5">
                  <span className="text-foreground/55 font-mono text-[10px] tabular-nums">
                    {parseFloat(chunk.score).toFixed(2)}
                  </span>
                  <ScoreDot score={parseFloat(chunk.score) || 0} />
                  <ChevronDown
                    className={cn(
                      "text-foreground/40 h-3.5 w-3.5 transition-transform",
                      isOpen && "rotate-180",
                    )}
                  />
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Tiny dot indicating chunk relevance — neutral palette, no warning colors. */
function ScoreDot({ score }: { score: number }) {
  // Map score to brand-tone opacity instead of red/yellow/green so the UI
  // reads as a quality signal, not an alert.
  const tone =
    score >= 0.7
      ? "bg-foreground"
      : score >= 0.4
        ? "bg-foreground/55"
        : "bg-foreground/25";
  return (
    <span
      className={cn("h-1.5 w-1.5 shrink-0 rounded-full", tone)}
      title={`Relevance: ${score.toFixed(2)}`}
    />
  );
}

interface WebHit {
  title: string;
  url: string;
  content: string;
  score?: number | null;
}

interface WebSearchPayload {
  query: string;
  results: WebHit[];
}

/** Parse a structured `web_search` tool result, or null if it isn't one
 *  (error string / legacy text → caller falls back to the default renderer). */
function parseWebSearch(result: string): WebSearchPayload | null {
  try {
    const p = JSON.parse(result);
    if (
      p &&
      typeof p === "object" &&
      p.kind === "web_search" &&
      Array.isArray(p.results)
    ) {
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

function WebSearchResults({ data }: { data: WebSearchPayload }) {
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

      <div className="border-foreground/10 divide-foreground/8 overflow-hidden rounded-xl border divide-y">
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

// --- Helpers ---

/** Pretty-print tool args. Handles three shapes:
 *  - object → JSON.stringify with indent
 *  - JSON-string (e.g. raw streaming payload) → parse then pretty-print
 *  - plain non-JSON string → return as-is
 */
function formatArgs(args: unknown): string {
  if (args === null || args === undefined) return "";
  if (typeof args === "string") {
    try {
      const parsed = JSON.parse(args);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return args;
    }
  }
  return JSON.stringify(args, null, 2);
}

function isEmptyArgs(args: unknown): boolean {
  if (args === null || args === undefined) return true;
  if (typeof args === "string") return args.trim() === "" || args.trim() === "{}";
  if (typeof args === "object") return Object.keys(args).length === 0;
  return false;
}

/** Raw view: arguments + the exact tool output, monospace, unparsed. */
function RawToolView({
  toolCall,
  resultText,
}: {
  toolCall: ToolCall;
  resultText: string;
}) {
  return (
    <div className="space-y-3">
      {isEmptyArgs(toolCall.args) ? (
        <p className="text-muted-foreground text-xs italic">No arguments</p>
      ) : (
        <div className="group relative">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
              Arguments
            </p>
            <CopyButton
              text={formatArgs(toolCall.args)}
              className="opacity-0 group-hover:opacity-100"
            />
          </div>
          <pre className="border-foreground/10 bg-background/60 scrollbar-thin overflow-x-auto rounded-lg border p-2.5 font-mono text-[11px] leading-relaxed">
            {formatArgs(toolCall.args)}
          </pre>
        </div>
      )}
      {toolCall.result !== undefined && resultText !== "" && (
        <div className="group relative">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
              Result
            </p>
            <CopyButton text={resultText} className="opacity-0 group-hover:opacity-100" />
          </div>
          <pre className="border-foreground/10 bg-background/60 max-h-72 scrollbar-thin overflow-x-auto overflow-y-auto rounded-lg border p-2.5 font-mono text-[11px] leading-relaxed break-words whitespace-pre-wrap">
            {resultText}
          </pre>
        </div>
      )}
    </div>
  );
}

/** Default formatted view for any tool without a specialized renderer.
 *  Pretty-prints JSON output, otherwise shows readable wrapped text — so a
 *  newly added backend tool renders sensibly with no frontend changes. */
function GenericToolResult({
  toolCall,
  resultText,
}: {
  toolCall: ToolCall;
  resultText: string;
}) {
  let prettyJson: string | null = null;
  try {
    const parsed = JSON.parse(resultText);
    if (parsed && typeof parsed === "object") {
      prettyJson = JSON.stringify(parsed, null, 2);
    }
  } catch {
    /* not JSON — render as text */
  }

  if (toolCall.status !== "completed" && !resultText) {
    return (
      <p className="text-muted-foreground py-2 text-xs italic">
        {toolCall.status === "error" ? "Tool failed." : "Running…"}
      </p>
    );
  }

  return (
    <div className="space-y-3 py-1">
      {!isEmptyArgs(toolCall.args) && (
        <div className="group relative">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
              Arguments
            </p>
            <CopyButton
              text={formatArgs(toolCall.args)}
              className="opacity-0 group-hover:opacity-100"
            />
          </div>
          <pre className="border-foreground/10 bg-background/60 scrollbar-thin overflow-x-auto rounded-lg border p-2.5 font-mono text-[11px] leading-relaxed">
            {formatArgs(toolCall.args)}
          </pre>
        </div>
      )}
      {resultText &&
        (prettyJson ? (
          <pre className="border-foreground/10 bg-background/60 max-h-80 scrollbar-thin overflow-x-auto overflow-y-auto rounded-lg border p-2.5 font-mono text-[11px] leading-relaxed">
            {prettyJson}
          </pre>
        ) : (
          <p className="text-foreground/80 max-h-80 overflow-y-auto text-[13px] leading-relaxed break-words whitespace-pre-wrap">
            {resultText}
          </p>
        ))}
    </div>
  );
}

{%- if cookiecutter.enable_antv_charts %}
/** Extract a chart image URL from an AntV `generate_*` tool result.
 *  AntV mcp-server-chart tools render server-side and return the image URL —
 *  usually a bare URL string, sometimes wrapped in JSON ({url|resultObj|...}).
 *  Returns null when no http(s) URL is present (caller falls back to raw text). */
function parseAntvImageUrl(result: string): string | null {
  const trimmed = result.trim();
  if (/^https?:\/\/\S+$/.test(trimmed)) return trimmed;
  try {
    const p = JSON.parse(trimmed);
    const candidate =
      typeof p === "string" ? p : (p?.url ?? p?.resultObj ?? p?.image ?? p?.content);
    if (typeof candidate === "string" && /^https?:\/\//.test(candidate.trim())) {
      return candidate.trim();
    }
  } catch {
    /* not JSON — fall through to regex */
  }
  const match = trimmed.match(/https?:\/\/[^\s")']+/);
  return match ? match[0] : null;
}

/** "generate_mind_map" -> "Mind Map", "generate_line_chart" -> "Line Chart". */
function antvToolLabel(name: string): string {
  return name
    .replace(/^generate_/, "")
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
{%- endif %}

{%- if cookiecutter.enable_skills %}
/** "market_data" -> "Market Data", "fire" -> "Fire". */
function formatSkillName(name: string): string {
  return name
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Extract the description text from a `load_skill` XML result.
 *  The library returns <skill><name>…</name><description>…</description>…</skill>. */
function parseLoadSkillResult(result: string): { description: string } | null {
  const m = result.match(/<description>([\s\S]*?)<\/description>/);
  if (!m?.[1]) return null;
  return { description: m[1].trim() };
}

/** Clean card for a loaded skill — just the description, no raw XML. */
function LoadSkillResult({ resultText, status }: { resultText: string; status: string }) {
  if (!resultText || status !== "completed") {
    return (
      <p className="text-muted-foreground py-2 text-xs italic">
        {status === "error" ? "Failed to load skill." : "Loading…"}
      </p>
    );
  }
  const parsed = parseLoadSkillResult(resultText);
  if (!parsed) return null;

  return (
    <p className="text-foreground/75 py-1 text-[13px] leading-relaxed">{parsed.description}</p>
  );
}
{%- endif %}

{%- if cookiecutter.enable_antv_charts %}
/** Render a server-rendered AntV diagram image with an "open full size" link. */
function AntvChartImage({ url, title }: { url: string; title: string }) {
  return (
    <div className="py-1">
      <a href={url} target="_blank" rel="noopener noreferrer" className="block">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt={title}
          loading="lazy"
          className="border-foreground/10 bg-background/60 max-h-[28rem] w-full rounded-xl border object-contain"
        />
      </a>
      <div className="text-primary mt-1.5 flex items-center gap-1 text-[10px]">
        <Link className="h-2.5 w-2.5 shrink-0" />
        <a href={url} target="_blank" rel="noopener noreferrer" className="truncate hover:underline">
          Open full size
        </a>
      </div>
    </div>
  );
}
{%- endif %}

/** Pull the question texts out of an `ask_user` tool's args (object or
 *  JSON-string). Handles the `questions` list. Returns [] when none found. */
function extractQuestions(args: unknown): string[] {
  let obj: unknown = args;
  if (typeof args === "string") {
    try {
      obj = JSON.parse(args);
    } catch {
      return [];
    }
  }
  if (obj && typeof obj === "object" && Array.isArray((obj as { questions?: unknown }).questions)) {
    return (obj as { questions: Array<{ question?: unknown }> }).questions.map((q) =>
      String(q?.question ?? ""),
    );
  }
  return [];
}

/** Transcript view of an `ask_user` turn. Once answered, the result is already a
 *  "Q: …/A: …" transcript, so render it as-is; while waiting, list the
 *  questions that were asked. */
function AskUserResult({ args, resultText }: { args: unknown; resultText: string }) {
  if (resultText) {
    return (
      <p className="text-foreground/85 py-1 text-sm leading-relaxed break-words whitespace-pre-wrap">
        {resultText}
      </p>
    );
  }
  const questions = extractQuestions(args);
  return (
    <div className="space-y-2.5 py-1">
      <div>
        <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
          {questions.length > 1 ? "Questions" : "Question"}
        </p>
        {questions.length > 0 ? (
          <ul className="text-foreground/85 mt-0.5 space-y-1 text-sm leading-relaxed">
            {questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground mt-0.5 text-xs italic">Waiting for the user…</p>
        )}
      </div>
      {questions.length > 0 && (
        <p className="text-muted-foreground text-xs italic">Waiting for the user…</p>
      )}
    </div>
  );
}

// --- Main component ---

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  // Collapsed by default — the bar acts as the toggle. `showRaw` swaps the
  // formatted view for args + raw output (the </> button). Charts are the
  // exception: they're only useful when visible, so expand them by default.
  const [expanded, setExpanded] = useState(
    toolCall.name === "ask_user" ||
{%- if cookiecutter.enable_charts and cookiecutter.enable_antv_charts %}
      (toolCall.status === "completed" &&
        ((toolCall.name === "create_chart_tool" && parseChartResult(toolCall.result) !== null) ||
          (toolCall.name === "create_map_tool" && parseMapResult(toolCall.result) !== null) ||
          (toolCall.name.startsWith("generate_") &&
            typeof toolCall.result === "string" &&
            parseAntvImageUrl(toolCall.result) !== null))),
{%- elif cookiecutter.enable_charts %}
      (toolCall.name === "create_chart_tool" &&
        toolCall.status === "completed" &&
        parseChartResult(toolCall.result) !== null),
{%- elif cookiecutter.enable_antv_charts %}
      (toolCall.status === "completed" &&
        ((toolCall.name === "create_map_tool" && parseMapResult(toolCall.result) !== null) ||
          (toolCall.name.startsWith("generate_") &&
            typeof toolCall.result === "string" &&
            parseAntvImageUrl(toolCall.result) !== null))),
{%- else %}
      false,
{%- endif %}
  );
  const [showRaw, setShowRaw] = useState(false);

  // Short input hint shown in the collapsed bar — the query for search
  // tools, the URL for fetch_url, etc. (any tool with a url/query arg).
  const urlArg = toolCall.args?.url;
  const queryArg = toolCall.args?.query;
  const inputHint =
    typeof urlArg === "string"
      ? urlArg
      : typeof queryArg === "string"
        ? queryArg
        : null;

  const resultText =
    toolCall.result !== undefined
      ? typeof toolCall.result === "string"
        ? toolCall.result
        : JSON.stringify(toolCall.result, null, 2)
      : "";

  // Check if we have a specialized renderer
  const isDateTime = toolCall.name === "get_current_datetime" && toolCall.status === "completed";
  const isRAGSearch =
    (toolCall.name === "search_knowledge_base" || toolCall.name === "search_documents") &&
    toolCall.status === "completed" &&
    typeof toolCall.result === "string";
  const webResults =
    (toolCall.name === "web_search_tool" || toolCall.name === "search_web") &&
    toolCall.status === "completed" &&
    typeof toolCall.result === "string"
      ? parseWebSearch(toolCall.result)
      : null;
  const isWebSearch = webResults !== null;
  const isAskUser = toolCall.name === "ask_user";
{%- if cookiecutter.enable_skills %}
  // pydantic-ai-skills tool names
  const isLoadSkill = toolCall.name === "load_skill";
  const isListSkills = toolCall.name === "list_skills";
  const loadedSkillName =
    isLoadSkill && typeof toolCall.args?.skill_name === "string"
      ? toolCall.args.skill_name
      : null;
{%- endif %}
{%- if cookiecutter.enable_charts %}
  // Memoize the parsed chart spec — `parseChartResult` does `JSON.parse` for
  // string results, returning a NEW object each call. Without this memo, every
  // streaming delta (text/thinking) re-renders ToolCallCard → new spec ref →
  // ChartMessage re-renders → Recharts re-layouts → ResponsiveContainer
  // briefly reports -1 dimensions → `RenderedTicksReporter` setState → React
  // detects too-many updates and bails with "Maximum update depth exceeded".
  const chartSpec = useMemo(
    () =>
      toolCall.name === "create_chart_tool" && toolCall.status === "completed"
        ? parseChartResult(toolCall.result)
        : null,
    [toolCall.name, toolCall.status, toolCall.result],
  );
  const isChart = chartSpec !== null;
  // A chart that finishes after this card mounted (live streaming) won't
  // have triggered the initial-state default — expand it on transition.
  useEffect(() => {
    if (isChart) setExpanded(true);
  }, [isChart]);
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
  const mapSpec =
    toolCall.name === "create_map_tool" && toolCall.status === "completed"
      ? parseMapResult(toolCall.result)
      : null;
  const isMap = mapSpec !== null;
  // AntV mcp-server-chart tools (generate_line_chart, generate_mind_map, ...)
  // return a server-rendered image URL.
  const antvImageUrl =
    toolCall.name.startsWith("generate_") &&
    toolCall.status === "completed" &&
    typeof toolCall.result === "string"
      ? parseAntvImageUrl(toolCall.result)
      : null;
  const isAntvChart = antvImageUrl !== null;
  // A map/image that finishes after this card mounted (live streaming) won't
  // have triggered the initial-state default — expand it on transition.
  useEffect(() => {
    if (isMap || isAntvChart) setExpanded(true);
  }, [isMap, isAntvChart]);
{%- endif %}

  const hasSpecialRenderer =
    isDateTime ||
    isRAGSearch ||
    isWebSearch ||
    isAskUser
{%- if cookiecutter.enable_charts %}
    || isChart
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
    || isMap
    || isAntvChart
{%- endif %}
  ;

  const friendlyName = isDateTime
    ? "Current Date & Time"
    : isRAGSearch
      ? "Knowledge Base Search"
      : isWebSearch
        ? "Web Search"
{%- if cookiecutter.enable_charts %}
        : isChart
          ? "Chart"
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
        : isMap
          ? "Map"
          : isAntvChart
            ? antvToolLabel(toolCall.name)
{%- endif %}
        : isAskUser
          ? "Question"
{%- if cookiecutter.enable_skills %}
          : isLoadSkill
            ? loadedSkillName
              ? formatSkillName(loadedSkillName)
              : "Load Skill"
            : isListSkills
              ? "Available Skills"
              : toolCall.name === "run_python"
                ? "Run Python"
                : toolCall.name;
{%- else %}
          : toolCall.name === "run_python"
            ? "Run Python"
            : toolCall.name;
{%- endif %}

  const ToolIcon = isDateTime
    ? Clock
    : isRAGSearch
      ? Search
      : isWebSearch
        ? Globe
{%- if cookiecutter.enable_charts %}
        : isChart
          ? BarChart3
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
        : isMap
          ? MapPin
          : isAntvChart
            ? BarChart3
{%- endif %}
        : isAskUser
          ? MessageCircleQuestion
          : Wrench;

  const toggleExpanded = () => {
    setExpanded((prev) => {
      const next = !prev;
      if (!next) setShowRaw(false);
      return next;
    });
  };

  const toggleRaw = (e: MouseEvent) => {
    e.stopPropagation();
    setShowRaw((r) => !r);
    setExpanded(true);
  };

  return (
    <Card className="bg-muted/50">
      <div
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={toggleExpanded}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleExpanded();
          }
        }}
        className="hover:bg-foreground/[0.03] flex w-full cursor-pointer items-center justify-between gap-2 px-3 py-2 text-left transition-colors"
      >
        <div className="flex min-w-0 items-center gap-2">
          <ToolIcon
            className={cn(
              "h-4 w-4 shrink-0",
              hasSpecialRenderer ? "text-primary" : "text-muted-foreground",
            )}
          />
          <span className="truncate text-sm font-medium">{friendlyName}</span>
          {inputHint ? (
            <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs italic">
              {inputHint}
            </span>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "text-muted-foreground hover:bg-foreground/10 hover:text-foreground h-6 w-6 transition-colors",
              showRaw && "text-primary",
            )}
            onClick={toggleRaw}
            title={showRaw ? "Show formatted view" : "Show arguments + raw output"}
          >
            <Code2 className="h-3.5 w-3.5" />
          </Button>
          {expanded ? (
            <ChevronUp className="text-muted-foreground h-4 w-4" />
          ) : (
            <ChevronDown className="text-muted-foreground h-4 w-4" />
          )}
        </div>
      </div>

      {expanded && (
        <CardContent className="px-3 pt-0 pb-3">
          {showRaw ? (
            <RawToolView toolCall={toolCall} resultText={resultText} />
          ) : toolCall.status === "completed" && isDateTime ? (
            <DateTimeResult result={resultText} />
          ) : toolCall.status === "completed" && isRAGSearch ? (
            <RAGSearchResults result={resultText} />
          ) : toolCall.status === "completed" && isWebSearch && webResults ? (
            <WebSearchResults data={webResults} />
{%- if cookiecutter.enable_charts %}
          ) : toolCall.status === "completed" && isChart && chartSpec ? (
            <ChartMessage spec={chartSpec} />
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
          ) : toolCall.status === "completed" && isMap && mapSpec ? (
            <MapMessage spec={mapSpec} />
          ) : toolCall.status === "completed" && isAntvChart && antvImageUrl ? (
            <AntvChartImage url={antvImageUrl} title={friendlyName} />
{%- endif %}
          ) : isAskUser ? (
            <AskUserResult args={toolCall.args} resultText={resultText} />
{%- if cookiecutter.enable_skills %}
          ) : isLoadSkill ? (
            <LoadSkillResult resultText={resultText} status={toolCall.status} />
          ) : isListSkills ? null : (
{%- else %}
          ) : (
{%- endif %}
            <GenericToolResult toolCall={toolCall} resultText={resultText} />
          )}
        </CardContent>
      )}
    </Card>
  );
}
