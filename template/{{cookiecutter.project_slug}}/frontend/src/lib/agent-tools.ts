/**
 * Shared tool-name predicates for the agent's web tools.
 *
 * `web_search_tool` / `search_web` are the app's structured Tavily tool; `duckduckgo_search`
 * is the pydantic-ai builtin (its result is a Python-repr list). `web_fetch` is the pydantic-ai
 * builtin that opens a single page (result is a Python-repr `{url,title,content}` dict);
 * `fetch_url` / `fetch` are the legacy names for the same idea.
 */

export const WEB_SEARCH_TOOLS = new Set(["web_search_tool", "search_web", "duckduckgo_search"]);
export const FETCH_TOOLS = new Set(["web_fetch", "fetch_url", "fetch"]);

export const isWebSearchTool = (name: string | undefined | null): boolean =>
  !!name && WEB_SEARCH_TOOLS.has(name);

export const isFetchTool = (name: string | undefined | null): boolean =>
  !!name && FETCH_TOOLS.has(name);
