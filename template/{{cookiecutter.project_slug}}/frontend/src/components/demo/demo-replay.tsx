{% raw %}"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  BarChart3,
  BookOpen,
  Bot,
  Brain,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Code2,
  ExternalLink,
  FastForward,
  GitBranch,
  Globe,
  Loader2,
  MessageSquare,
  Monitor,
  Pause,
  Play,
  Radio,
  RotateCcw,
  SkipBack,
  SkipForward,
  Telescope,
  Workflow,
  Wrench,
  X,
} from "lucide-react";
import { BrowseActivityProvider } from "@/components/chat/browse-activity";
import { MarkdownContent } from "@/components/chat/markdown-content";
import { MessageItem } from "@/components/chat/message-item";
{% endraw %}{%- if cookiecutter.enable_deep_research %}{% raw %}
import { ResearchReplayBlock } from "@/components/chat/research-replay-block";
{% endraw %}{%- endif %}{% raw %}
import { ToolCallCard } from "@/components/chat/tool-call-card";
import {
  BrowserStage,
  BrowserSession,
  browseSessionDurationMs,
  type FollowUp,
} from "@/components/chat/tool-results/browser-stage";
import { RawToolView } from "@/components/chat/tool-results/generic";
import { parseWebSearch, type WebSearchPayload } from "@/components/chat/tool-results/web-search";
import { isFetchTool, isWebSearchTool } from "@/lib/agent-tools";
import { cleanPageText, parseFetchedPage } from "@/lib/py-literal";
import { useConversationReplay } from "@/hooks/use-conversation-replay";
import { conversationMessagesToChatMessages, type RawMessage } from "@/lib/conversation-to-chat";
import { formatSql } from "@/lib/sql-format";
import { cn } from "@/lib/utils";
import type { ChatMessage, ResearchReplay, ToolCall } from "@/types";

interface DemoReplayProps {
  rawMessages: RawMessage[];
}

type StepStatus = "done" | "active" | "pending";
type StepKind = "tool" | "thinking" | "text" | "research";
interface TurnStep {
  label: string;
  kind: StepKind;
  tool?: ToolCall;
  content?: string;
  research?: ResearchReplay;
}
interface ReplayStep extends TurnStep {
  key: string;
  status: StepStatus;
}
// A whole web-browsing sub-sequence collapsed into one frame: the single search plus the
// pages the agent then opened. Rendered as one continuous BrowserSession animation.
interface BrowseData {
  query: string;
  results: WebSearchPayload["results"];
  visits: FollowUp[];
}

// A single frame in the "Agent's computer" timeline — one reasoning/tool/response step.
interface Frame extends TurnStep {
  key: string;
  idx: number;
  promptKey: string;
  promptTitle: string;
  // Present when this frame is a collapsed browse sequence (1 search + N page visits).
  browse?: BrowseData;
  // The original per-tool frame keys folded into this browse frame (so dock steps still map here).
  mergedKeys?: string[];
}

const playBtnRingStyle = { inset: "-10px", borderRadius: "9999px" };
const playBtnGlowStyle = { boxShadow: "0 0 60px oklch(from var(--color-brand) l c h / 0.5)" };
const progressGlowStyle = { boxShadow: "0 0 12px oklch(from var(--color-brand) l c h / 0.55)" };
const scrollbarStyle: React.CSSProperties = {
  scrollbarWidth: "thin",
  scrollbarColor: "var(--color-border) transparent",
};

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);

// Human-readable label for the tool currently being replayed — drives the live dock status.
const TOOL_LABELS: Record<string, string> = {
  load_skill: "Loading skill",
  run_python: "Running Python",
  create_chart: "Creating a chart",
  create_chart_tool: "Creating a chart",
  map_tool: "Building a map",
  create_map: "Building a map",
  create_map_tool: "Building a map",
  web_search_tool: "Searching the web",
  search_web: "Searching the web",
  duckduckgo_search: "Searching the web",
  search_knowledge_base: "Searching the knowledge base",
  search_documents: "Searching documents",
  fetch_url: "Opening a page",
  fetch: "Opening a page",
  web_fetch: "Opening a page",
  ask_user: "Asking a question",
  ask_user_tool: "Asking a question",
};

const humanizeTool = (name: string) =>
  name
    .replace(/_/g, " ")
    .replace(/\btool\b/gi, "")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase()) || "Working";

// Icon representing a frame inside the "Agent's computer" thumbnail / scrubber.
const frameIconFor = (frame?: { kind: StepKind; tool?: ToolCall } | null) => {
  if (!frame) return Monitor;
  if (frame.kind === "thinking") return Brain;
  if (frame.kind === "text") return MessageSquare;
  if (frame.kind === "research") return Telescope;
  const name = frame.tool?.name;
  if (!name) return Wrench;
  if (name === "run_python") return Code2;
  if (name.startsWith("create_chart")) return BarChart3;
  if (name === "load_skill" || name === "list_skills") return BookOpen;
  if (name.includes("search") || isFetchTool(name)) return Globe;
  return Wrench;
};

// The ordered steps an assistant turn takes — reasoning, tool calls and the response, in order.
// Read from the SOURCE message so the list is known up-front and fills in as replay progresses.
function turnSteps(message: ChatMessage): TurnStep[] {
  const out: TurnStep[] = [];
  const toolStep = (tc: ToolCall): TurnStep => ({
    label: TOOL_LABELS[tc.name] ?? humanizeTool(tc.name),
    kind: "tool",
    tool: tc,
  });
  if (message.parts && message.parts.length > 0) {
    for (const p of message.parts) {
      if (p.type === "tool" && p.toolCall) out.push(toolStep(p.toolCall));
      else if (p.type === "text")
        out.push({ label: "Writing the response", kind: "text", content: p.content ?? message.content ?? "" });
      else if (p.type === "thinking") out.push({ label: "Thinking", kind: "thinking", content: p.content ?? "" });
      else if (p.type === "research") out.push({ label: "Researching", kind: "research", research: p.research });
    }
    return out;
  }
  if (message.thinking) out.push({ label: "Thinking", kind: "thinking", content: message.thinking });
  for (const tc of message.toolCalls ?? []) out.push(toolStep(tc));
  if (message.content) out.push({ label: "Writing the response", kind: "text", content: message.content });
  return out;
}

// mm:ss for the per-task live timer.
const formatElapsed = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

/** One row in a step timeline: status icon + connector line + label, with an optional live timer.
 * When `onSelect` is provided the row is a button that opens that step in the computer panel. */
function StepItem({
  label,
  status,
  isLast,
  timer,
  onSelect,
  selected,
}: {
  label: string;
  status: StepStatus;
  isLast: boolean;
  timer?: string | null;
  onSelect?: () => void;
  selected?: boolean;
}) {
  const icon = (
    <span className="relative z-10 flex h-[18px] w-[18px] shrink-0 items-center justify-center">
      {status === "done" ? (
        <span className="bg-brand flex h-[18px] w-[18px] items-center justify-center rounded-full">
          <Check className="h-3 w-3 text-white" strokeWidth={3} />
        </span>
      ) : status === "active" ? (
        <Loader2 className="text-brand h-[18px] w-[18px] animate-spin" />
      ) : (
        <span className="border-border bg-background h-3.5 w-3.5 rounded-full border-2" />
      )}
    </span>
  );
  const text = (
    <span
      className={cn(
        "min-w-0 flex-1 truncate text-sm leading-[18px]",
        status === "pending"
          ? "text-foreground/40"
          : status === "active"
            ? "text-foreground font-medium"
            : "text-foreground/60",
      )}
    >
      {label}
    </span>
  );
  const timerEl = timer ? (
    <span className="text-brand/80 shrink-0 font-mono text-xs tabular-nums">{timer}</span>
  ) : null;
  return (
    <li className="step-reveal relative pb-3 last:pb-0">
      {!isLast && (
        <span
          className={cn(
            "absolute top-[18px] bottom-0 left-[9px] w-px",
            status === "done" ? "bg-brand/40" : "bg-border",
          )}
        />
      )}
      {onSelect ? (
        <button
          type="button"
          onClick={onSelect}
          className={cn(
            "relative z-10 flex w-full items-center gap-3 rounded-md py-0.5 text-left transition-colors",
            selected ? "bg-brand/10" : "hover:bg-muted/40",
          )}
        >
          {icon}
          {text}
          {timerEl}
        </button>
      ) : (
        <div className="flex items-center gap-3">
          {icon}
          {text}
          {timerEl}
        </div>
      )}
    </li>
  );
}

