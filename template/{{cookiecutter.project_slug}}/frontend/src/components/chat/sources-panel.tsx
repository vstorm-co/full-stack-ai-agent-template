"use client";

import { useEffect, useRef } from "react";
import { FileText, Globe, Link, X } from "lucide-react";
import { useSourcesPanelStore } from "@/stores/sources-panel-store";
import type { SourceItem } from "@/lib/chat-sources";
import { cn } from "@/lib/utils";

function ScoreDot({ score }: { score: number }) {
  const tone =
    score >= 0.7 ? "bg-foreground" : score >= 0.4 ? "bg-foreground/55" : "bg-foreground/25";
  return (
    <span
      className={cn("h-1.5 w-1.5 shrink-0 rounded-full", tone)}
      title={`Relevance: ${score.toFixed(2)}`}
    />
  );
}

function RAGSourceRow({
  item,
  highlighted,
}: {
  item: SourceItem;
  highlighted: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (highlighted) {
      ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [highlighted]);

  return (
    <div
      ref={ref}
      className={cn(
        "border-foreground/8 rounded-xl border p-3 transition-colors",
        highlighted && "border-foreground/30 bg-foreground/[0.04]",
      )}
    >
      <div className="flex items-start gap-2.5">
        <span className="bg-foreground/8 text-foreground/65 mt-0.5 inline-flex h-5 min-w-[1.5rem] shrink-0 items-center justify-center rounded px-1 font-mono text-[10px] tabular-nums">
          {item.index}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <FileText className="text-foreground/40 h-3.5 w-3.5 shrink-0" />
            <p className="text-foreground truncate text-xs font-medium" title={item.title}>
              {item.title}
            </p>
            {item.score !== undefined && <ScoreDot score={item.score} />}
          </div>
          {item.subtitle && (
            <p className="text-foreground/45 mt-0.5 pl-5 font-mono text-[10px] tracking-wider uppercase">
              {item.subtitle}
            </p>
          )}
          {item.content && (
            <p className="text-foreground/60 mt-2 pl-5 text-[11px] leading-relaxed">
              {item.content}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function WebSourceRow({
  item,
  highlighted,
}: {
  item: SourceItem;
  highlighted: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (highlighted) {
      ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [highlighted]);

  const inner = (
    <div
      ref={ref}
      className={cn(
        "border-foreground/8 rounded-xl border p-3 transition-colors",
        highlighted && "border-foreground/30 bg-foreground/[0.04]",
        item.url && "hover:border-foreground/25 cursor-pointer",
      )}
    >
      <div className="flex items-start gap-2.5">
        <Globe className="text-foreground/40 mt-0.5 h-3.5 w-3.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate text-xs font-medium" title={item.title}>
            {item.title}
          </p>
          {item.subtitle && (
            <div className="text-foreground/45 mt-0.5 flex items-center gap-1 text-[10px]">
              <Link className="h-2.5 w-2.5 shrink-0" />
              {item.subtitle}
            </div>
          )}
          {item.content && (
            <p className="text-foreground/60 mt-2 line-clamp-3 text-[11px] leading-relaxed">
              {item.content}
            </p>
          )}
        </div>
      </div>
    </div>
  );

  if (item.url) {
    return (
      <a href={item.url} target="_blank" rel="noopener noreferrer">
        {inner}
      </a>
    );
  }
  return inner;
}

export function SourcesPanel() {
  const { isOpen, sources, highlightedIndex, close } = useSourcesPanelStore();

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, close]);

  if (!isOpen) return null;

  const ragSources = sources.filter((s) => s.type === "rag");
  const webSources = sources.filter((s) => s.type === "web");

  return (
    <div className="bg-background border-border fixed top-0 right-0 z-50 flex h-full w-[360px] flex-col border-l shadow-xl">
      {/* Header */}
      <div className="border-foreground/8 flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-foreground text-sm font-semibold">
          Sources
          <span className="text-foreground/45 ml-2 font-normal">({sources.length})</span>
        </h2>
        <button
          type="button"
          onClick={close}
          aria-label="Close sources panel"
          className="text-foreground/50 hover:text-foreground hover:bg-foreground/8 rounded-md p-1 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
        {ragSources.length > 0 && (
          <section className="space-y-2">
            {ragSources.length > 0 && webSources.length > 0 && (
              <h3 className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
                Knowledge base
              </h3>
            )}
            {ragSources.map((s) => (
              <RAGSourceRow
                key={`rag-${s.index}`}
                item={s}
                highlighted={s.index === highlightedIndex}
              />
            ))}
          </section>
        )}

        {webSources.length > 0 && (
          <section className="space-y-2">
            {ragSources.length > 0 && (
              <h3 className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
                Web
              </h3>
            )}
            {webSources.map((s) => (
              <WebSourceRow
                key={`web-${s.index}`}
                item={s}
                highlighted={s.index === highlightedIndex}
              />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
