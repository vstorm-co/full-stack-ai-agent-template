/**
 * Human-readable captions narrating what the agent is doing "under the hood"
 * while a tool runs. Used by the live agent-step animation to label each step
 * in plain language. Dependency-free — safe to use anywhere in the UI.
 */

const EXACT_CAPTIONS: Record<string, string> = {
  search_knowledge_base: "Searching the knowledge base",
  search_documents: "Searching the documents",
  web_search_tool: "Searching the web",
  search_web: "Searching the web",
  fetch_url: "Reading a web page",
  get_current_datetime: "Checking the date and time",
  run_python: "Running calculations",
  create_chart_tool: "Creating a chart",
  create_map_tool: "Drawing a map",
  ask_user: "Asking you a question",
  load_skill: "Loading a skill",
};

/** Prefix-based fallbacks for tools like `generate_*`. */
const PREFIX_CAPTIONS: ReadonlyArray<readonly [string, string]> = [
  ["generate_", "Generating a chart"],
  ["search_", "Searching"],
  ["create_", "Creating"],
  ["fetch_", "Fetching data"],
  ["get_", "Looking that up"],
  ["list_", "Looking that up"],
];

function humanizeToolName(name: string): string {
  const words = name
    .replace(/_tool$/, "")
    .split("_")
    .filter(Boolean);
  if (words.length === 0) return name;
  return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

/**
 * Present-tense phrase describing what the agent is doing while `toolName` runs.
 * Falls back to "Running <Tool Name>" for unknown tools.
 */
export function toolCaption(toolName: string): string {
  const exact = EXACT_CAPTIONS[toolName];
  if (exact) return exact;
  for (const [prefix, caption] of PREFIX_CAPTIONS) {
    if (toolName.startsWith(prefix)) return caption;
  }
  return `Running ${humanizeToolName(toolName)}`;
}