/** Small clickable "window" tile that opens the Agent's computer panel. */
function ToolThumb({ frame, onClick, live }: { frame: Frame | null; onClick: () => void; live: boolean }) {
  const Icon = frameIconFor(frame);
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Open agent's computer"
      title="Open agent's computer"
      className="group border-border/70 bg-muted/50 hover:border-brand/60 relative flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-lg border shadow-sm transition-colors"
    >
      <span className="bg-foreground/15 absolute top-1.5 left-1.5 h-1 w-1 rounded-full" />
      <span className="bg-foreground/10 absolute top-1.5 left-3 h-1 w-1 rounded-full" />
      <Icon className="text-foreground/55 group-hover:text-brand mt-1 h-4 w-4 transition-colors" />
      {live && <span className="bg-brand absolute top-1 right-1 h-1.5 w-1.5 animate-pulse rounded-full" />}
    </button>
  );
}

/** The agent's reasoning for one step. */
function ThinkingView({ content }: { content: string }) {
  return (
    <div className="border-border/60 bg-muted/30 rounded-lg border p-3">
      <p className="text-foreground/50 mb-2 flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase">
        <Brain className="h-3.5 w-3.5" /> Reasoning
      </p>
      <p className="text-foreground/70 font-mono text-[12px] leading-relaxed whitespace-pre-wrap">
        {content || "…"}
      </p>
    </div>
  );
}

/** The agent's written answer for one step. */
function ResponseView({ content }: { content: string }) {
  return (
    <div className="border-border/60 bg-card rounded-lg border p-3">
      <p className="text-foreground/50 mb-2 flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase">
        <MessageSquare className="h-3.5 w-3.5" /> Response
      </p>
      <div className="prose-sm max-w-none text-sm">
        <MarkdownContent content={content || "…"} />
      </div>
    </div>
  );
}

/** Collapsible "under the hood" section — the exact args in / raw result out. */
function RawIO({ tool, resultText }: { tool: ToolCall; resultText: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-border/50 rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="text-foreground/55 hover:text-foreground/85 flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium transition-colors"
      >
        <Code2 className="h-3.5 w-3.5 shrink-0" />
        <span className="flex-1">Raw input / output</span>
        <ChevronDown className={cn("h-3.5 w-3.5 shrink-0 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="border-border/50 border-t px-3 py-2.5">
          <RawToolView toolCall={tool} resultText={resultText} />
        </div>
      )}
    </div>
  );
}

// True when an assistant turn does any web searching — used to hold its answer until the
// browse animation finishes.
function turnHasBrowsing(message: ChatMessage): boolean {
  const names = message.parts?.length
    ? message.parts.map((p) => (p.type === "tool" ? p.toolCall?.name : undefined))
    : (message.toolCalls ?? []).map((t) => t.name);
  return names.some((n) => isWebSearchTool(n));
}

// In the chat stream, a browsing turn shows ONE "Web Search" card. The individual page fetches
// are folded into it — replayed as the browse animation in the computer panel and listed as the
// search's sources — so we drop the fetch_url/fetch cards here. Left in, only the first few baked
// visits show, which reads as "the agent opened just 3 pages" when it reviews the whole result set.
function stripBrowseFetches(message: ChatMessage): ChatMessage {
  if (message.role !== "assistant" || !turnHasBrowsing(message)) return message;
  if (message.parts?.length) {
    return { ...message, parts: message.parts.filter((p) => !(p.type === "tool" && isFetchTool(p.toolCall?.name))) };
  }
  if (message.toolCalls?.length) {
    return { ...message, toolCalls: message.toolCalls.filter((t) => !isFetchTool(t.name)) };
  }
  return message;
}

// The ordered tool calls of a turn (generation order) — from `parts` when present, else `toolCalls`.
function orderedTools(msg: ChatMessage | undefined): ToolCall[] {
  if (!msg) return [];
  const tools = msg.parts?.length
    ? msg.parts.filter((p) => p.type === "tool").map((p) => p.toolCall)
    : (msg.toolCalls ?? []);
  return tools.filter((t): t is ToolCall => Boolean(t));
}

// A fetch tool call → the page the agent opened (or null when it carries no URL).
function toolToVisit(t: ToolCall): FollowUp | null {
  if (!isFetchTool(t.name)) return null;
  const args = (t.args ?? {}) as Record<string, unknown>;
  const url = typeof args.url === "string" ? args.url : "";
  if (!url) return null;
  return {
    url,
    content: typeof t.result === "string" ? t.result : JSON.stringify(t.result ?? ""),
    screenshot: typeof args.screenshot === "string" ? args.screenshot : undefined,
  };
}

// The pages that belong to one web search's run: the consecutive fetches right after it (until any
// non-fetch step), taken from the FULL source message so the run is complete even mid-stream.
function runVisits(fullMsg: ChatMessage | undefined, searchToolId: string): FollowUp[] {
  const tools = orderedTools(fullMsg);
  const start = tools.findIndex((t) => t.id === searchToolId);
  if (start < 0) return [];
  const visits: FollowUp[] = [];
  for (let k = start + 1; k < tools.length; k += 1) {
    const v = toolToVisit(tools[k]!);
    if (!v) break; // a non-fetch step ends the run
    visits.push(v);
  }
  return visits;
}

// The first browse run of a turn: the first web search + only the pages fetched right after it.
// ONE window animates per turn — that first search — so replay pacing is sized to this run alone.
// Sizing to every search's pages would animate e.g. 5×3 = 15 pages and drag the demo.
function firstBrowseRun(msg: ChatMessage | undefined): { query: string; visits: FollowUp[] } | null {
  const tools = orderedTools(msg);
  const search = tools.find((t) => isWebSearchTool(t.name));
  if (!search) return null;
  const args = (search.args ?? {}) as Record<string, unknown>;
  const query = typeof args.query === "string" ? args.query : "";
  return { query, visits: runVisits(msg, search.id) };
}

// Collapse a web_search followed by its fetch visits into ONE browse frame, so the panel plays the
// whole "search → open each result → scan → back → next" as a single, sequential, watchable scene
// in one window — instead of N separate frames the view auto-scrolls between. Each browse frame
// takes ONLY its own search's consecutive fetches as visits (not every fetch in the turn): the first
// search animates its own pages, and any later search renders settled with its own — so 5 searches
// never animate all 15 pages.
function collapseBrowsing(frames: Frame[], fullMessages: ChatMessage[]): Frame[] {
  const out: Frame[] = [];
  for (let i = 0; i < frames.length; i += 1) {
    const f = frames[i];
    if (!f) continue;
    const t = f.tool;
    if (t && isWebSearchTool(t.name)) {
      const mergedKeys: string[] = [f.key];
      let j = i + 1;
      while (j < frames.length) {
        const fj = frames[j];
        const ft = fj?.tool;
        if (!ft || !isFetchTool(ft.name)) break;
        mergedKeys.push(fj.key);
        j += 1;
      }
      const resultText = typeof t.result === "string" ? t.result : JSON.stringify(t.result ?? "");
      const parsed = parseWebSearch(resultText);
      if (parsed) {
        const msgIndex = Number(f.key.split("-")[0]);
        const visits = runVisits(fullMessages[msgIndex], t.id);
        // DuckDuckGo results carry no query text — fall back to the tool call's args.query.
        const args = (t.args ?? {}) as Record<string, unknown>;
        const query = parsed.query || (typeof args.query === "string" ? args.query : "");
        out.push({
          ...f,
          label: visits.length ? "Browsing the web" : f.label,
          browse: { query, results: parsed.results, visits },
          mergedKeys,
          idx: out.length,
        });
        i = j - 1;
        continue;
      }
    }
    out.push({ ...f, idx: out.length });
  }
  return out;
}

