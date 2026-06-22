"use client";

{%- if cookiecutter.enable_charts %}
import { useEffect, useMemo, useState, type MouseEvent } from "react";
{%- else %}
import { useState, type MouseEvent } from "react";
{%- endif %}
import { Card, CardContent, Button } from "@/components/ui";
import type { ToolCall } from "@/types";
import {
  Wrench,
  Clock,
  Search,
  Globe,
  ChevronDown,
  ChevronUp,
  Code2,
  MessageCircleQuestion,
  Loader2,
  CheckCircle2,
  XCircle,
{%- if cookiecutter.enable_charts %}
  BarChart3,
{%- endif %}
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toolCaption } from "@/lib/agent-step-captions";
{%- if cookiecutter.enable_charts %}
import { ChartMessage, parseChartResult } from "./chart-message";
{%- endif %}
import { DateTimeResult } from "./tool-results/datetime";
import { RAGSearchResults } from "./tool-results/rag";
import { WebSearchResults, parseWebSearch } from "./tool-results/web-search";
{%- if cookiecutter.enable_skills %}
import { LoadSkillResult, formatSkillName } from "./tool-results/skills";
{%- endif %}
import { AskUserResult } from "./tool-results/ask-user";
import { GenericToolResult, RawToolView } from "./tool-results/generic";
{%- if cookiecutter.enable_code_execution %}
import { RunPythonResult } from "./tool-results/run-python";
{%- endif %}

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  // Collapsed by default — the bar acts as the toggle. `showRaw` swaps the
  // formatted view for args + raw output (the </> button). Charts are the
  // exception: they're only useful when visible, so expand them by default.
{%- if cookiecutter.enable_code_execution %}
  const isRunPython = toolCall.name === "run_python";
{%- endif %}
  const [expanded, setExpanded] = useState(
    toolCall.name === "ask_user" ||
{%- if cookiecutter.enable_code_execution %}
      (isRunPython && toolCall.status === "completed") ||
{%- endif %}
{%- if cookiecutter.enable_charts %}
      (toolCall.name === "create_chart_tool" &&
        toolCall.status === "completed" &&
        parseChartResult(toolCall.result) !== null),
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
    typeof urlArg === "string" ? urlArg : typeof queryArg === "string" ? queryArg : null;

  const resultText =
    toolCall.result !== undefined
      ? typeof toolCall.result === "string"
        ? toolCall.result
        : JSON.stringify(toolCall.result, null, 2)
      : "";

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
  const isLoadSkill = toolCall.name === "load_skill";
  const isListSkills = toolCall.name === "list_skills";
  const loadedSkillName =
    isLoadSkill && typeof toolCall.args?.skill_name === "string" ? toolCall.args.skill_name : null;
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

  const hasSpecialRenderer =
    isDateTime || isRAGSearch || isWebSearch || isAskUser{%- if cookiecutter.enable_charts %} || isChart{%- endif %}{%- if cookiecutter.enable_code_execution %} || isRunPython{%- endif %};
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
          : isAskUser
            ? MessageCircleQuestion
{%- if cookiecutter.enable_code_execution %}
            : isRunPython
              ? Code2
{%- endif %}
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

  // While still running: narrate what the agent is doing instead of the finished label,
  // and swap the chevron/raw toggle for a spinner — the header becomes a step caption.
  const isRunning = toolCall.status === "running" || toolCall.status === "pending";
  const isError = toolCall.status === "error";
  const liveCaption = toolCaption(toolCall.name);

  return (
    <Card
      className={cn(
        "bg-muted/50 step-card-in",
        isRunning && "border-brand/50 relative overflow-hidden",
      )}
    >
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
              isRunning
                ? "text-brand animate-pulse"
                : hasSpecialRenderer
                  ? "text-primary"
                  : "text-muted-foreground",
            )}
          />
          {isRunning ? (
            <span className="text-foreground/80 flex min-w-0 items-center gap-1.5 text-sm font-medium">
              <span className="truncate">{liveCaption}</span>
              <span className="flex shrink-0 gap-0.5" aria-hidden="true">
                <span className="bg-brand/70 h-1 w-1 animate-bounce rounded-full [animation-delay:0ms]" />
                <span className="bg-brand/70 h-1 w-1 animate-bounce rounded-full [animation-delay:150ms]" />
                <span className="bg-brand/70 h-1 w-1 animate-bounce rounded-full [animation-delay:300ms]" />
              </span>
            </span>
          ) : (
            <span className="truncate text-sm font-medium">{friendlyName}</span>
          )}
          {inputHint && !isRunning ? (
            <span className="text-muted-foreground min-w-0 flex-1 truncate text-xs italic">
              {inputHint}
            </span>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {isRunning ? (
            <Loader2 className="text-brand h-4 w-4 animate-spin" aria-label="Running" />
          ) : (
            <>
              {isError ? (
                <XCircle className="text-destructive pop-in h-4 w-4 shrink-0" aria-label="Failed" />
              ) : (
                <CheckCircle2 className="text-brand pop-in h-4 w-4 shrink-0" aria-label="Done" />
              )}
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "text-muted-foreground hover:bg-foreground/10 hover:text-foreground h-6 w-6 transition-colors",
                  showRaw && "text-primary",
                )}
                onClick={toggleRaw}
                title={showRaw ? "Show formatted view" : "Show arguments + raw output"}
                aria-label={showRaw ? "Show formatted view" : "Show arguments and raw output"}
              >
                <Code2 className="h-3.5 w-3.5" />
              </Button>
              {expanded ? (
                <ChevronUp className="text-muted-foreground h-4 w-4" />
              ) : (
                <ChevronDown className="text-muted-foreground h-4 w-4" />
              )}
            </>
          )}
        </div>
      </div>

      {/* Live progress shimmer — only while the step is in flight. */}
      {isRunning && (
        <div className="step-progress pointer-events-none absolute inset-x-0 bottom-0 h-0.5" />
      )}

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
          ) : isAskUser ? (
            <AskUserResult args={toolCall.args} resultText={resultText} />
{%- if cookiecutter.enable_code_execution %}
          ) : isRunPython ? (
            <RunPythonResult toolCall={toolCall} resultText={resultText} />
{%- endif %}
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
