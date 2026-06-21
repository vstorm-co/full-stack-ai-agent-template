/**
 * Single source of truth for changelog entries shown on /changelog.
 *
 * Sorted newest-first. Each release has a version + date + title + optional
 * description + a flat list of typed changes. Add new entries at the top.
 *
 * Type tags drive the colored pill on the marketing page. Recognized values:
 *   - feat        new functionality
 *   - improvement enhancement to existing feature
 *   - fix         bug fix
 *   - chore       infra / refactor (rendered subdued)
 *   - security    security patch (rendered with destructive tone)
 */

export type ChangeType = "feat" | "improvement" | "fix" | "chore" | "security";

export interface ChangelogEntry {
  version: string;
  date: string; // YYYY-MM-DD
  title: string;
  description?: string;
  changes: { type: ChangeType; text: string }[];
}

export const CHANGELOG: ChangelogEntry[] = [
  {
    version: "1.4.0",
    date: "2026-05-08",
    title: "Marketing site, blog, legal",
    description:
      "Full marketing surface — about, contact, help, blog (MDX), legal pages, cookie banner. New blog posts and updated FAQ.",
    changes: [
      { type: "feat", text: "Blog with MDX, frontmatter, related posts, reading-time estimates" },
      {
        type: "feat",
        text: "Cookie banner with granular consent (essential / analytics / functional)",
      },
      {
        type: "feat",
        text: "Legal pages: terms, privacy, cookie policy with prose-marketing typography",
      },
      { type: "feat", text: "About, help, contact, security, community pages" },
      { type: "improvement", text: "API docs link in footer now redirects to backend Swagger UI" },
      { type: "improvement", text: "Sitemap.xml includes blog posts with per-post lastModified" },
    ],
  },
  {
    version: "1.3.0",
    date: "2026-05-07",
    title: "Admin tools",
    description: "Power-user admin surface: users, conversations, Stripe events, system health.",
    changes: [
      { type: "feat", text: "Admin shared layout with sidebar nav" },
      { type: "feat", text: "User detail drawer with suspend / promote / impersonate / delete" },
      { type: "feat", text: "Stripe events log with replay action and Stripe deep link" },
      { type: "feat", text: "System health page with live readiness probe and per-service status" },
      { type: "improvement", text: "Branded admin user table with click-to-inspect rows" },
      { type: "fix", text: "Type error in admin user list response shape" },
    ],
  },
  {
    version: "1.2.0",
    date: "2026-05-06",
    title: "Settings tabs + billing redesign",
    changes: [
      {
        type: "feat",
        text: "Settings split into Profile / Account / API keys / Notifications / Integrations / Appearance",
      },
      { type: "feat", text: "API key manager with reveal-once dialog and clipboard confirmation" },
      { type: "feat", text: "Brand color preset switcher (5 themes, runtime swap)" },
      {
        type: "feat",
        text: "Billing hub with usage gauges, sub-route quick links, recent invoices",
      },
      { type: "improvement", text: "Credits page shows 30-day sparkline and week-over-week delta" },
    ],
  },
  {
    version: "1.1.0",
    date: "2026-05-05",
    title: "Chat polish + RAG",
    changes: [
      { type: "feat", text: "Chat empty state with example prompts" },
      { type: "feat", text: "Regenerate action on the most recent assistant message" },
      { type: "feat", text: "Drag-drop file upload overlay on RAG page" },
      { type: "feat", text: "3-step sync source wizard (provider / configure / schedule)" },
      { type: "improvement", text: "Branded chat input bottom-bar with pill status indicators" },
    ],
  },
  {
    version: "1.0.0",
    date: "2026-05-01",
    title: "Initial release",
    description: "First public release.",
    changes: [
      { type: "feat", text: "FastAPI + Next.js stack, JWT auth, organizations, RBAC" },
      {
        type: "feat",
        text: "AI agents (PydanticAI / LangChain / LangGraph / DeepAgents)",
      },
      { type: "feat", text: "RAG pipeline with Milvus / Qdrant / Chroma / pgvector" },
      { type: "feat", text: "Stripe billing with checkout, portal, credits, invoices" },
      { type: "feat", text: "Multi-tenant organizations with invitations and SSO-ready scaffold" },
    ],
  },
];