// The computer panel goes deeper than the chat: richer web/research/fetch renderers, plus the
// raw tool I/O the chat hides. Text/thinking/research have no raw layer.
function FrameContent({
  frame,
  onBrowseProgress,
  browseInstant = false,
}: {
  frame: Frame;
  onBrowseProgress?: (visitIndex: number) => void;
  /** Render this browse scene in its finished end-state (no replay) — set for any browse that
   *  isn't the one currently in progress, so opening the panel late shows a completed search. */
  browseInstant?: boolean;
}) {
  if (frame.kind === "thinking") return <ThinkingView content={frame.content ?? ""} />;
  if (frame.kind === "text") return <ResponseView content={frame.content ?? ""} />;
{% endraw %}{%- if cookiecutter.enable_deep_research %}{% raw %}
  if (frame.kind === "research" && frame.research)
    return <ResearchReplayBlock research={frame.research} animate={false} detailed />;
{% endraw %}{%- endif %}{% raw %}

  const tool = frame.tool;
  if (!tool) return <div className="text-foreground/50 p-3 text-sm">Working…</div>;
  const resultText =
    typeof tool.result === "string" ? tool.result : JSON.stringify(tool.result ?? "", null, 2);
  // A baked page screenshot lives in args but must never be dumped into the Raw I/O blob.
  const screenshot = typeof (tool.args as Record<string, unknown> | undefined)?.screenshot === "string"
    ? ((tool.args as Record<string, unknown>).screenshot as string)
    : undefined;
  const rawTool = screenshot
    ? { ...tool, args: { ...(tool.args as Record<string, unknown>), screenshot: "[screenshot omitted]" } }
    : tool;

  // A collapsed browse sequence: one window plays search → visit each result → scan.
  if (frame.browse) {
    return (
      <div className="space-y-2">
        <BrowserSession
          query={frame.browse.query}
          results={frame.browse.results}
          visits={frame.browse.visits}
          onProgress={onBrowseProgress}
          instant={browseInstant}
        />
        <RawIO tool={rawTool} resultText={resultText} />
      </div>
    );
  }

  if (isWebSearchTool(tool.name)) {
    const data = parseWebSearch(resultText);
    if (data) {
      const query =
        data.query || (typeof tool.args?.query === "string" ? (tool.args.query as string) : "");
      return (
        <div className="space-y-2">
          <BrowserStage kind="search" query={query} results={data.results} />
          <RawIO tool={tool} resultText={resultText} />
        </div>
      );
    }
  }
  if (isFetchTool(tool.name) && typeof tool.args?.url === "string") {
    return (
      <div className="space-y-2">
        <BrowserStage kind="read" url={String(tool.args.url)} content={resultText} screenshot={screenshot} />
        <RawIO tool={rawTool} resultText={resultText} />
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <ToolCallCard key={frame.key} toolCall={tool} defaultExpanded />
      <RawIO tool={tool} resultText={resultText} />
    </div>
  );
}

// A short, concrete detail for a graph node — the skill name, page host, chart title, query…
function graphSubLabel(frame: Frame): string | null {
  const t = frame.tool;
  if (!t) return null;
  const a = (t.args ?? {}) as Record<string, unknown>;
  if (t.name === "load_skill" && typeof a.name === "string") return a.name;
  if (isFetchTool(t.name) && typeof a.url === "string") {
    try {
      return new URL(a.url).hostname.replace(/^www\./, "");
    } catch {
      return a.url;
    }
  }
  if (t.name.startsWith("create_chart") && typeof a.title === "string") return a.title;
  if (isWebSearchTool(t.name) && typeof a.query === "string") return a.query;
  if ((t.name === "ask_user" || t.name === "ask_user_tool") && typeof a.question === "string") return a.question;
  return null;
}

// A compact "what the agent did here" preview for a graph node: a type tag, an optional right-side
// metric chip, and a short body snippet (code / reasoning / result) echoing the tool's real I/O.
interface NodePreview {
  tag: string;
  meta?: string | null;
  body?: string | null;
  code?: boolean;
  /** Web-search / browse nodes render their pages as a numbered source list instead of a body.
   *  Each source can carry the baked page screenshot so the row expands into a scrollable snapshot. */
  sources?: { title: string; url: string; screenshot?: string }[];
}

// Bare hostname for a source row (no protocol / www / path).
function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// Strip Markdown syntax so a snippet reads as clean prose (no #, **, `code`, [links], bullets…).
function stripMarkdown(s: string): string {
  return s
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s{0,3}>\s?/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/~~([^~]+)~~/g, "$1")
    .replace(/^\s*\|.*$/gm, " ")
    .replace(/^-{3,}$/gm, " ");
}

// Clean prose snippet — markdown stripped, whitespace collapsed, clipped.
const clipText = (s: string, n = 180) => {
  const t = stripMarkdown(s).replace(/\s+/g, " ").trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
};

// Code snippet — indentation and line breaks preserved, capped to the first few lines.
const clipCode = (s: string, maxLines = 6) => {
  const lines = s.replace(/\s+$/, "").split("\n");
  const shown = lines.slice(0, maxLines).join("\n");
  return lines.length > maxLines ? `${shown}\n…` : shown;
};

/**
 * Pull the SQL query + row count out of a text-to-SQL tool call (e.g. `query_product_database`).
 * The query is authored in `args.sql`; the result JSON carries the row count, which lands under
 * `rows` for table results or `products` for product-card results. Falls back to a `sql`/`query`
 * field in the result when args carry no SQL. Returns null when no SQL is present.
 */
function sqlFromToolCall(
  args: Record<string, unknown>,
  result: string,
): { sql: string; rows: number | null } | null {
  let sql = typeof args.sql === "string" ? args.sql : null;
  let rows: number | null = null;
  try {
    const parsed = JSON.parse(result) as { sql?: unknown; query?: unknown; rows?: unknown; products?: unknown };
    if (!sql && typeof parsed.sql === "string") sql = parsed.sql;
    if (!sql && typeof parsed.query === "string") sql = parsed.query;
    if (Array.isArray(parsed.rows)) rows = parsed.rows.length;
    else if (Array.isArray(parsed.products)) rows = parsed.products.length;
  } catch {
    /* result is not JSON — fall back to args.sql alone */
  }
  return sql ? { sql, rows } : null;
}

function graphNodePreview(frame: Frame): NodePreview {
  if (frame.kind === "thinking") return { tag: "Reasoning", body: clipText(frame.content ?? "") };
  if (frame.kind === "text") return { tag: "Response", body: clipText(frame.content ?? "") };
  if (frame.kind === "research") {
    const steps = frame.research?.todos.length ?? 0;
    return { tag: "Deep research", meta: steps ? `${steps} steps` : null };
  }

  const t = frame.tool;
  if (!t) return { tag: "Tool" };
  const a = (t.args ?? {}) as Record<string, unknown>;
  const result = typeof t.result === "string" ? t.result : JSON.stringify(t.result ?? "");

  if (t.name === "run_python") {
    const code = typeof a.code === "string" ? a.code : "";
    return code ? { tag: "Python", body: clipCode(code), code: true } : { tag: "Python", body: clipText(result) };
  }
  if (t.name.startsWith("create_chart")) {
    const type = typeof a.chart_type === "string" ? a.chart_type : "chart";
    return { tag: "Chart", meta: type };
  }
  if (t.name === "load_skill") {
    const desc = /<description>([\s\S]*?)<\/description>/i.exec(result)?.[1];
    return { tag: "Skill", body: clipText(desc || result, 150) };
  }
  if (isWebSearchTool(t.name)) {
    const parsed = parseWebSearch(result);
    const results = frame.browse?.results ?? parsed?.results ?? [];
    const visits = frame.browse?.visits ?? [];
    const shotByUrl = new Map(visits.filter((v) => v.screenshot).map((v) => [v.url, v.screenshot]));
    if (results.length) {
      return {
        tag: "Web search",
        meta: `${results.length} results`,
        sources: results.map((r, i) => ({
          title: r.title,
          url: r.url,
          screenshot: shotByUrl.get(r.url) ?? visits[i]?.screenshot,
        })),
      };
    }
    return { tag: "Web search", body: clipText(result, 160) };
  }
  if (isFetchTool(t.name)) {
    const page = parseFetchedPage(result);
    const text = page ? cleanPageText(page.content) : result;
    return {
      tag: "Fetch",
      meta: text ? `${text.length.toLocaleString()} chars` : null,
      body: clipText(page?.title ? `${page.title}. ${text}` : text, 160),
    };
  }
  if (t.name === "ask_user" || t.name === "ask_user_tool") {
    return { tag: "Q&A", body: clipText(result, 200) };
  }
  const sqlResult = sqlFromToolCall(a, result);
  if (sqlResult) {
    return {
      tag: "SQL",
      meta: sqlResult.rows != null ? `${sqlResult.rows} rows` : null,
      body: clipCode(formatSql(sqlResult.sql)),
      code: true,
    };
  }
  return { tag: "Tool", body: clipText(result, 160) };
}

