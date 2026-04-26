"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, Badge, Button } from "@/components/ui";
import type { ToolCall } from "@/types";
import {
  Wrench,
  CheckCircle,
  Loader2,
  AlertCircle,
  Clock,
  Calendar,
  FileText,
  Search,
  Globe,
  Link,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CopyButton } from "./copy-button";

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
          <Calendar className="h-5 w-5 text-primary" />
          <div>
            <p className="text-xs text-muted-foreground">Date</p>
            <p className="text-sm font-semibold">{dateMatch[1]}</p>
          </div>
        </div>
      )}
      {timeMatch && (
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          <div>
            <p className="text-xs text-muted-foreground">Time</p>
            <p className="text-sm font-semibold">{timeMatch[1]}</p>
          </div>
        </div>
      )}
      {!dateMatch && !timeMatch && (
        <p className="text-sm">{result}</p>
      )}
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
  const pattern = /\[(\d+)\]\s*Source:\s*([^,\n]+?)(?:,\s*page\s*(\d+))?(?:,\s*chunk\s*(\d+))?(?:\s*\[([^\]]+)\])?\s*\(score:\s*([\d.]+)\)\n([\s\S]*?)(?=\n\[\d+\]|$)/g;
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
        <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
          <Search className="h-4 w-4" />
          No relevant documents found
        </div>
      );
    }
    return null; // fallback to default renderer
  }

  return (
    <div className="space-y-2 py-1">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Search className="h-3.5 w-3.5" />
        Found {items.length} result{items.length !== 1 ? "s" : ""}
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {items.map((item) => (
          <Card
            key={item.index}
            className={cn(
              "min-w-[220px] max-w-[280px] shrink-0 cursor-pointer transition-all",
              expandedIdx === item.index ? "ring-2 ring-primary" : "hover:bg-accent"
            )}
            onClick={() => setExpandedIdx(expandedIdx === item.index ? null : item.index)}
          >
            <CardContent className="p-3">
              <div className="mb-1.5 flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                <span className="text-xs font-medium truncate">{item.source}</span>
              </div>
              <div className="flex flex-wrap gap-1 mb-1.5">
                <Badge variant="secondary" className="text-[10px] px-1 py-0">
                  [{item.index}]
                </Badge>
                {item.page && (
                  <Badge variant="outline" className="text-[10px] px-1 py-0">
                    p.{item.page}
                  </Badge>
                )}
                {item.collection && (
                  <Badge variant="outline" className="text-[10px] px-1 py-0">
                    {item.collection}
                  </Badge>
                )}
                <Badge
                  variant="outline"
                  className={cn("text-[10px] px-1 py-0 ml-auto", {
                    "text-green-600": parseFloat(item.score) >= 0.7,
                    "text-yellow-600": parseFloat(item.score) >= 0.4 && parseFloat(item.score) < 0.7,
                    "text-red-600": parseFloat(item.score) < 0.4,
                  })}
                >
                  {parseFloat(item.score).toFixed(2)}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">{item.content}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Expanded view */}
      {expandedIdx !== null && (() => {
        const expandedItem = items.find(i => i.index === expandedIdx);
        if (!expandedItem) return null;
        return (
          <Card className="border-primary/50 bg-primary/5">
            <CardContent className="p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">[{expandedItem.index}]</Badge>
                  <span className="text-xs font-medium">{expandedItem.source}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => setExpandedIdx(null)}
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                </Button>
              </div>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {expandedItem.content}
              </p>
            </CardContent>
          </Card>
        );
      })()}
    </div>
  );
}

interface WebResultItem {
  index: number;
  title: string;
  url: string;
  content: string;
}

function parseWebResults(result: string): WebResultItem[] {
  const items: WebResultItem[] = [];
  const pattern = /\[(\d+)\]\s*(.+?)\n\s*URL:\s*(\S+)\n\s*([\s\S]*?)(?=\n\[\d+\]|$)/g;
  let match;
  while ((match = pattern.exec(result)) !== null) {
    items.push({
      index: parseInt(match[1] ?? "0"),
      title: (match[2] ?? "").trim(),
      url: (match[3] ?? "").trim(),
      content: (match[4] ?? "").trim(),
    });
  }
  return items;
}

function WebSearchResults({ result }: { result: string }) {
  const items = parseWebResults(result);

  if (items.length === 0) {
    if (result.includes("No web results")) {
      return (
        <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
          <Globe className="h-4 w-4" />
          No web results found
        </div>
      );
    }
    return null;
  }

  return (
    <div className="space-y-2 py-1">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Globe className="h-3.5 w-3.5" />
        {items.length} web result{items.length !== 1 ? "s" : ""}
      </div>
      {items.map((item) => (
        <div key={item.index} className="rounded-md border bg-background p-2.5">
          <div className="flex items-start gap-2">
            <Badge variant="secondary" className="text-[10px] px-1 py-0 shrink-0 mt-0.5">
              [{item.index}]
            </Badge>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium truncate">{item.title}</p>
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[10px] text-primary hover:underline truncate"
              >
                <Link className="h-2.5 w-2.5 shrink-0" />
                {item.url}
              </a>
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{item.content}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// --- Main component ---

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [showRaw, setShowRaw] = useState(false);

  const statusConfig = {
    pending: { icon: Loader2, color: "text-muted-foreground", animate: true },
    running: { icon: Loader2, color: "text-blue-500", animate: true },
    completed: { icon: CheckCircle, color: "text-green-500", animate: false },
    error: { icon: AlertCircle, color: "text-red-500", animate: false },
  };

  const { icon: StatusIcon, color, animate } = statusConfig[toolCall.status] || statusConfig.pending;

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
  const isWebSearch =
    (toolCall.name === "web_search" || toolCall.name === "search_web") &&
    toolCall.status === "completed" &&
    typeof toolCall.result === "string";

  const hasSpecialRenderer = isDateTime || isRAGSearch || isWebSearch;

  return (
    <Card className="bg-muted/50">
      <CardHeader className="py-2 px-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isDateTime ? (
              <Clock className="h-4 w-4 text-primary" />
            ) : isRAGSearch ? (
              <Search className="h-4 w-4 text-primary" />
            ) : isWebSearch ? (
              <Globe className="h-4 w-4 text-primary" />
            ) : (
              <Wrench className="h-4 w-4 text-muted-foreground" />
            )}
            <CardTitle className="text-sm font-medium">
              {isDateTime
                ? "Current Date & Time"
                : isRAGSearch
                ? "Knowledge Base Search"
                : isWebSearch
                ? "Web Search"
                : toolCall.name}
            </CardTitle>
            {(isRAGSearch || isWebSearch) && toolCall.args?.query ? (
              <span className="text-xs text-muted-foreground italic truncate max-w-[200px]">
                &ldquo;{String(toolCall.args.query)}&rdquo;
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-1">
            {hasSpecialRenderer && toolCall.status === "completed" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setShowRaw(!showRaw)}
                title={showRaw ? "Show formatted" : "Show raw"}
              >
                {showRaw ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            )}
            <StatusIcon
              className={cn("h-4 w-4", color, animate && "animate-spin")}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="py-2 px-3">
        {/* Specialized rendering */}
        {toolCall.status === "completed" && !showRaw && isDateTime && (
          <DateTimeResult result={resultText} />
        )}
        {toolCall.status === "completed" && !showRaw && isRAGSearch && (
          <RAGSearchResults result={resultText} />
        )}
        {toolCall.status === "completed" && !showRaw && isWebSearch && (
          <WebSearchResults result={resultText} />
        )}

        {/* Raw/default rendering */}
        {(!hasSpecialRenderer || showRaw || toolCall.status !== "completed") && (
          <div className="space-y-2">
            {/* Arguments */}
            <div className="group relative">
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-muted-foreground">Arguments:</p>
                <CopyButton
                  text={JSON.stringify(toolCall.args, null, 2)}
                  className="opacity-0 group-hover:opacity-100"
                />
              </div>
              <pre className="text-xs bg-background p-2 rounded overflow-x-auto">
                {JSON.stringify(toolCall.args, null, 2)}
              </pre>
            </div>

            {/* Result */}
            {toolCall.result !== undefined && (
              <div className="group relative">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-xs text-muted-foreground">Result:</p>
                  <CopyButton
                    text={resultText}
                    className="opacity-0 group-hover:opacity-100"
                  />
                </div>
                <pre className="text-xs bg-background p-2 rounded overflow-x-auto max-h-48 overflow-y-auto">
                  {resultText}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
