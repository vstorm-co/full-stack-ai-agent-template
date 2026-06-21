"use client";
import type { ToolCall } from "@/types";
import { MarkdownContent } from "../markdown-content";
import { CopyButton } from "../copy-button";

interface Parsed {
  stdout: string | null;
  result: string | null;
  error: string | null;
}

function parseResult(text: string): Parsed {
  if (!text || text === "(code ran successfully with no output)") {
    return { stdout: null, result: null, error: null };
  }
  if (text.startsWith("Execution failed:")) {
    return { stdout: null, result: null, error: text };
  }

  // Format: "stdout:\n<text>" optionally followed by "\n\nresult: <value>"
  if (text.startsWith("stdout:\n")) {
    const body = text.slice("stdout:\n".length);
    const sep = body.indexOf("\n\nresult: ");
    if (sep !== -1) {
      return {
        stdout: body.slice(0, sep).trim(),
        result: body.slice(sep + "\n\nresult: ".length).trim(),
        error: null,
      };
    }
    return { stdout: body.trim(), result: null, error: null };
  }

  // Format: "result: <value>"
  if (text.startsWith("result: ")) {
    return { stdout: null, result: text.slice("result: ".length).trim(), error: null };
  }

  // Fallback: treat entire text as stdout
  return { stdout: text, result: null, error: null };
}

export function RunPythonResult({
  toolCall,
  resultText,
}: {
  toolCall: ToolCall;
  resultText: string;
}) {
  const code = typeof toolCall.args?.code === "string" ? toolCall.args.code.trim() : null;
  const isRunning = toolCall.status !== "completed" && !resultText;

  if (isRunning) {
    return <p className="text-muted-foreground py-2 text-xs italic">Running…</p>;
  }

  const { stdout, result, error } = parseResult(resultText);
  const outputText = [stdout, result ? `result: ${result}` : null].filter(Boolean).join("\n\n");

  return (
    <div className="space-y-2 pt-1">
      {code && <MarkdownContent content={"```python\n" + code + "\n```"} />}

      {error && (
        <div className="bg-destructive/8 text-destructive rounded-lg p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
          {error}
        </div>
      )}

      {outputText && (
        <div className="group relative">
          <div className="border-border bg-muted overflow-hidden rounded-xl border">
            <div className="border-foreground/8 text-foreground/55 flex items-center justify-between border-b px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
              <span>Output</span>
              <CopyButton text={outputText} className="opacity-0 group-hover:opacity-100" />
            </div>
            <pre className="text-foreground/85 scrollbar-thin max-h-80 overflow-y-auto p-3.5 font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap">
              {outputText}
            </pre>
          </div>
        </div>
      )}

      {!code && !error && !outputText && resultText && (
        <p className="text-muted-foreground py-2 text-xs italic">{resultText}</p>
      )}
    </div>
  );
}
