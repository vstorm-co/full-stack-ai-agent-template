/**
 * Skills load through pydantic-ai-skills' `load_capability` tool: its argument is
 * the skill's `id`, and its result is `{"instructions": "# Skill: <id>\n\n…"}` —
 * which reaches the frontend as the Python repr (`str(value)`) or as JSON.
 */

export const LOAD_SKILL_TOOL = "load_capability";

const INSTRUCTIONS = /["']instructions["']\s*:\s*(["'])([\s\S]*)\1\s*}\s*$/;

/** The skill's instructions from a `load_capability` result, or null. */
export function loadedSkillInstructions(result: string): string | null {
  const body = INSTRUCTIONS.exec(result.trim())?.[2];
  if (body === undefined) return null;
  return body
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\(["'\\])/g, "$1");
}

/** A one-paragraph summary of a loaded skill — its instructions without the heading. */
export function loadedSkillSummary(result: string): string | null {
  const instructions = loadedSkillInstructions(result);
  if (instructions === null) return null;
  const paragraphs = instructions
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p && !/^#\s*Skill:/i.test(p));
  return paragraphs[0] ?? null;
}