// Type-colored accents so the run graph reads at a glance (reasoning / response / research / tool).
type AccentKey = "reasoning" | "response" | "research" | "tool";
const NODE_ACCENT: Record<AccentKey, { chip: string; icon: string }> = {
  reasoning: { chip: "bg-amber-500/10 text-amber-600 dark:text-amber-400", icon: "text-amber-500" },
  response: { chip: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400", icon: "text-emerald-500" },
  research: { chip: "bg-violet-500/10 text-violet-600 dark:text-violet-400", icon: "text-violet-500" },
  tool: { chip: "bg-brand/10 text-brand", icon: "text-brand" },
};

const accentKeyFor = (kind: StepKind): AccentKey =>
  kind === "thinking" ? "reasoning" : kind === "text" ? "response" : kind === "research" ? "research" : "tool";

/** A single source row in a browse node — click to expand the scrollable page snapshot. */
function SourceRow({ index, source }: { index: number; source: { title: string; url: string; screenshot?: string } }) {
  const [open, setOpen] = useState(false);
  const host = hostOf(source.url);
  const hasShot = Boolean(source.screenshot);
  return (
    <li>
      <button
        type="button"
        disabled={!hasShot}
        onClick={(e) => {
          e.stopPropagation(); // don't also select the node
          if (hasShot) setOpen((o) => !o);
        }}
        aria-expanded={hasShot ? open : undefined}
        className={cn(
          "flex w-full items-center gap-2.5 px-3 py-1.5 text-left transition-colors",
          hasShot && "hover:bg-muted/50 cursor-pointer",
        )}
      >
        <span className="bg-muted text-foreground/50 inline-flex h-4 min-w-[1rem] shrink-0 items-center justify-center rounded px-1 font-mono text-[9px] tabular-nums">
          {index + 1}
        </span>
        <span className="text-foreground/75 min-w-0 flex-1 truncate text-xs">{source.title}</span>
        <span className="text-foreground/40 shrink-0 truncate text-[10px]">{host}</span>
        {hasShot && (
          <ChevronDown
            className={cn("text-foreground/35 h-3.5 w-3.5 shrink-0 transition-transform", open && "rotate-180")}
          />
        )}
      </button>
      {open && hasShot && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          title={`Open ${host}`}
          onClick={(e) => e.stopPropagation()} // open the page, don't also select the node
          className="border-border/50 bg-muted/20 hover:border-brand/50 group mx-3 mb-2 block overflow-hidden rounded-lg border transition-colors"
        >
          <div className="text-foreground/45 border-border/50 group-hover:text-brand flex items-center gap-2 border-b px-2.5 py-1 font-mono text-[9px] tracking-wider uppercase">
            <span className="truncate">{host}</span>
            <span>·</span>
            <span>open page</span>
            <ExternalLink className="ml-auto h-3 w-3 shrink-0" />
          </div>
          <div className="max-h-64 overflow-y-auto" style={scrollbarStyle}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={source.screenshot} alt={host} className="block w-full select-none" draggable={false} />
          </div>
        </a>
      )}
    </li>
  );
}

/** The source list for a browse/search node. Shows the first few pages, then collapses the long
 *  tail behind a "+N more" toggle — a DuckDuckGo search returns ~40 hits, and dumping them all
 *  would swamp the graph card. The toggle stops propagation so it doesn't also select the node. */
function SourceList({ sources }: { sources: { title: string; url: string; screenshot?: string }[] }) {
  const PREVIEW_COUNT = 3;
  const [expanded, setExpanded] = useState(false);
  const hasMore = sources.length > PREVIEW_COUNT;
  const visible = expanded ? sources : sources.slice(0, PREVIEW_COUNT);
  const rest = sources.length - PREVIEW_COUNT;
  return (
    <div className="border-border/50 border-t">
      <ul className="divide-border/40 divide-y">
        {visible.map((s, i) => (
          <SourceRow key={`${s.url}-${i}`} index={i} source={s} />
        ))}
      </ul>
      {hasMore && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation(); // toggle the tail, don't select the node
            setExpanded((v) => !v);
          }}
          className="text-foreground/55 hover:text-foreground hover:bg-muted/40 border-border/40 flex w-full items-center justify-center gap-1.5 border-t px-3 py-1.5 text-[11px] font-medium transition-colors"
        >
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", expanded && "rotate-180")} />
          {expanded ? "Show less" : `+${rest} more source${rest !== 1 ? "s" : ""}`}
        </button>
      )}
    </div>
  );
}

/** One card in the run graph — the agent's action, typed, with a preview of what it produced. */
function GraphNode({ frame, active, onClick }: { frame: Frame; active: boolean; onClick: () => void }) {
  const Icon = frameIconFor(frame);
  const sub = graphSubLabel(frame);
  const preview = graphNodePreview(frame);
  const accent = NODE_ACCENT[accentKeyFor(frame.kind)];
  const hasSources = Boolean(preview.sources && preview.sources.length > 0);
  return (
    // Not a <button>: the browse node nests per-source expander buttons, so the card is a
    // clickable div (keyboard-activatable) to keep the HTML valid.
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "bg-card w-full max-w-md cursor-pointer overflow-hidden rounded-xl border text-left transition-all",
        active ? "border-brand/50 ring-brand/30 ring-2" : "border-border/60 hover:border-brand/40",
      )}
    >
      <div className="flex items-center gap-2.5 px-3 py-2">
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
            active ? "bg-brand/15" : "bg-muted",
          )}
        >
          <Icon className={cn("h-4 w-4", active ? "text-brand" : accent.icon)} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="text-foreground block truncate text-sm font-medium">{frame.label}</span>
          {sub && <span className="text-foreground/45 block truncate text-xs">{sub}</span>}
        </span>
        <span className="flex shrink-0 items-center gap-1.5">
          {preview.meta && (
            <span className="text-foreground/50 bg-muted rounded px-1.5 py-0.5 font-mono text-[10px] tabular-nums">
              {preview.meta}
            </span>
          )}
          <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wide uppercase", accent.chip)}>
            {preview.tag}
          </span>
        </span>
      </div>
      {hasSources ? (
        <SourceList sources={preview.sources!} />
      ) : (
        preview.body &&
        (preview.code ? (
          <div className="border-border/50 bg-muted/30 border-t">
            <pre
              className="text-foreground/70 overflow-x-auto px-3 py-2 font-mono text-[11px] leading-relaxed"
              style={scrollbarStyle}
            >
              <code>{preview.body}</code>
            </pre>
          </div>
        ) : (
          <div className="border-border/50 border-t px-3 py-2">
            <p className="text-foreground/55 line-clamp-3 text-xs leading-relaxed">{preview.body}</p>
          </div>
        ))
      )}
    </div>
  );
}

/** The agent's run for one prompt as a vertical flow graph: sequential action nodes, with a deep
 * research step fanning out into the parallel subagents it dispatched. Clicking a node opens that
 * step in the log view. Shows the SHAPE of the run — the branch/merge the flat timeline can't. */
