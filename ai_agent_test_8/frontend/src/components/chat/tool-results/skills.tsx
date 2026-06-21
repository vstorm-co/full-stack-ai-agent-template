"use client";

/** "market_data" -> "Market Data", "fire" -> "Fire". */
export function formatSkillName(name: string): string {
  return name
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Extract the description text from a `load_skill` XML result.
 *  The library returns <skill><name>…</name><description>…</description>…</skill>. */
export function parseLoadSkillResult(result: string): { description: string } | null {
  const m = result.match(/<description>([\s\S]*?)<\/description>/);
  if (!m?.[1]) return null;
  return { description: m[1].trim() };
}

/** Clean card for a loaded skill — just the description, no raw XML. */
export function LoadSkillResult({ resultText, status }: { resultText: string; status: string }) {
  if (!resultText || status !== "completed") {
    return (
      <p className="text-muted-foreground py-2 text-xs italic">
        {status === "error" ? "Failed to load skill." : "Loading…"}
      </p>
    );
  }
  const parsed = parseLoadSkillResult(resultText);
  if (!parsed) return null;

  return (
    <p className="text-foreground/75 py-1 text-[13px] leading-relaxed">{parsed.description}</p>
  );
}
