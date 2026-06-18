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
    { label: t("nav.customers"), href: "/blog" },
    { label: t("nav.resources"), href: `${ROUTES.HOME}#faq` },
  ];
}

export function buildFooterColumns(t: T): FooterColumn[] {
  return [
    {
      title: t("footer.product"),
      links: [
        { label: t("nav.features"), href: `${ROUTES.HOME}#features` },
        { label: t("nav.pricing"), href: ROUTES.PRICING },
        { label: t("nav.changelog"), href: "/changelog" },
      ],
    },
    {
      title: t("footer.company"),
      links: [
        { label: t("nav.about"), href: "/about" },
        { label: t("nav.blog"), href: "/blog" },
        { label: t("nav.contact"), href: "/contact" },
      ],
    },
    {
      title: t("footer.resources"),
      links: [
        { label: t("footer.helpCenter"), href: "/help" },
        { label: t("footer.apiDocs"), href: `${BACKEND_URL}/docs` },
        { label: t("nav.security"), href: "/security" },
        { label: t("nav.community"), href: "/community" },
      ],
    },
  ];
}

export function buildFooterLegal(t: T) {
  return [
    { label: t("footer.terms"), href: "/legal/terms" },
    { label: t("footer.privacy"), href: "/legal/privacy" },
    { label: t("footer.cookies"), href: "/legal/cookies" },
  ];
}

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
