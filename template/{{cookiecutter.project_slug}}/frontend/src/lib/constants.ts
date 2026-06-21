export const APP_NAME = "{{ cookiecutter.project_name }}";
export const APP_DESCRIPTION = "{{ cookiecutter.project_description }}";

export const API_ROUTES = {
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",
  HEALTH: "/health",
  USERS: "/users",
  CHAT: "/chat",
} as const;

export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  FORGOT_PASSWORD: "/forgot-password",
  DASHBOARD: "/dashboard",
  CHAT: "/chat",
  PROFILE: "/profile",
  SETTINGS: "/settings",
  SETTINGS_PROFILE: "/settings/profile",
  SETTINGS_ACCOUNT: "/settings/account",
  SETTINGS_APPEARANCE: "/settings/appearance",
  SETTINGS_NOTIFICATIONS: "/settings/notifications",
  SETTINGS_SLASH_COMMANDS: "/settings/slash-commands",
  RAG: "/rag",
  ADMIN: "/admin",
  ADMIN_USERS: "/admin/users",
  ADMIN_CONVERSATIONS: "/admin/conversations",
  ADMIN_RATINGS: "/admin/ratings",
  ADMIN_STRIPE_EVENTS: "/admin/stripe-events",
  ADMIN_SYSTEM: "/admin/system",
  ORGS: "/orgs",
  ORGS_CREATE: "/orgs?create=1",
  ORG_MEMBERS: (id: string) => `/orgs/${id}/members`,
  ORG_INTEGRATIONS: (id: string) => `/orgs/${id}/integrations`,
  ORG_SETTINGS: (id: string) => `/orgs/${id}/settings`,
  KB: "/kb",
  KB_DETAIL: (id: string) => `/kb/${id}`,
  BILLING: "/billing",
  BILLING_USAGE: "/billing/usage",
  BILLING_CREDITS: "/billing/credits",
  BILLING_INVOICES: "/billing/invoices",
  BILLING_PAYMENT_METHODS: "/billing/payment-methods",
  BILLING_SUBSCRIPTION: "/billing/subscription",
  PRICING: "/pricing",
  ABOUT: "/about",
  CONTACT: "/contact",
  HELP: "/help",
  CHANGELOG: "/changelog",
  COMMUNITY: "/community",
  ONBOARDING: "/onboarding/welcome",
  LEGAL_TERMS: "/legal/terms",
  LEGAL_PRIVACY: "/legal/privacy",
  LEGAL_COOKIES: "/legal/cookies",
  BLOG: "/blog",
  BLOG_POST: (slug: string) => `/blog/${slug}`,
  SECURITY: "/security",
} as const;

// WebSocket URL (for chat - direct to backend, use wss:// in production)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:{{ cookiecutter.backend_port }}";

// Backend API URL (public, for direct links like API docs)
export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:{{ cookiecutter.backend_port }}";
