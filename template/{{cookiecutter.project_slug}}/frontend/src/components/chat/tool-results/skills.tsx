"use client";

import { loadedSkillSummary } from "@/lib/skill-result";

/** "market_data" -> "Market Data", "fire" -> "Fire". */
export function formatSkillName(name: string): string {
  return name
    .split(/[_-]/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Clean card for a loaded skill — the start of its instructions, not the raw result. */
export function LoadSkillResult({ resultText, status }: { resultText: string; status: string }) {
  if (!resultText || status !== "completed") {
    return (
      <p className="text-muted-foreground py-2 text-xs italic">
        {status === "error" ? "Failed to load skill." : "Loading…"}
      </p>
    );
  }
  const summary = loadedSkillSummary(resultText);
  if (!summary) return null;

  return <p className="text-foreground/75 py-1 text-[13px] leading-relaxed">{summary}</p>;
}
