"use client";

import { FileText, Search } from "lucide-react";

import type { ToolCall } from "@/types";
import { parsePyLiteral, type PyValue } from "@/lib/py-literal";
import { GenericToolResult } from "./generic";

/** Result shapes mirror the harness memory toolset TypedDicts; results arrive
 *  as Python-repr strings (`str(dict)`), hence parsePyLiteral with a JSON
 *  fallback. `read_memory` is the exception — it returns the file text as-is. */

/** The pydantic-ai-harness Memory capability's four tools. Mirrors
 *  `MEMORY_TOOL_NAMES` in the backend's `app/agents/memory.py`. */
export const MEMORY_TOOLS = new Set([
  "write_memory",
  "read_memory",
  "delete_memory",
  "search_memory",
]);

export const isMemoryTool = (name: string | undefined | null): boolean =>
  !!name && MEMORY_TOOLS.has(name);

interface WriteResult {
  file: string;
  status: "created" | "appended" | "updated";
}

interface DeleteResult {
  file: string;
  status: "deleted" | "not_found";
}

interface SearchMatch {
  file: string;
  snippet: string;
}

interface SearchResult {
  matches: SearchMatch[];
  scanned: number;
  truncated: boolean;
}

function parseRecord(result: string): Record<string, PyValue> | null {
  let value: PyValue | null = parsePyLiteral(result);
  if (value === null) {
    try {
      value = JSON.parse(result) as PyValue;
    } catch {
      return null;
    }
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  return value;
}

/** `write_memory` and `delete_memory` both answer with a file plus a status.
 *  Exported because the demo run-graph labels its nodes from the same result. */
export function parseMemoryFileStatus<S extends string = string>(
  result: string,
): { file: string; status: S } | null {
  const rec = parseRecord(result);
  if (!rec || typeof rec.file !== "string" || typeof rec.status !== "string") return null;
  return { file: rec.file, status: rec.status as S };
}

export function parseMemorySearch(result: string): SearchResult | null {
  const rec = parseRecord(result);
  if (!rec || !Array.isArray(rec.matches)) return null;
  const matches: SearchMatch[] = [];
  for (const m of rec.matches) {
    if (typeof m === "object" && m !== null && !Array.isArray(m)) {
      const file = (m as Record<string, PyValue>).file;
      const snippet = (m as Record<string, PyValue>).snippet;
      if (typeof file === "string") {
        matches.push({ file, snippet: typeof snippet === "string" ? snippet : "" });
      }
    }
  }
  return {
    matches,
    scanned: typeof rec.scanned === "number" ? rec.scanned : matches.length,
    truncated: rec.truncated === true,
  };
}

const WRITE_LABELS: Record<WriteResult["status"], string> = {
  created: "Created",
  appended: "Appended to",
  updated: "Updated",
};

function FileBadge({ file }: { file: string }) {
  return (
    <code className="text-foreground bg-foreground/8 rounded px-1.5 py-0.5 font-mono text-xs">
      {file}
    </code>
  );
}

function Pending({ status }: { status: string }) {
  return (
    <p className="text-muted-foreground py-2 text-xs italic">
      {status === "error" ? "Memory operation failed." : "Working…"}
    </p>
  );
}

export function MemoryToolResult({
  toolCall,
  resultText,
}: {
  toolCall: ToolCall;
  resultText: string;
}) {
  // An empty result is a legitimate answer for a blank memory file, so only the
  // status decides whether the call is still in flight.
  if (toolCall.status !== "completed") {
    return <Pending status={toolCall.status} />;
  }

  if (toolCall.name === "write_memory") {
    const parsed = parseMemoryFileStatus<WriteResult["status"]>(resultText);
    if (!parsed) return <GenericToolResult toolCall={toolCall} resultText={resultText} />;
    const savedContent =
      typeof toolCall.args?.content === "string" ? (toolCall.args.content as string) : null;
    return (
      <div className="space-y-1.5 py-1">
        <p className="text-foreground/75 text-[13px]">
          {WRITE_LABELS[parsed.status] ?? "Updated"} <FileBadge file={parsed.file} />
        </p>
        {savedContent && (
          <p className="text-foreground/55 border-foreground/15 line-clamp-3 border-l-2 pl-2 text-xs whitespace-pre-wrap">
            {savedContent}
          </p>
        )}
      </div>
    );
  }

  if (toolCall.name === "delete_memory") {
    const parsed = parseMemoryFileStatus<DeleteResult["status"]>(resultText);
    if (!parsed) return <GenericToolResult toolCall={toolCall} resultText={resultText} />;
    return (
      <p className="text-foreground/75 py-1 text-[13px]">
        {parsed.status === "deleted" ? (
          <>
            Deleted <FileBadge file={parsed.file} />
          </>
        ) : (
          <>
            <FileBadge file={parsed.file} /> was not found.
          </>
        )}
      </p>
    );
  }

  if (toolCall.name === "read_memory") {
    const file = typeof toolCall.args?.file === "string" ? toolCall.args.file : "MEMORY.md";
    return (
      <div className="border-foreground/10 rounded-xl border">
        <div className="text-foreground/55 border-foreground/10 flex items-center gap-2 border-b px-3 py-2 font-mono text-[10px] tracking-wider uppercase">
          <FileText className="h-3 w-3" />
          {file}
        </div>
        {resultText ? (
          <pre className="text-foreground/75 max-h-64 overflow-y-auto p-3 font-mono text-xs whitespace-pre-wrap">
            {resultText}
          </pre>
        ) : (
          <p className="text-muted-foreground p-3 text-xs italic">This file is empty.</p>
        )}
      </div>
    );
  }

  if (toolCall.name === "search_memory") {
    const parsed = parseMemorySearch(resultText);
    if (!parsed) return <GenericToolResult toolCall={toolCall} resultText={resultText} />;
    const query = typeof toolCall.args?.query === "string" ? toolCall.args.query : null;
    if (parsed.matches.length === 0) {
      return (
        <p className="text-muted-foreground py-2 text-xs italic">
          No memories matched{query ? ` “${query}”` : ""}.
        </p>
      );
    }
    return (
      <div className="space-y-2 py-1">
        <div className="text-foreground/55 flex items-center gap-2 font-mono text-[10px] tracking-wider uppercase">
          <Search className="h-3 w-3" />
          {parsed.matches.length} match{parsed.matches.length === 1 ? "" : "es"}
          {query ? ` for “${query}”` : ""}
        </div>
        <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
          {parsed.matches.map((match, idx) => (
            <li key={`${match.file}-${idx}`} className="px-3 py-2">
              <div className="flex items-baseline gap-2">
                <span className="text-foreground/45 h-5 min-w-[1.5rem] font-mono text-[10px]">
                  {idx + 1}.
                </span>
                <FileBadge file={match.file} />
              </div>
              {match.snippet && (
                <p className="text-foreground/60 mt-1 line-clamp-2 pl-8 text-xs">{match.snippet}</p>
              )}
            </li>
          ))}
        </ul>
        <p className="text-foreground/45 text-[11px]">
          Scanned {parsed.scanned} file{parsed.scanned === 1 ? "" : "s"}
          {parsed.truncated ? " (results truncated)" : ""}.
        </p>
      </div>
    );
  }

  return <GenericToolResult toolCall={toolCall} resultText={resultText} />;
}
