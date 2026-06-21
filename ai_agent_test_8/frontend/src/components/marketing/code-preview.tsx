"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

interface CodeTab {
  label: string;
  filename?: string;
  language: string;
  code: string;
}

interface CodePreviewProps {
  tabs: CodeTab[];
}

export function CodePreview({ tabs }: CodePreviewProps) {
  const [active, setActive] = useState(0);
  const [copied, setCopied] = useState(false);
  const tab = tabs[active];
  if (!tab) return null;

  const onCopy = async () => {
    await navigator.clipboard.writeText(tab.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div className="border-foreground/15 bg-card overflow-hidden rounded-2xl border shadow-2xl">
      <div className="border-foreground/10 flex items-center justify-between border-b">
        <ul className="flex">
          {tabs.map((t, i) => (
            <li key={t.label}>
              <button
                type="button"
                onClick={() => setActive(i)}
                className={cn(
                  "border-b-2 px-5 py-3 font-mono text-xs transition-colors",
                  i === active
                    ? "border-brand text-foreground"
                    : "text-foreground/55 hover:text-foreground/80 border-transparent",
                )}
              >
                {t.label}
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={onCopy}
          aria-label="Copy code"
          className="text-foreground/55 hover:text-foreground mr-3 inline-flex items-center gap-1.5 rounded px-2 py-1 font-mono text-xs transition-colors"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {tab.filename && (
        <div className="text-foreground/45 border-foreground/10 border-b px-5 py-2 font-mono text-xs">
          {tab.filename}
        </div>
      )}

      <pre className="text-foreground overflow-x-auto p-5 font-mono text-sm leading-relaxed">
        <code>{highlight(tab.code)}</code>
      </pre>
    </div>
  );
}

/** Lightweight tokenizer — keywords get brand color, comments dimmed.
 *  Supports bash, yaml/dockerfile, http. Not a full lexer; aims for taste. */
function highlight(code: string) {
  const lines = code.split("\n");
  return lines.map((line, i) => (
    <span key={i} className="block">
      {tokenize(line)}
      {"\n"}
    </span>
  ));
}

function tokenize(line: string) {
  if (/^\s*#/.test(line)) {
    return <span className="text-foreground/40 italic">{line}</span>;
  }
  if (/^\$\s/.test(line)) {
    return (
      <>
        <span className="text-brand">$</span>
        <span>{line.slice(1)}</span>
      </>
    );
  }
  // Keyword highlighting (simple): commands, http verbs
  const KEYWORDS =
    /\b(uv|pip|docker|compose|run|build|up|down|exec|curl|GET|POST|PATCH|DELETE|fastapi-fullstack|create|FROM|RUN|WORKDIR|COPY|CMD|EXPOSE)\b/g;
  const STRINGS = /"([^"]*)"/g;
  const out: (string | React.ReactNode)[] = [];
  let cursor = 0;
  const matches: { start: number; end: number; node: React.ReactNode }[] = [];
  let m: RegExpExecArray | null;
  KEYWORDS.lastIndex = 0;
  while ((m = KEYWORDS.exec(line)) !== null) {
    matches.push({
      start: m.index,
      end: m.index + m[0].length,
      node: (
        <span key={`k-${m.index}`} className="text-brand font-medium">
          {m[0]}
        </span>
      ),
    });
  }
  STRINGS.lastIndex = 0;
  while ((m = STRINGS.exec(line)) !== null) {
    matches.push({
      start: m.index,
      end: m.index + m[0].length,
      node: (
        <span key={`s-${m.index}`} className="text-foreground/70">
          {m[0]}
        </span>
      ),
    });
  }
  matches.sort((a, b) => a.start - b.start);
  for (const match of matches) {
    if (cursor < match.start) out.push(line.slice(cursor, match.start));
    out.push(match.node);
    cursor = match.end;
  }
  if (cursor < line.length) out.push(line.slice(cursor));
  return out.length > 0 ? out : line;
}