function RunGraph({
  frames,
  activeIdx,
  onSelect,
}: {
  frames: Frame[];
  activeIdx: number;
  onSelect: (i: number) => void;
}) {
  if (frames.length === 0)
    return <div className="text-foreground/40 p-6 text-center text-sm">Nothing to graph yet.</div>;
  return (
    <div className="flex flex-col items-center px-4 py-5">
      {frames.map((f, i) => {
        const subs = f.kind === "research" ? (f.research?.subagents ?? []) : [];
        return (
          <div key={f.key} className="flex w-full flex-col items-center">
            {i > 0 && <span className="bg-border/70 h-5 w-px shrink-0" />}
            <GraphNode frame={f} active={i === activeIdx} onClick={() => onSelect(i)} />
            {subs.length > 0 && (
              <>
                <span className="bg-border/70 h-4 w-px shrink-0" />
                <div className="border-border/60 bg-muted/20 w-full max-w-sm rounded-xl border border-dashed p-2.5">
                  <p className="text-foreground/45 mb-2 flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase">
                    <GitBranch className="h-3 w-3" /> {subs.length} agents in parallel
                  </p>
                  <div className={cn("grid gap-1.5", subs.length > 1 ? "sm:grid-cols-2" : "grid-cols-1")}>
                    {subs.map((s) => (
                      <div
                        key={s.task_id}
                        className="border-border/50 bg-card flex items-center gap-1.5 rounded-lg border px-2 py-1.5"
                      >
                        <Bot className="text-foreground/50 h-3.5 w-3.5 shrink-0" />
                        <span className="min-w-0 flex-1">
                          <span className="text-foreground/80 block truncate text-xs font-medium">
                            {s.subagent_name}
                          </span>
                          <span className="text-foreground/40 block truncate text-[11px]">{s.description}</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** The optional side panel — the full session log (reasoning, tools, responses) with a scrubber
 * that highlights and scrolls to the active step. A header toggle swaps the log for a run graph. */
function AgentComputer({
  frames,
  index,
  promptTitle,
  promptKey,
  isLive,
  canFollow,
  promptIndex,
  promptCount,
  hasPrevPrompt,
  hasNextPrompt,
  onPrevPrompt,
  onNextPrompt,
  canStepBack,
  canStepForward,
  onStep,
  onScrub,
  onSelect,
  onFollow,
  onClose,
  onBrowseProgress,
  activeBrowseToolId,
}: {
  frames: Frame[];
  index: number;
  promptTitle: string;
  promptKey: string;
  isLive: boolean;
  canFollow: boolean;
  promptIndex: number;
  promptCount: number;
  hasPrevPrompt: boolean;
  hasNextPrompt: boolean;
  onPrevPrompt: () => void;
  onNextPrompt: () => void;
  canStepBack: boolean;
  canStepForward: boolean;
  onStep: (dir: -1 | 1) => void;
  onScrub: (i: number) => void;
  onSelect: (i: number) => void;
  onFollow: () => void;
  onClose: () => void;
  onBrowseProgress?: (visitIndex: number) => void;
  /** The web-search tool call currently browsing (or null). Only the frame matching it animates;
   *  every other browse frame renders settled — so opening the panel late shows a finished search. */
  activeBrowseToolId: string | null;
}) {
  const total = frames.length;
  const [view, setView] = useState<"log" | "graph">("log");
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  useEffect(() => {
    if (view !== "log") return;
    // Follow the active frame so the panel scrolls in step with the chat — during the live run,
    // on a scrub, and on a prompt switch. `index` only changes on a frame transition (not on every
    // stream delta), and a browse holds `index` on its single frame for the whole animation, so
    // this tracks the run without yanking an in-progress browse scene out of view. `block: "nearest"`
    // keeps it a gentle nudge — it only scrolls when the active frame drifts out of view.
    itemRefs.current[index]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [index, promptKey, view]);

  return (
    <div className="bg-background/40 flex h-full flex-col">
      <div className="border-border/60 flex items-center gap-2.5 border-b px-4 py-3">
        <span className="bg-brand/12 flex h-7 w-7 shrink-0 items-center justify-center rounded-md">
          <Monitor className="text-brand h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-foreground text-sm leading-tight font-semibold">Agent&apos;s computer</p>
          <p className="text-foreground/45 truncate text-xs">{promptTitle || "Waiting for the agent…"}</p>
        </div>
        {isLive && (
          <span className="text-brand bg-brand/10 inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium">
            <Radio className="h-3 w-3 animate-pulse" /> Live
          </span>
        )}
        <button
          type="button"
          onClick={() => setView((v) => (v === "log" ? "graph" : "log"))}
          aria-pressed={view === "graph"}
          aria-label={view === "graph" ? "Show step log" : "Show run graph"}
          title={view === "graph" ? "Show step log" : "Show run graph"}
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors",
            view === "graph"
              ? "bg-brand/15 text-brand"
              : "text-foreground/40 hover:text-foreground hover:bg-muted",
          )}
        >
          <Workflow className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close agent's computer"
          className="text-foreground/40 hover:text-foreground hover:bg-muted flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div key={promptKey} className="min-h-0 flex-1 overflow-y-auto" style={scrollbarStyle}>
        {view === "graph" ? (
          <RunGraph frames={frames} activeIdx={index} onSelect={onSelect} />
        ) : total === 0 ? (
          <div className="text-foreground/40 flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-sm">
            <Monitor className="text-foreground/20 h-8 w-8" />
            <p>Reasoning, tool activity and responses show up here as the agent works.</p>
          </div>
        ) : (
          <div className="space-y-3 p-3">
            {frames.map((f, i) => {
              // A browse frame animates only while it's the one in progress (live + matching the
              // active search); any other browse — a finished earlier turn, or this turn once the
              // answer is out — renders settled. That's the node-status tracking that makes opening
              // the panel after a search show it already completed.
              const isActiveBrowse = isLive && Boolean(f.browse) && f.tool?.id === activeBrowseToolId;
              return (
              <div
                key={f.key}
                ref={(el) => {
                  itemRefs.current[i] = el;
                }}
                onClick={() => onSelect(i)}
                className={cn(
                  "scroll-mt-3 cursor-pointer rounded-xl transition-all duration-300",
                  i === index ? "ring-brand/40 bg-brand/[0.04] ring-2" : "opacity-70 hover:opacity-100",
                )}
              >
                <FrameContent
                  frame={f}
                  onBrowseProgress={onBrowseProgress}
                  browseInstant={!isActiveBrowse}
                />
              </div>
              );
            })}
          </div>
        )}
      </div>

      {total > 0 && (
        <div className="border-border/60 border-t">
          {promptCount > 1 && (
            <div className="border-border/50 flex items-center gap-2 border-b px-3 py-2">
              <button
                type="button"
                onClick={onPrevPrompt}
                disabled={!hasPrevPrompt}
                aria-label="Previous prompt"
                className="text-foreground/55 hover:text-foreground hover:bg-muted inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Prev
              </button>
              <span className="text-foreground/45 flex-1 text-center font-mono text-[11px] tabular-nums">
                Prompt {promptIndex + 1} / {promptCount}
              </span>
              <button
                type="button"
                onClick={onNextPrompt}
                disabled={!hasNextPrompt}
                aria-label="Next prompt"
                className="text-foreground/55 hover:text-foreground hover:bg-muted inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
              >
                Next <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-2.5">
          <button
            type="button"
            onClick={() => onStep(-1)}
            disabled={!canStepBack}
            aria-label="Previous step"
            className="text-foreground/55 hover:text-foreground hover:bg-muted flex h-7 w-7 items-center justify-center rounded-full transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <SkipBack className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onStep(1)}
            disabled={!canStepForward}
            aria-label="Next step"
            className="text-foreground/55 hover:text-foreground hover:bg-muted flex h-7 w-7 items-center justify-center rounded-full transition-colors disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <SkipForward className="h-3.5 w-3.5" />
          </button>
          <input
            type="range"
            min={0}
            max={Math.max(0, total - 1)}
            value={index}
            onChange={(e) => onScrub(Number(e.target.value))}
            aria-label="Scrub through steps"
            className="h-1.5 flex-1 cursor-pointer"
            style={{ accentColor: "var(--color-brand)" }}
          />
          <span className="text-foreground/45 shrink-0 font-mono text-xs tabular-nums">
            {index + 1}/{total}
          </span>
          {canFollow && !isLive && (
            <button
              type="button"
              onClick={onFollow}
              className="text-brand hover:bg-brand/10 inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-xs font-medium transition-colors"
            >
              <Radio className="h-3 w-3" /> Live
            </button>
          )}
          </div>
        </div>
      )}
    </div>
  );
}

export function DemoReplay({ rawMessages }: DemoReplayProps) {
  const messages = useMemo(() => conversationMessagesToChatMessages(rawMessages), [rawMessages]);

  // "Response after the browse animation": hold the turn's answer for ONE fixed duration — the
  // browse animation's own length — regardless of whether the panel is open. The chat's hold and
  // the panel's animation are both sized from this single number, so they always last the same.
  // No early release, no panel-dependent pacing: that split was the source of the desync. The
  // whole browse phase (chat "busy" spinner AND the panel scene) is gated by `activeBrowseToolId`,
  // which lives for exactly this window, so both start and end together.
  const waitForBrowse = (message: ChatMessage): Promise<void> => {
    const run = firstBrowseRun(message);
    if (!run) return Promise.resolve();
    const durationMs = browseSessionDurationMs(run.query, run.visits.length);
    return new Promise<void>((resolve) => window.setTimeout(resolve, durationMs));
  };
  // Hidden browse fetches (fetch_url/fetch) are stripped from the chat, so replaying their
  // "running" beat at full length just adds dead time — collapse it to a blink.
  const browseFetchBeatMs = (tc: ToolCall): number | undefined =>
    isFetchTool(tc.name) ? 140 : undefined;

  const { isReplaying, paused, displayMessages, tick, start, stop, pause, resume } =
    useConversationReplay(messages, { onBeforeText: waitForBrowse, toolBeatMs: browseFetchBeatMs });
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [following, setFollowing] = useState(true);
  const [expanded, setExpanded] = useState(true);
  const userToggledExpand = useRef(false);
  const lastAutoY = useRef(0);

  // Agent's computer panel — optional; opened from the thumbnail. `pinnedIdx` holds a frame the
  // user scrubbed/clicked to (null = follow the live/active frame).
  const [panelOpen, setPanelOpen] = useState(false);
  const [pinnedIdx, setPinnedIdx] = useState<number | null>(null);
  // Page the panel's browse animation is currently on — mirrored into the chat card so its spinner
  // stays in lockstep (true sync when the panel is open).
  const [browseVisitIndex, setBrowseVisitIndex] = useState<number | null>(null);
  const onBrowseProgress = (i: number) => setBrowseVisitIndex(i);

  // Flat timeline of reasoning/tool/response steps — built from what's REVEALED so far
  // (`displayMessages`), so the computer/graph unfold in lockstep with the chat instead of
  // showing the whole run up-front. Idle → full conversation (finished / pre-play).
  const frames = useMemo<Frame[]>(() => {
    const out: Frame[] = [];
    let promptKey = "p-0";
    let promptTitle = "Prompt 1";
    let n = 0;
    displayMessages.forEach((m, i) => {
      if (m.role === "user") {
        n += 1;
        promptKey = `p-${i}`;
        promptTitle = (m.content || `Prompt ${n}`).trim();
        return;
      }
      if (m.role !== "assistant") return;
      turnSteps(m).forEach((s, k) => {
        out.push({ ...s, key: `${i}-${k}`, idx: out.length, promptKey, promptTitle });
      });
    });
    return collapseBrowsing(out, messages);
  }, [displayMessages, messages]);
  const frameByKey = useMemo(() => {
    const map = new Map<string, number>();
    frames.forEach((f) => {
      map.set(f.key, f.idx);
      f.mergedKeys?.forEach((k) => map.set(k, f.idx));
    });
    return map;
  }, [frames]);
  const promptGroups = useMemo(() => {
    const map = new Map<string, { key: string; title: string; frames: Frame[] }>();
    for (const f of frames) {
      let g = map.get(f.promptKey);
      if (!g) {
        g = { key: f.promptKey, title: f.promptTitle, frames: [] };
        map.set(f.promptKey, g);
      }
      g.frames.push(f);
    }
    return [...map.values()];
  }, [frames]);
  const totalSteps = frames.length;

  // The web-search tool call whose pages are being opened right now — drives the chat card's live
  // "opening pages" spinner so the main window isn't frozen while the computer panel is closed.
  // Live from when the search resolves until the answer text starts streaming in.
  const activeBrowseToolId = useMemo<string | null>(() => {
    if (!isReplaying) return null;
    const last = displayMessages[displayMessages.length - 1];
    if (!last || last.role !== "assistant" || !last.isStreaming || !turnHasBrowsing(last)) return null;
    const hasText = last.parts?.length
      ? last.parts.some((p) => p.type === "text" && (p.content ?? "").length > 0)
      : Boolean(last.content);
    if (hasText) return null;
    const tools = last.parts?.length
      ? last.parts.filter((p) => p.type === "tool").map((p) => p.toolCall)
      : (last.toolCalls ?? []);
    return tools.find((t) => isWebSearchTool(t?.name))?.id ?? null;
    // `tick` bumps on every stream update so this tracks the turn's progress.
  }, [isReplaying, displayMessages, tick]);

  // Drop the mirrored page index once the active browse ends, so a stale value can't linger.
  useEffect(() => {
    if (!activeBrowseToolId) setBrowseVisitIndex(null);
  }, [activeBrowseToolId]);

  const showPrePlay = !hasPlayed && !isReplaying;
  const progress =
    messages.length > 0 ? Math.round((displayMessages.length / messages.length) * 100) : 0;

  // Steps for the CURRENT prompt only — the active assistant turn's checklist. Derived from the
  // REVEALED turn (`displayMessages`), so a step only appears once the agent starts it; the last
  // one is active while streaming. No pending rows — nothing shows before the agent gets to it.
  const steps = useMemo<ReplayStep[]>(() => {
    if (!isReplaying) return [];
    const idx = displayMessages.length - 1;
    const last = displayMessages[idx];
    if (!last) return [];
    if (last.role !== "assistant")
      return [{ key: "read", label: "Reading the request", kind: "text", status: "active" }];
    const turn = turnSteps(last);
    const built = turn.length;
    return turn.map((s, k) => ({
      ...s,
      key: `${idx}-${k}`,
      status: !last.isStreaming ? "done" : k === built - 1 ? "active" : "done",
    }));
    // `tick` bumps on every visual update so statuses track the stream.
  }, [isReplaying, displayMessages, tick]);

  const doneCount = steps.filter((s) => s.status === "done").length;
  const allDone = steps.length > 0 && doneCount === steps.length;
  const activeStep = steps.find((s) => s.status === "active") ?? steps.at(-1) ?? null;
  const activity = activeStep?.label ?? "Working";

  // The frame the panel shows: pinned if the user scrubbed, else the live/active frame.
  const liveIdx = activeStep ? (frameByKey.get(activeStep.key) ?? null) : null;
  const lastLiveIdx = useRef(0);
  useEffect(() => {
    if (pinnedIdx === null && liveIdx != null) lastLiveIdx.current = liveIdx;
  }, [pinnedIdx, liveIdx]);
  const shownIdx = clamp(pinnedIdx ?? liveIdx ?? lastLiveIdx.current, 0, Math.max(0, totalSteps - 1));
  const shownFrame = frames[shownIdx] ?? null;
  // The computer shows only the current prompt's frames — not the whole conversation.
  const currentGroup = promptGroups.find((g) => g.key === shownFrame?.promptKey) ?? promptGroups[0] ?? null;
  const groupFrames = currentGroup?.frames ?? [];
  const localIndex = Math.max(
    0,
    groupFrames.findIndex((f) => f.idx === shownIdx),
  );
  // Prompt-level navigation for the panel — jump the computer to another agent turn.
  const groupIndex = promptGroups.findIndex((g) => g.key === currentGroup?.key);
  const gotoPrompt = (dir: -1 | 1) => {
    const target = promptGroups[groupIndex + dir];
    if (target) setPinnedIdx(target.frames[0]?.idx ?? shownIdx);
  };

  // Per-task live timer — runs only on the currently-active step, resets when it changes,
  // and disappears once that step completes.
  const activeKey = useMemo(() => steps.find((s) => s.status === "active")?.key ?? null, [steps]);
  const [activeStart, setActiveStart] = useState<number | null>(null);
  const [, setClock] = useState(0);
  useEffect(() => {
    setActiveStart(activeKey ? Date.now() : null);
  }, [activeKey]);
  // Tick the timer only while running (frozen while paused).
  useEffect(() => {
    if (!isReplaying || !activeKey || paused) return;
    const id = setInterval(() => setClock((c) => c + 1), 250);
    return () => clearInterval(id);
  }, [isReplaying, activeKey, paused]);
  // Shift the start forward by the paused duration so elapsed time resumes seamlessly.
  const pausedAtRef = useRef<number | null>(null);
  useEffect(() => {
    if (paused) {
      pausedAtRef.current = Date.now();
    } else if (pausedAtRef.current !== null) {
      const gap = Date.now() - pausedAtRef.current;
      pausedAtRef.current = null;
      setActiveStart((s) => (s !== null ? s + gap : s));
    }
  }, [paused]);
  const activeTimer = activeStart !== null ? formatElapsed(Date.now() - activeStart) : null;

  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const toggleGroup = (key: string) =>
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const play = () => {
    setHasPlayed(true);
    setFollowing(true);
    setExpanded(true);
    userToggledExpand.current = false;
    setPinnedIdx(null);
    setBrowseVisitIndex(null);
    start();
  };

  const toggleExpand = () => {
    userToggledExpand.current = true;
    setExpanded((e) => !e);
  };

  // Thumbnail toggles the panel; opening resets to follow the live step.
  const togglePanel = () =>
    setPanelOpen((o) => {
      if (!o) setPinnedIdx(null);
      return !o;
    });

  const openFrame = (idx: number | undefined) => {
    if (idx == null) return;
    setPinnedIdx(clamp(idx, 0, Math.max(0, totalSteps - 1)));
    setPanelOpen(true);
  };

  // Skip the animation and jump straight to the finished conversation ("Skip to results").
  const skipToEnd = () => {
    stop();
    setHasPlayed(true);
    setFollowing(true);
    requestAnimationFrame(() => {
      const container = scrollRef.current;
      if (container) container.scrollTo({ top: container.scrollHeight, behavior: "auto" });
    });
  };

  // Keep the container pinned to the bottom while replaying.
  useEffect(() => {
    if (!isReplaying || !following) return;
    const container = scrollRef.current;
    if (!container) return;
    const target = container.scrollHeight - container.clientHeight;
    if (target - container.scrollTop > 2) {
      container.scrollTo({ top: target, behavior: "auto" });
      lastAutoY.current = container.scrollTop;
    }
  }, [tick, isReplaying, following]);

  // Disengage auto-scroll only on a genuine user scroll-up GESTURE (wheel up or
  // a downward touch drag). We deliberately don't watch the "scroll" event: each
  // new replayed turn commits its message and pops the next bubble in, which
  // shifts the layout and nudges scrollTop — the old scroll-based check read
  // that as "the user scrolled up" and killed the follow at every turn boundary.
  // Programmatic scrollBy and reflows never fire wheel/touch, so this is immune.
  useEffect(() => {
    if (!isReplaying) return;
    const container = scrollRef.current;
    if (!container) return;
    let touchY = 0;
    const onWheel = (e: WheelEvent) => {
      if (e.deltaY < 0) setFollowing(false);
    };
    const onTouchStart = (e: TouchEvent) => {
      touchY = e.touches[0]?.clientY ?? 0;
    };
    const onTouchMove = (e: TouchEvent) => {
      const y = e.touches[0]?.clientY ?? 0;
      if (y - touchY > 8) setFollowing(false); // finger dragged down = scrolling up
      touchY = y;
    };
    container.addEventListener("wheel", onWheel, { passive: true });
    container.addEventListener("touchstart", onTouchStart, { passive: true });
    container.addEventListener("touchmove", onTouchMove, { passive: true });
    return () => {
      container.removeEventListener("wheel", onWheel);
      container.removeEventListener("touchstart", onTouchStart);
      container.removeEventListener("touchmove", onTouchMove);
    };
  }, [isReplaying]);

  const jumpToActive = () => {
    setFollowing(true);
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "auto" });
    lastAutoY.current = container.scrollTop;
  };

  const blurStyle = {
    filter: "blur(6px)",
    opacity: 0.25,
    pointerEvents: "none" as const,
    userSelect: "none" as const,
  };

  const panelVisible = panelOpen && !showPrePlay;

  return (
    <div className={cn("mx-auto flex h-[calc(100vh-3.5rem)] w-full", panelVisible ? "max-w-none" : "max-w-4xl")}>
      {/* Chat + dock column — grows to fill the left; the panel takes a fixed share on the right */}
      <div className={cn("flex min-w-0 flex-1 flex-col px-4", panelVisible && "hidden lg:flex")}>
        {/* Messages — scrollable container, fills remaining height */}
        <div
          ref={scrollRef}
          className="[&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-thumb:hover]:bg-brand/50 flex-1 overflow-y-auto py-4 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-track]:bg-transparent"
          style={scrollbarStyle}
        >
          <div
            className="transition-[filter,opacity] duration-700"
            style={showPrePlay ? blurStyle : undefined}
          >
            <BrowseActivityProvider
              value={{
                toolCallId: activeBrowseToolId,
                // Only mirror the animation's page when the panel is actually open; otherwise the
                // card runs its own fast spinner (null = no external clock).
                visitIndex: panelOpen && activeBrowseToolId ? browseVisitIndex : null,
              }}
            >
              {(showPrePlay ? messages : displayMessages).map((message) => (
                <MessageItem key={message.id} message={stripBrowseFetches(message)} />
              ))}
            </BrowseActivityProvider>
          </div>
          <div ref={bottomRef} className="h-0" />
          {isReplaying && <div aria-hidden className="h-[24vh]" />}
        </div>

        {/* Pre-play overlay — cinematic reveal moment */}
        {showPrePlay && (
          <div className="bg-foreground/60 fixed inset-0 z-30 flex flex-col items-center justify-center gap-7 backdrop-blur-sm">
            <button
              type="button"
              onClick={play}
              className="group/btn relative outline-none"
              aria-label="Watch replay"
            >
              <span className="bg-brand/30 absolute inset-0 animate-ping rounded-full" />
              <span
                className="bg-brand/12 absolute animate-ping rounded-full [animation-delay:420ms]"
                style={playBtnRingStyle}
              />
              <span
                className="bg-brand relative flex h-24 w-24 items-center justify-center rounded-full shadow-lg transition-transform duration-300 group-hover/btn:scale-[1.06] group-active/btn:scale-95"
                style={playBtnGlowStyle}
              >
                <Play className="h-10 w-10 translate-x-1 fill-white text-white" />
              </span>
            </button>

            <div className="text-center">
              <p className="text-xl font-semibold text-white">Watch the agent work</p>
              <p className="mt-1.5 font-mono text-sm text-white/60">
                {messages.length} messages · replayed live
              </p>
            </div>
          </div>
        )}

        {/* Jump-to-active button — re-engages auto-scroll after manual scroll-up */}
        {isReplaying && !following && (
          <button
            type="button"
            onClick={jumpToActive}
            className="step-reveal border-border bg-card/95 text-foreground/80 hover:border-brand/50 hover:text-foreground fixed right-4 bottom-44 z-20 inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs font-medium shadow-lg backdrop-blur transition-colors"
          >
            <ArrowDown className="h-3.5 w-3.5" />
            Jump to active
          </button>
        )}

        {/* Bottom dock — replay status panel + controls, pinned by the flex column */}
        <div className="bg-background/70 -mx-4 px-4 pt-2 pb-4">
          {showPrePlay ? (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={play}
                className="bg-brand inline-flex items-center gap-2 rounded-full px-8 py-3 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
              >
                <Play className="h-4 w-4 fill-current" />
                Watch the agent work
              </button>
            </div>
          ) : isReplaying ? (
            <div className="border-border/70 bg-card/80 mx-auto flex max-w-3xl gap-2.5 overflow-hidden rounded-2xl border p-2 shadow-[0_8px_30px_-12px_oklch(0%_0_0/0.25)] backdrop-blur">
              <ToolThumb frame={shownFrame} onClick={togglePanel} live />
              <div className="min-w-0 flex-1">
                {/* Header — live status; the whole row toggles the step list */}
                <button
                  type="button"
                  onClick={toggleExpand}
                  aria-expanded={expanded}
                  className="hover:bg-muted/40 -mx-1 flex w-[calc(100%+0.5rem)] items-center gap-3 rounded-lg px-1.5 py-1.5 text-left transition-colors"
                >
                  <span className="relative flex h-7 w-7 shrink-0 items-center justify-center">
                    <span className={cn("bg-brand/12 absolute inset-0 rounded-full", !allDone && !paused && "animate-pulse")} />
                    {allDone ? (
                      <Check className="text-brand relative h-4 w-4" strokeWidth={2.5} />
                    ) : paused ? (
                      <Pause className="text-brand relative h-3.5 w-3.5" />
                    ) : (
                      <Loader2 className="text-brand relative h-4 w-4 animate-spin" />
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="text-foreground block truncate text-sm font-semibold">
                      {allDone ? "Done" : paused ? "Paused" : activity}
                    </span>
                    {steps.length > 0 && (
                      <span className="text-foreground/45 block text-xs">
                        {doneCount} of {steps.length} {steps.length === 1 ? "step" : "steps"}
                      </span>
                    )}
                  </span>
                  <ChevronDown
                    className={cn(
                      "text-foreground/40 h-4 w-4 shrink-0 transition-transform duration-300",
                      expanded && "rotate-180",
                    )}
                  />
                </button>

                {/* Slim progress line */}
                <div className="bg-border/50 mt-1 h-px w-full overflow-hidden">
                  <div
                    className="bg-brand h-full transition-[width] duration-500 ease-out"
                    style={{ width: `${progress}%`, ...progressGlowStyle }}
                  />
                </div>

                {/* Expandable step timeline — animated open/close via grid rows */}
                <div
                  className={cn(
                    "grid transition-[grid-template-rows] duration-300 ease-out",
                    expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
                  )}
                >
                  <div className="overflow-hidden">
                    <ul className="max-h-52 overflow-y-auto px-1.5 py-2.5" style={scrollbarStyle}>
                      {steps.map((s, i) => (
                        <StepItem
                          key={s.key}
                          label={s.label}
                          status={s.status}
                          isLast={i === steps.length - 1}
                          timer={s.status === "active" ? activeTimer : null}
                          onSelect={() => openFrame(frameByKey.get(s.key))}
                          selected={panelVisible && shownIdx === frameByKey.get(s.key)}
                        />
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Controls */}
                <div className="border-border/50 mt-1 flex items-center justify-end gap-1 border-t px-1 pt-1.5">
                  <button
                    type="button"
                    onClick={skipToEnd}
                    className="text-foreground/55 hover:text-foreground hover:bg-muted inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
                  >
                    <FastForward className="h-3.5 w-3.5" />
                    Skip to end
                  </button>
                  <button
                    type="button"
                    onClick={paused ? resume : pause}
                    className="text-foreground/55 hover:text-foreground hover:bg-muted inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
                  >
                    {paused ? <Play className="h-3.5 w-3.5 fill-current" /> : <Pause className="h-3.5 w-3.5" />}
                    {paused ? "Resume" : "Pause"}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            // Finished — the panel stays, grouped into a collapsible section per prompt.
            <div className="border-border/70 bg-card/80 mx-auto max-w-3xl overflow-hidden rounded-2xl border shadow-[0_8px_30px_-12px_oklch(0%_0_0/0.25)] backdrop-blur">
              <div className="flex items-center gap-2.5 px-3 py-3">
                <ToolThumb frame={shownFrame} onClick={togglePanel} live={false} />
                <span className="min-w-0 flex-1">
                  <span className="text-foreground block text-sm font-semibold">Replay complete</span>
                  <span className="text-foreground/45 block text-xs">
                    {promptGroups.length} {promptGroups.length === 1 ? "prompt" : "prompts"} · {totalSteps}{" "}
                    {totalSteps === 1 ? "step" : "steps"}
                  </span>
                </span>
              </div>

              <div className="max-h-64 overflow-y-auto" style={scrollbarStyle}>
                {promptGroups.map((g) => {
                  const open = expandedGroups.has(g.key);
                  return (
                    <div key={g.key} className="border-border/50 border-t">
                      <button
                        type="button"
                        onClick={() => toggleGroup(g.key)}
                        aria-expanded={open}
                        className="hover:bg-muted/40 flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left transition-colors"
                      >
                        <ChevronDown
                          className={cn(
                            "text-foreground/40 h-4 w-4 shrink-0 transition-transform duration-200",
                            open && "rotate-180",
                          )}
                        />
                        <span className="text-foreground/80 min-w-0 flex-1 truncate text-sm">{g.title}</span>
                        <span className="text-foreground/40 shrink-0 font-mono text-xs tabular-nums">
                          {g.frames.length}
                        </span>
                      </button>
                      <div
                        className={cn(
                          "grid transition-[grid-template-rows] duration-300 ease-out",
                          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
                        )}
                      >
                        <div className="overflow-hidden">
                          <ul className="py-1 pr-3.5 pb-3 pl-9">
                            {g.frames.map((f, i) => (
                              <StepItem
                                key={f.key}
                                label={f.label}
                                status="done"
                                isLast={i === g.frames.length - 1}
                                onSelect={() => openFrame(f.idx)}
                                selected={panelVisible && shownIdx === f.idx}
                              />
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="border-border/50 flex justify-center border-t px-2.5 py-3">
                <button
                  type="button"
                  onClick={play}
                  className="bg-brand inline-flex items-center gap-2 rounded-full px-7 py-2.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
                >
                  <RotateCcw className="h-4 w-4" />
                  Watch again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Agent's computer — optional side panel (full-width drawer on narrow screens) */}
      {panelVisible && (
        <aside className="border-border/60 bg-card/40 flex w-full min-w-0 flex-col border-l lg:w-[46%] lg:max-w-[820px] lg:min-w-[400px] lg:shrink-0">
          <AgentComputer
            frames={groupFrames}
            index={localIndex}
            promptTitle={currentGroup?.title ?? ""}
            promptKey={currentGroup?.key ?? "none"}
            isLive={isReplaying && pinnedIdx === null}
            canFollow={isReplaying}
            promptIndex={groupIndex}
            promptCount={promptGroups.length}
            hasPrevPrompt={groupIndex > 0}
            hasNextPrompt={groupIndex >= 0 && groupIndex < promptGroups.length - 1}
            onPrevPrompt={() => gotoPrompt(-1)}
            onNextPrompt={() => gotoPrompt(1)}
            canStepBack={shownIdx > 0}
            canStepForward={shownIdx < totalSteps - 1}
            onStep={(dir) => setPinnedIdx(clamp(shownIdx + dir, 0, Math.max(0, totalSteps - 1)))}
            onScrub={(i) => setPinnedIdx(groupFrames[i]?.idx ?? shownIdx)}
            onSelect={(i) => setPinnedIdx(groupFrames[i]?.idx ?? shownIdx)}
            onFollow={() => setPinnedIdx(null)}
            onClose={() => setPanelOpen(false)}
            onBrowseProgress={onBrowseProgress}
            activeBrowseToolId={activeBrowseToolId}
          />
        </aside>
      )}
    </div>
  );
}
{% endraw %}
