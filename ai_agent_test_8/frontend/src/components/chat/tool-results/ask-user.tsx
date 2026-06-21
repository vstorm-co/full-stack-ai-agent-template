"use client";

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
export function AskUserResult({ args, resultText }: { args: unknown; resultText: string }) {
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
