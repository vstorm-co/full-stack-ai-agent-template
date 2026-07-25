/**
 * Curated MCP plugin catalog — the "marketplace" shown in Settings → Integrations.
 *
 * Every entry here was verified to work with our client. The transport
 * (streamable HTTP or SSE) is inferred from the URL on the backend, so
 * SSE-only servers such as Atlassian/Jira sit alongside the rest.
 * The URL is baked in so non-technical users never see it; entries with
 * `auth: "token"` show a single token field plus a direct link to the page
 * where the token is generated.
 */

import { MCP_LOGOS } from "./mcp-logos.generated";

export type McpCatalogCategory = "business" | "research" | "finance" | "developer";

/** Display order + labels for the catalog section headings. */
export const MCP_CATEGORIES: { id: McpCatalogCategory; label: string }[] = [
  { id: "business", label: "Business & work" },
  { id: "research", label: "Research & docs" },
  { id: "finance", label: "Finance & markets" },
  { id: "developer", label: "Developer" },
];

export interface McpCatalogEntry {
  /** Stable id — also used as the default connection name (slug). */
  id: string;
  /** Which section heading this card appears under. */
  category: McpCatalogCategory;
  title: string;
  /** Brand domain the color logo is keyed by (see {@link logoDataUri}). */
  domain: string;
  description: string;
  /**
   * For tokenPlacement: "url" this contains a `{token}` placeholder.
   * For auth: "personal-url" this is empty — the user pastes their own link.
   */
  url: string;
  auth: "none" | "token" | "personal-url" | "oauth";
  /**
   * Where the token goes: Authorization Bearer header (default) or embedded
   * into the URL (some providers, e.g. Alpha Vantage, take ?apikey=...).
   */
  tokenPlacement?: "header" | "url";
  /** For auth: "token" / "personal-url" — where to generate the credential. */
  tokenHelp?: { label: string; url: string };
  /** Short "what you can ask" example shown on the card. */
  example?: string;
}

/** Base URL (no query string) — used to match catalog entries to connections. */
export function catalogBaseUrl(url: string): string {
  const queryStart = url.indexOf("?");
  return queryStart === -1 ? url : url.slice(0, queryStart);
}

/**
 * Last-resort logo source: Google's favicon service, tokenless and over HTTPS.
 * Only reached for a domain missing from {@link MCP_LOGOS} — every catalog
 * entry should be baked in, so hitting this means `bun run gen:mcp-logos`
 * needs a re-run. Not exported: nothing should request it on purpose.
 */
function faviconServiceUrl(domain: string): string {
  return `https://www.google.com/s2/favicons?sz=128&domain=${encodeURIComponent(domain)}`;
}

/**
 * Brand logo for a catalog domain, as a baked-in data URI ({@link MCP_LOGOS}).
 *
 * Used everywhere a catalog logo is shown — the Settings marketplace and the
 * demo-only MCP badge alike. Baked rather than fetched for two reasons: the
 * self-contained export has no network, and a live app shouldn't tell a third
 * party which plugins its users are looking at. Regenerate the map with
 * `bun run gen:mcp-logos` after adding a catalog entry.
 */
export function logoDataUri(domain: string): string {
  return MCP_LOGOS[domain] ?? faviconServiceUrl(domain);
}

/** Catalog id / connection name → tool prefix (mirrors the backend `_tool_prefix`). */
function toToolPrefix(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, "_")
      .replace(/^_+|_+$/g, "") || "mcp"
  );
}

/**
 * Match a tool-call name to a known catalog server by its `{prefix}_` prefix.
 *
 * Purely static — it reads only {@link MCP_CATALOG}, never live connections — so
 * it works identically in a live chat, the `/demo` replay and the self-contained
 * export (which has no backend). Catalog-connected servers keep their id as the
 * connection name, so the tool prefix is `toToolPrefix(entry.id)`. Returns the
 * matched entry plus the prefix (longest wins), or `null` for built-in tools or
 * servers not in the catalog (custom URLs have no brand logo to show).
 */
export function matchCatalogMcpTool(
  toolName: string,
): { entry: McpCatalogEntry; prefix: string } | null {
  let best: { entry: McpCatalogEntry; prefix: string } | null = null;
  for (const entry of MCP_CATALOG) {
    const prefix = toToolPrefix(entry.id);
    if (toolName === prefix || toolName.startsWith(`${prefix}_`)) {
      if (!best || prefix.length > best.prefix.length) best = { entry, prefix };
    }
  }
  return best;
}

