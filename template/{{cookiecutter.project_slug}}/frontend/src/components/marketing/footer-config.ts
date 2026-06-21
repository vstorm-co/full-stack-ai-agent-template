import { BACKEND_URL, ROUTES } from "@/lib/constants";

/**
 * Translation-aware factories for marketing nav + footer.
 *
 * Hrefs live here (template-level), labels come from i18n messages
 * (`marketing.nav.*`, `marketing.footer.*`). Use the `build*` helpers
 * from any component — server or client — that has access to a `t()`.
 */

type T = (key: string) => string;

export interface FooterColumn {
  title: string;
  links: { label: string; href: string }[];
}

export function buildMarketingNavLinks(t: T) {
  return [
    { label: t("nav.platform"), href: `${ROUTES.HOME}#features` },
    { label: t("nav.solutions"), href: `${ROUTES.HOME}#how` },
    { label: t("nav.pricing"), href: ROUTES.PRICING },
{%- if cookiecutter.enable_marketing_site %}
    { label: t("nav.customers"), href: ROUTES.BLOG },
{%- endif %}
    { label: t("nav.resources"), href: `${ROUTES.HOME}#faq` },
  ];
}

/* -------------------------------------------------------------------------
   Rich navigation with mega-menu dropdowns.
   Icon keys map to lucide-react glyphs in `pill-nav.tsx`.
   ------------------------------------------------------------------------- */

export type NavIcon =
  | "sparkles"
  | "workflow"
  | "insights"
  | "changelog"
  | "support"
  | "sales"
  | "knowledge"
  | "research"
  | "help"
  | "api"
  | "security"
  | "community"
  | "blog";

export interface NavMenuItem {
  label: string;
  href: string;
  description?: string;
  icon?: NavIcon;
}

export interface NavItem {
  label: string;
  /** Set for a plain link. Mutually exclusive with `items`. */
  href?: string;
  /** Set for a dropdown trigger. */
  items?: NavMenuItem[];
  /** Optional CTA shown at the bottom of the dropdown panel. */
  featured?: { label: string; href: string };
}

export function buildMarketingNav(t: T): NavItem[] {
  return [
    {
      label: t("menu.product"),
      items: [
        {
          label: t("menu.items.overview.label"),
          description: t("menu.items.overview.desc"),
          href: `${ROUTES.HOME}#features`,
          icon: "sparkles",
        },
        {
          label: t("menu.items.howItWorks.label"),
          description: t("menu.items.howItWorks.desc"),
          href: `${ROUTES.HOME}#how`,
          icon: "workflow",
        },
        {
          label: t("menu.items.insights.label"),
          description: t("menu.items.insights.desc"),
          href: `${ROUTES.HOME}#features`,
          icon: "insights",
        },
        {
          label: t("menu.items.changelog.label"),
          description: t("menu.items.changelog.desc"),
          href: ROUTES.CHANGELOG,
          icon: "changelog",
        },
      ],
      featured: { label: t("menu.seePricing"), href: ROUTES.PRICING },
    },
    {
      label: t("menu.solutions"),
      items: [
        {
          label: t("menu.items.support.label"),
          description: t("menu.items.support.desc"),
          href: `${ROUTES.HOME}#how`,
          icon: "support",
        },
        {
          label: t("menu.items.sales.label"),
          description: t("menu.items.sales.desc"),
          href: `${ROUTES.HOME}#features`,
          icon: "sales",
        },
        {
          label: t("menu.items.knowledge.label"),
          description: t("menu.items.knowledge.desc"),
          href: `${ROUTES.HOME}#features`,
          icon: "knowledge",
        },
{%- if cookiecutter.enable_marketing_site %}
        {
          label: t("menu.items.research.label"),
          description: t("menu.items.research.desc"),
          href: ROUTES.CONTACT,
          icon: "research",
        },
{%- endif %}
      ],
{%- if cookiecutter.enable_marketing_site %}
      featured: { label: t("menu.talkToSales"), href: ROUTES.CONTACT },
{%- endif %}
    },
    { label: t("nav.pricing"), href: ROUTES.PRICING },
    {
      label: t("menu.resources"),
      items: [
{%- if cookiecutter.enable_marketing_site %}
        {
          label: t("footer.helpCenter"),
          description: t("menu.items.help.desc"),
          href: ROUTES.HELP,
          icon: "help",
        },
{%- endif %}
        {
          label: t("footer.apiDocs"),
          description: t("menu.items.api.desc"),
          href: `${BACKEND_URL}/docs`,
          icon: "api",
        },
{%- if cookiecutter.enable_marketing_site %}
        {
          label: t("nav.security"),
          description: t("menu.items.security.desc"),
          href: ROUTES.SECURITY,
          icon: "security",
        },
        {
          label: t("nav.community"),
          description: t("menu.items.community.desc"),
          href: ROUTES.COMMUNITY,
          icon: "community",
        },
        {
          label: t("nav.blog"),
          description: t("menu.items.blog.desc"),
          href: ROUTES.BLOG,
          icon: "blog",
        },
{%- endif %}
      ],
    },
  ];
}

