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
import { MarkdownContent } from "@/components/chat/markdown-content";
import { MessageItem } from "@/components/chat/message-item";
{% endraw %}{%- if cookiecutter.enable_deep_research %}{% raw %}
import { ResearchReplayBlock } from "@/components/chat/research-replay-block";
{% endraw %}{%- endif %}{% raw %}
import { ToolCallCard } from "@/components/chat/tool-call-card";
{% endraw %}{%- if cookiecutter.enable_web_fetch %}{% raw %}
import { FetchUrlResult } from "@/components/chat/tool-results/fetch-url";
{% endraw %}{%- endif %}{% raw %}
import { RawToolView } from "@/components/chat/tool-results/generic";
import { WebSearchResults, parseWebSearch } from "@/components/chat/tool-results/web-search";
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
// A single frame in the "Agent's computer" timeline — one reasoning/tool/response step.
interface Frame extends TurnStep {
  key: string;
  idx: number;
  promptKey: string;
  promptTitle: string;
}

const playBtnRingStyle = { inset: "-10px", borderRadius: "9999px" };
const playBtnGlowStyle = { boxShadow: "0 0 60px oklch(from var(--color-brand) l c h / 0.5)" };
const progressGlowStyle = { boxShadow: "0 0 12px oklch(from var(--color-brand) l c h / 0.55)" };
const scrollbarStyle: React.CSSProperties = {
  scrollbarWidth: "thin",
  scrollbarColor: "var(--color-border) transparent",
};

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);

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
  search_knowledge_base: "Searching the knowledge base",
  search_documents: "Searching documents",
  fetch_url: "Opening a page",
  ask_user: "Asking a question",
  ask_user_tool: "Asking a question",
};

const humanizeTool = (name: string) =>
  name
    .replace(/_/g, " ")
    .replace(/\btool\b/gi, "")
    .trim()
    .replace(/^\w/, (c) => c.toUpperCase()) || "Working";

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
  if (name.includes("search") || name === "fetch_url") return Globe;
  return Wrench;
};

// Read from the SOURCE message so the full list is known up-front and fills in as replay progresses.
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

// The computer panel goes deeper than the chat: richer web/research/fetch renderers, plus the
// raw tool I/O the chat hides. Text/thinking/research have no raw layer.
function FrameContent({ frame }: { frame: Frame }) {
  if (frame.kind === "thinking") return <ThinkingView content={frame.content ?? ""} />;
  if (frame.kind === "text") return <ResponseView content={frame.content ?? ""} />;
{% endraw %}{%- if cookiecutter.enable_deep_research %}{% raw %}
  if (frame.kind === "research" && frame.research)
    return <ResearchReplayBlock research={frame.research} animate={false} detailed />;
{% endraw %}{%- endif %}{% raw %}

  const tool = frame.tool;
  if (!tool) return <div className="text-foreground/50 p-3 text-sm">Working…</div>;
  // `tool.result == null` must yield "" — stringifying it would give the literal
  // two-char string `""`, which is truthy and renders as a bogus content box.
  const resultText =
    tool.result == null
      ? ""
      : typeof tool.result === "string"
        ? tool.result
        : JSON.stringify(tool.result, null, 2);

  if (tool.name === "web_search_tool" || tool.name === "search_web") {
    const data = parseWebSearch(resultText);
    if (data)
      return (
        <div className="space-y-2">
          <WebSearchResults data={data} detailed />
          <RawIO tool={tool} resultText={resultText} />
        </div>
      );
  }
{% endraw %}{%- if cookiecutter.enable_web_fetch %}{% raw %}
  if ((tool.name === "fetch_url" || tool.name === "fetch") && typeof tool.args?.url === "string") {
    return (
      <div className="space-y-2">
        <FetchUrlResult url={String(tool.args.url)} content={resultText} />
        <RawIO tool={tool} resultText={resultText} />
      </div>
    );
  }
{% endraw %}{%- endif %}{% raw %}
  return (
    <div className="space-y-2">
      <ToolCallCard key={frame.key} toolCall={tool} defaultExpanded />
      <RawIO tool={tool} resultText={resultText} />
    </div>
  );
}

