/**
 * Memory file naming, mirroring what the agent's tools accept.
 *
 * The backend normalizes and enforces this too (`canonical_memory_filename`);
 * validating here just keeps the user from a round trip. A nested or oddly
 * shaped name is invisible to the agent, so it is rejected rather than stored.
 */

export const MAIN_NOTEBOOK = "MEMORY.md";
export const MAX_MEMORY_NAME_CHARS = 80;
export const MAX_MEMORY_CONTENT_CHARS = 65_536;

const NAME_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

/** Add the `.md` the backend would append, so names can be compared. */
export function canonicalMemoryName(name: string): string {
  const trimmed = name.trim();
  if (!trimmed || trimmed.endsWith(".md")) return trimmed;
  return `${trimmed}.md`;
}

export function isValidMemoryName(name: string): boolean {
  const canonical = canonicalMemoryName(name);
  return (
    canonical.length > 0 &&
    canonical.length <= MAX_MEMORY_NAME_CHARS &&
    NAME_PATTERN.test(canonical) &&
    !canonical.includes("..")
  );
}