export function buildFooterColumns(t: T): FooterColumn[] {
  return [
    {
      title: t("footer.product"),
      links: [
        { label: t("nav.features"), href: `${ROUTES.HOME}#features` },
        { label: t("nav.pricing"), href: ROUTES.PRICING },
        { label: t("nav.changelog"), href: ROUTES.CHANGELOG },
      ],
    },
{%- if cookiecutter.enable_marketing_site %}
    {
      title: t("footer.company"),
      links: [
        { label: t("nav.about"), href: ROUTES.ABOUT },
        { label: t("nav.blog"), href: ROUTES.BLOG },
        { label: t("nav.contact"), href: ROUTES.CONTACT },
      ],
    },
    {
      title: t("footer.resources"),
      links: [
        { label: t("footer.helpCenter"), href: ROUTES.HELP },
        { label: t("footer.apiDocs"), href: `${BACKEND_URL}/docs` },
        { label: t("nav.security"), href: ROUTES.SECURITY },
        { label: t("nav.community"), href: ROUTES.COMMUNITY },
      ],
    },
{%- else %}
    {
      title: t("footer.resources"),
      links: [
        { label: t("footer.apiDocs"), href: `${BACKEND_URL}/docs` },
      ],
    },
{%- endif %}
  ];
}

export function buildFooterLegal(t: T) {
  return [
{%- if cookiecutter.enable_marketing_site %}
    { label: t("footer.terms"), href: ROUTES.LEGAL_TERMS },
    { label: t("footer.privacy"), href: ROUTES.LEGAL_PRIVACY },
    { label: t("footer.cookies"), href: ROUTES.LEGAL_COOKIES },
{%- endif %}
  ];
}

/**
 * Social links rendered in the footer. Hrefs are placeholders — replace with
 * your real profiles (or remove entries you don't use). `icon` maps to a
 * lucide-react glyph in `marketing-footer.tsx`.
 */
export type SocialIcon = "x" | "github" | "linkedin";

export interface SocialLink {
  label: string;
  href: string;
  icon: SocialIcon;
}

export const SOCIAL_LINKS: SocialLink[] = [
  { label: "X (Twitter)", href: "https://x.com", icon: "x" },
  { label: "GitHub", href: "https://github.com", icon: "github" },
  { label: "LinkedIn", href: "https://linkedin.com", icon: "linkedin" },
];

/**
 * Compatibility exports — used by code paths that don't yet have access to a
 * translator (e.g. some test fixtures or the Sprint-3.5 migration). Defaults
 * to English; replace usages with `build*` helpers once refactored.
 */
const enFallback: T = (key) => {
  const en: Record<string, string> = {
    "nav.features": "Features",
    "nav.howItWorks": "How it works",
    "nav.pricing": "Pricing",
    "nav.faq": "FAQ",
    "nav.blog": "Blog",
    "nav.platform": "Platform",
    "nav.solutions": "Solutions",
    "nav.customers": "Customers",
    "nav.resources": "Resources",
    "nav.changelog": "Changelog",
    "nav.about": "About",
    "nav.contact": "Contact",
    "nav.security": "Security",
    "nav.community": "Community",
    "footer.product": "Product",
    "footer.company": "Company",
    "footer.resources": "Resources",
    "footer.helpCenter": "Help center",
    "footer.apiDocs": "API docs",
    "footer.terms": "Terms",
    "footer.privacy": "Privacy",
    "footer.cookies": "Cookies",
    "footer.tagline": "The AI assistant that knows your work.",
  };
  return en[key] ?? key;
};

export const MARKETING_NAV_LINKS = buildMarketingNavLinks(enFallback);
export const FOOTER_COLUMNS = buildFooterColumns(enFallback);
export const FOOTER_LEGAL = buildFooterLegal(enFallback);
export const FOOTER_TAGLINE = enFallback("footer.tagline");