function graphSubLabel(frame: Frame): string | null {
  const t = frame.tool;
  if (!t) return null;
  const a = (t.args ?? {}) as Record<string, unknown>;
  if (t.name === "load_skill" && typeof a.name === "string") return a.name;
  if ((t.name === "fetch_url" || t.name === "fetch") && typeof a.url === "string") {
    try {
      return new URL(a.url).hostname.replace(/^www\./, "");
    } catch {
      return a.url;
    }
  }
  if (t.name.startsWith("create_chart") && typeof a.title === "string") return a.title;
  if ((t.name === "web_search_tool" || t.name === "search_web") && typeof a.query === "string") return a.query;
  if ((t.name === "ask_user" || t.name === "ask_user_tool") && typeof a.question === "string") return a.question;
  return null;
}

interface NodePreview {
  tag: string;
  meta?: string | null;
  body?: string | null;
  code?: boolean;
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

const clipText = (s: string, n = 180) => {
  const t = stripMarkdown(s).replace(/\s+/g, " ").trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
};

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
  const result =
    t.result == null ? "" : typeof t.result === "string" ? t.result : JSON.stringify(t.result);

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
  if (t.name === "web_search_tool" || t.name === "search_web") {
    const parsed = parseWebSearch(result);
    const titles = parsed?.results.map((r) => r.title).join(" · ") ?? "";
    return {
      tag: "Web search",
      meta: parsed?.results.length ? `${parsed.results.length} results` : null,
      body: clipText(titles || result, 160),
    };
  }
  if (t.name === "fetch_url" || t.name === "fetch") {
    return {
      tag: "Fetch",
      meta: result ? `${result.length.toLocaleString()} chars` : null,
      body: clipText(result, 160),
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

/** One card in the run graph — the agent's action, typed, with a preview of what it produced. */
function GraphNode({ frame, active, onClick }: { frame: Frame; active: boolean; onClick: () => void }) {
  const Icon = frameIconFor(frame);
  const sub = graphSubLabel(frame);
  const preview = graphNodePreview(frame);
  const accent = NODE_ACCENT[accentKeyFor(frame.kind)];
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "bg-card w-full max-w-md overflow-hidden rounded-xl border text-left transition-all",
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
      {preview.body &&
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
        ))}
    </button>
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
}) {
  const total = frames.length;
  const [view, setView] = useState<"log" | "graph">("log");
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);
  useEffect(() => {
    if (view !== "log") return;
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
            {frames.map((f, i) => (
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
                <FrameContent frame={f} />
              </div>
            ))}
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
  const { isReplaying, paused, displayMessages, tick, start, stop, pause, resume } =
    useConversationReplay(messages);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [following, setFollowing] = useState(true);
  const [expanded, setExpanded] = useState(true);
  const userToggledExpand = useRef(false);

  // Agent's computer panel — optional; opened from the thumbnail. `pinnedIdx` holds a frame the
  // user scrubbed/clicked to (null = follow the live/active frame).
  const [panelOpen, setPanelOpen] = useState(false);
  const [pinnedIdx, setPinnedIdx] = useState<number | null>(null);

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
    return out;
  }, [displayMessages]);
  const frameByKey = useMemo(() => {
    const map = new Map<string, number>();
    frames.forEach((f) => map.set(f.key, f.idx));
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
    start();
  };

  const toggleExpand = () => {
    userToggledExpand.current = true;
    setExpanded((e) => !e);
  };

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
    const onPointerDown = (e: PointerEvent) => {
      const inScrollbar = e.clientX - container.getBoundingClientRect().left >= container.clientWidth;
      if (inScrollbar) setFollowing(false);
    };
    container.addEventListener("wheel", onWheel, { passive: true });
    container.addEventListener("touchstart", onTouchStart, { passive: true });
    container.addEventListener("touchmove", onTouchMove, { passive: true });
    container.addEventListener("pointerdown", onPointerDown, { passive: true });
    return () => {
      container.removeEventListener("wheel", onWheel);
      container.removeEventListener("touchstart", onTouchStart);
      container.removeEventListener("touchmove", onTouchMove);
      container.removeEventListener("pointerdown", onPointerDown);
    };
  }, [isReplaying]);

  const jumpToActive = () => {
    setFollowing(true);
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "auto" });
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
            {(showPrePlay ? messages : displayMessages).map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
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
          />
        </aside>
      )}
    </div>
  );
}
{% endraw %}