export const MCP_CATALOG: McpCatalogEntry[] = [
  {
    id: "coingecko",
    category: "finance",
    title: "CoinGecko",
    domain: "coingecko.com",
    description: "Live cryptocurrency prices, market caps and trends — no account needed.",
    url: "https://mcp.api.coingecko.com/mcp",
    auth: "none",
    example: "“What's the Bitcoin price and how did it move this week?”",
  },
  {
    id: "alphavantage",
    category: "finance",
    title: "Alpha Vantage",
    domain: "alphavantage.co",
    description: "Stock quotes, forex and market data. Free API key — just enter your email.",
    url: "https://mcp.alphavantage.co/mcp?apikey={token}",
    auth: "token",
    tokenPlacement: "url",
    tokenHelp: {
      label: "Get a free API key (takes 30 seconds)",
      url: "https://www.alphavantage.co/support/#api-key",
    },
    example: "“Compare Apple and Microsoft stock over the last month.”",
  },
  {
    id: "stripe",
    category: "business",
    title: "Stripe",
    domain: "stripe.com",
    description: "Your Stripe payments, customers and invoices — for business owners.",
    url: "https://mcp.stripe.com/",
    auth: "token",
    tokenHelp: {
      label: "Get your API key from the Stripe dashboard",
      url: "https://dashboard.stripe.com/apikeys",
    },
    example: "“How many new customers did we get this month?”",
  },
  {
    id: "notion",
    category: "business",
    title: "Notion",
    domain: "notion.so",
    description: "Your Notion pages, docs and databases — sign in, no token to copy.",
    url: "https://mcp.notion.com/mcp",
    auth: "oauth",
    example: "“Summarize our product spec doc in Notion.”",
  },
  {
    id: "linear",
    category: "business",
    title: "Linear",
    domain: "linear.app",
    description: "Issues, projects and cycles in Linear — sign in with your account.",
    url: "https://mcp.linear.app/mcp",
    auth: "oauth",
    example: "“What issues are assigned to me this cycle?”",
  },
  {
    id: "jira",
    category: "business",
    title: "Jira & Confluence",
    domain: "atlassian.com",
    description:
      "Atlassian issues, boards, sprints and Confluence pages — sign in with your account.",
    url: "https://mcp.atlassian.com/v1/sse",
    auth: "oauth",
    example: "“What Jira issues are assigned to me in the current sprint?”",
  },
  {
    id: "zapier",
    category: "business",
    title: "Zapier (Slack, Sheets, Gmail…)",
    domain: "zapier.com",
    description:
      "Connect 7000+ business apps — Slack, Google Sheets, Gmail, HubSpot, Salesforce, Trello. Pick your apps on Zapier, then paste your personal link here.",
    url: "",
    auth: "personal-url",
    tokenHelp: {
      label: "Create your personal MCP link on Zapier",
      url: "https://mcp.zapier.com",
    },
    example: "“Add a row to my Google Sheet from this conversation.”",
  },
  {
    id: "exa",
    category: "research",
    title: "Exa Search",
    domain: "exa.ai",
    description:
      "Live web search and page reading — great for market research, competitor checks and fact-finding.",
    url: "https://mcp.exa.ai/mcp",
    auth: "none",
    example: "“Find recent news about our top three competitors.”",
  },
  {
    id: "deepwiki",
    category: "research",
    title: "DeepWiki",
    domain: "deepwiki.com",
    description: "Ask questions about any public GitHub repository's code and docs.",
    url: "https://mcp.deepwiki.com/mcp",
    auth: "none",
    example: "“What does the documentation of facebook/react say about hooks?”",
  },
  {
    id: "context7",
    category: "research",
    title: "Context7",
    domain: "context7.com",
    description: "Up-to-date documentation for programming libraries and frameworks.",
    url: "https://mcp.context7.com/mcp",
    auth: "none",
    example: "“How do I set up middleware in Next.js 15? Check the docs.”",
  },
  {
    id: "huggingface",
    category: "developer",
    title: "Hugging Face",
    domain: "huggingface.co",
    description: "Search models, datasets and papers on the Hugging Face Hub.",
    url: "https://huggingface.co/mcp",
    auth: "none",
    example: "“Find the most downloaded text-to-speech models.”",
  },
  {
    id: "microsoft-docs",
    category: "research",
    title: "Microsoft Learn",
    domain: "learn.microsoft.com",
    description: "Official Microsoft / Azure documentation search and code samples.",
    url: "https://learn.microsoft.com/api/mcp",
    auth: "none",
    example: "“How do I configure a managed identity for an Azure Function?”",
  },
  {
    id: "cloudflare-docs",
    category: "developer",
    title: "Cloudflare Docs",
    domain: "cloudflare.com",
    description: "Search Cloudflare documentation — Workers, Pages, DNS, security.",
    url: "https://docs.mcp.cloudflare.com/mcp",
    auth: "none",
    example: "“How do I set up a cron trigger for a Worker?”",
  },
  {
    id: "github",
    category: "developer",
    title: "GitHub",
    domain: "github.com",
    description: "Your repositories, issues and pull requests — needs a personal access token.",
    url: "https://api.githubcopilot.com/mcp/",
    auth: "token",
    tokenHelp: {
      label: "Generate a token on GitHub",
      url: "https://github.com/settings/tokens",
    },
    example: "“List open pull requests in my repository.”",
  },
];
