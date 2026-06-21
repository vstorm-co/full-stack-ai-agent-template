/**
 * Centralized, typed React Query key factory.
 *
 * One source of truth for cache keys so queries dedupe and mutations can
 * invalidate precisely (e.g. `queryClient.invalidateQueries({ queryKey: qk.billing.credits() })`).
 * Keep keys hierarchical: broader prefixes invalidate everything beneath them.
 */
export const qk = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  health: () => ["health"] as const,
  organizations: {
    all: () => ["organizations"] as const,
    list: () => ["organizations", "list"] as const,
    members: (orgId: string) => ["organizations", orgId, "members"] as const,
  },
  invitations: {
    all: () => ["invitations"] as const,
    list: (orgId: string) => ["invitations", orgId] as const,
  },
  billing: {
    all: () => ["billing"] as const,
    credits: () => ["billing", "credits"] as const,
    creditsTransactions: () => ["billing", "credits", "transactions"] as const,
    subscription: () => ["billing", "subscription"] as const,
    invoices: () => ["billing", "invoices"] as const,
    paymentMethods: () => ["billing", "payment-methods"] as const,
    usageTimeline: (days: number) => ["billing", "usage", "timeline", days] as const,
  },
  conversations: {
    all: () => ["conversations"] as const,
    list: () => ["conversations", "list"] as const,
    count: () => ["conversations", "count"] as const,
    messages: (id: string) => ["conversations", id, "messages"] as const,
  },
  conversationShares: {
    all: () => ["conversation-shares"] as const,
    list: (conversationId: string) => ["conversation-shares", conversationId] as const,
    sharedWithMe: (skip: number, limit: number) =>
      ["conversation-shares", "shared-with-me", skip, limit] as const,
  },
  kb: {
    all: () => ["kb"] as const,
    list: () => ["kb", "list"] as const,
    detail: (id: string) => ["kb", id] as const,
    documents: (id: string) => ["kb", id, "documents"] as const,
  },
  rag: {
    stats: () => ["rag", "stats"] as const,
    collections: () => ["rag", "collections"] as const,
  },
  slashCommands: {
    list: () => ["slash-commands", "list"] as const,
  },
  admin: {
    stats: () => ["admin", "stats"] as const,
    events: () => ["admin", "events"] as const,
    users: (params?: unknown) => ["admin", "users", params] as const,
    conversations: (params?: unknown) => ["admin", "conversations", params] as const,
  },
} as const;
