{% raw %}"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Check, Sparkles } from "lucide-react";

import { FaqAccordion } from "@/components/marketing/faq-accordion";
import {
  buildFooterColumns,
  buildFooterLegal,
  buildMarketingNav,
} from "@/components/marketing/footer-config";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { PillNav } from "@/components/marketing/pill-nav";
import { Section } from "@/components/marketing/section";
import { SmoothScroll } from "@/components/marketing/smooth-scroll";
import { TestimonialGrid } from "@/components/marketing/testimonial-grid";
import { apiClient } from "@/lib/api-client";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { getTeaserPlans, type TeaserPlan } from "@/lib/teaser-plans";
import { cn, formatCurrency } from "@/lib/utils";

interface PlanRead {
  id: string;
  code: string;
  display_name: string;
  description: string | null;
  monthly_credits_base: number;
  features: Record<string, unknown>;
  prices: Array<{
    id: string;
    currency: string;
    amount_cents: number;
    interval: string;
    is_active: boolean;
    trial_period_days: number | null;
  }>;
}

// FAQs moved to messages JSON (`marketing.pricing.faqs`).

const TESTIMONIALS = [
  {
    quote: "We replaced four separate SaaS tools and shipped our first AI feature in two weeks.",
    name: "Maya Chen",
    title: "CTO",
    company: "Lumen Labs",
  },
  {
    quote: "The pricing was the easy part. The pre-built billing flow saved us a sprint.",
    name: "Jonas Berg",
    title: "Founder",
    company: "Stash AI",
  },
  {
    quote: "Onboarded our entire ops team in an afternoon. The defaults are sensible.",
    name: "Priya Nair",
    title: "Head of Operations",
    company: "Northwind",
  },
];

interface PricingCard {
  id: string;
  name: string;
  price: string;
  cadence?: string;
  description: string;
  featured: boolean;
  badge: string | null;
  features: string[];
  cta: { label: string; href: string };
  trial?: number | null;
  isStub: boolean;
}

function teaserPlanToCard(plan: TeaserPlan, mostPopularLabel: string): PricingCard {
  return {
    id: plan.name,
    name: plan.name,
    price: plan.price,
    cadence: plan.cadence,
    description: plan.description,
    featured: !!plan.featured,
    badge: plan.featured ? mostPopularLabel : null,
    features: plan.features,
    cta: plan.cta,
    isStub: true,
  };
}

function realPlanToCard(plan: PlanRead, billing: "month" | "year"): PricingCard {
  const price = plan.prices.find((p) => p.is_active && p.interval === billing);
  return {
    id: plan.id,
    name: plan.display_name,
    price: price ? formatCurrency(price.amount_cents, price.currency) : "—",
    description: plan.description ?? "",
    featured: false,
    badge: null,
    features: [
      ...(plan.monthly_credits_base > 0
        ? [`${plan.monthly_credits_base.toLocaleString()} credits / month`]
        : []),
      ...Object.entries(plan.features)
        .filter(([, v]) => v === true || typeof v === "string")
        .slice(0, 5)
        .map(([k, v]) => (typeof v === "string" ? v : k.replace(/_/g, " "))),
    ],
    cta: { label: "Start free trial", href: ROUTES.REGISTER },
    trial: price?.trial_period_days ?? null,
    isStub: false,
  };
}

export default function PricingPage() {
  const tNav = useTranslations("marketing");
  const tPricing = useTranslations("marketing.pricing");
  const locale = useLocale();

  const navLinks = useMemo(() => buildMarketingNav((k) => tNav(k)), [tNav]);
  const footerColumns = useMemo(() => buildFooterColumns((k) => tNav(k)), [tNav]);
  const footerLegal = useMemo(() => buildFooterLegal((k) => tNav(k)), [tNav]);

  const [plans, setPlans] = useState<PlanRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [billing, setBilling] = useState<"month" | "year">("month");

  useEffect(() => {
    apiClient
      .get<{ items: PlanRead[]; total: number }>("/billing/plans")
      .then((d) => setPlans(d.items))
      .catch(() => setPlans([]))
      .finally(() => setIsLoading(false));
  }, []);

  const activePlans = useMemo(
    () => plans.filter((p) => p.prices.some((pr) => pr.is_active && pr.interval === billing)),
    [plans, billing],
  );

  const usingStub = !isLoading && activePlans.length === 0;
  const cards: PricingCard[] = usingStub
    ? getTeaserPlans(locale).map((p) => teaserPlanToCard(p, tPricing("mostPopular")))
    : activePlans.map((p, i) => {
        const card = realPlanToCard(p, billing);
        if (i === 1) {
          return { ...card, featured: true, badge: tPricing("mostPopular") };
        }
        return card;
      });

  const faqs = tPricing.raw("faqs") as { q: string; a: string }[];

  return (
    <>
      <SmoothScroll />
      <PillNav
        brand={APP_NAME}
        links={navLinks}
        ctaLabel={tNav("nav.getStarted")}
        ctaHref={ROUTES.REGISTER}
        secondaryCta={{ label: tNav("nav.signIn"), href: ROUTES.LOGIN }}
      />

      <main id="main">
        <Section theme="light" padding="pt-28 pb-20 md:pt-32">
          <div className="mx-auto max-w-3xl text-center">
            <span className="eyebrow-badge mb-6">{tPricing("eyebrow")}</span>
            <h1 className="text-display-xl mb-6">{tPricing("title")}</h1>
            <p className="text-foreground/70 mx-auto max-w-xl text-lg leading-relaxed">
              {tPricing("description")}
            </p>

            <div className="border-foreground/15 bg-card mx-auto mt-10 inline-flex items-center rounded-full border p-1 text-sm">
              <button
                type="button"
                onClick={() => setBilling("month")}
                className={cn(
                  "rounded-full px-5 py-2 font-medium transition",
                  billing === "month"
                    ? "bg-foreground text-background shadow-sm"
                    : "text-foreground/65 hover:text-foreground",
                )}
              >
                {tPricing("monthly")}
              </button>
              <button
                type="button"
                onClick={() => setBilling("year")}
                className={cn(
                  "inline-flex items-center gap-2 rounded-full px-5 py-2 font-medium transition",
                  billing === "year"
                    ? "bg-foreground text-background shadow-sm"
                    : "text-foreground/65 hover:text-foreground",
                )}
              >
                {tPricing("annual")}
                <span className="bg-brand text-brand-foreground rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold tracking-wider uppercase">
                  {tPricing("savePill")}
                </span>
              </button>
            </div>
          </div>
        </Section>

        <Section theme="light" padding="pb-32 md:pb-40">
          <div className="mx-auto max-w-6xl">
            {usingStub && (
              <div className="border-foreground/10 bg-foreground/[0.03] text-foreground/65 mx-auto mb-8 inline-flex items-center gap-2 rounded-full border px-4 py-2 font-mono text-[11px] tracking-wider uppercase">
                <span aria-hidden className="bg-brand h-1.5 w-1.5 animate-pulse rounded-full" />
                {tPricing("demoBanner")}
              </div>
            )}

            {isLoading ? (
              <div className="grid gap-6 md:grid-cols-3">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="border-border bg-muted h-[480px] animate-pulse rounded-2xl border"
                  />
                ))}
              </div>
            ) : (
              <div className="grid items-stretch gap-6 md:grid-cols-3">
                {cards.map((card) => (
                  <div
                    key={card.id}
                    className={cn(
                      "relative flex flex-col rounded-2xl border p-8",
                      card.featured
                        ? "border-brand bg-brand/[0.06] -translate-y-2 shadow-2xl"
                        : "border-foreground/15 bg-card lift",
                    )}
                  >
                    {card.featured && card.badge && (
                      <div className="bg-brand text-brand-foreground absolute -top-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 rounded-full px-3 py-1 font-mono text-[11px] font-semibold tracking-wider uppercase">
                        <Sparkles className="h-3 w-3" />
                        {card.badge}
                      </div>
                    )}
                    <div>
                      <p className="eyebrow text-foreground/55">{card.name}</p>
                      <div className="mt-4 flex items-baseline gap-2">
                        <span className="font-display text-foreground text-5xl font-bold tracking-tight">
                          {card.price}
                        </span>
                        {card.cadence && (
                          <span className="text-foreground/55 text-sm">{card.cadence}</span>
                        )}
                      </div>
                      {card.description && (
                        <p className="text-foreground/65 mt-3 text-sm">{card.description}</p>
                      )}
                      {card.trial ? (
                        <p className="text-foreground/55 mt-2 font-mono text-xs tracking-wider uppercase">
                          {tPricing("trialBadge", { days: card.trial })}
                        </p>
                      ) : null}
                    </div>

                    <ul className="mt-8 flex-1 space-y-3">
                      {card.features.map((f) => (
                        <li key={f} className="text-foreground/85 flex gap-3 text-sm">
                          <span
                            className={cn(
                              "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                              card.featured
                                ? "bg-brand text-brand-foreground"
                                : "bg-foreground/8 text-foreground",
                            )}
                          >
                            <Check className="h-3 w-3" />
                          </span>
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>

                    <Link
                      href={card.cta.href}
                      className={cn(
                        "mt-10 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-medium transition-colors",
                        card.featured
                          ? "bg-foreground text-background hover:bg-foreground/90"
                          : "border-foreground/20 hover:border-foreground/40 hover:bg-foreground hover:text-background border",
                      )}
                    >
                      {card.isStub ? card.cta.label : tPricing("startTrial")}
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Section>

        <Section theme="dark" padding="py-32 md:py-40">
          <div className="mx-auto max-w-5xl">
            <div className="mx-auto mb-14 max-w-2xl text-center">
              <span className="eyebrow-badge mb-6">{tPricing("loved")}</span>
              <h2 className="text-display-lg">{tPricing("lovedTitle")}</h2>
            </div>
            <TestimonialGrid items={TESTIMONIALS} />
          </div>
        </Section>

        <Section theme="light" padding="py-32 md:py-40" id="faq">
          <div className="mx-auto max-w-3xl">
            <div className="mb-12 text-center">
              <span className="eyebrow-badge mb-6">{tNav("nav.faq")}</span>
              <h2 className="text-display-lg">{tPricing("faqTitle")}</h2>
            </div>
            <FaqAccordion items={faqs} />
          </div>
        </Section>
      </main>

      <MarketingFooter
        brand={APP_NAME}
        tagline={tNav("footer.tagline")}
        operationalLabel={tNav("footer.operational")}
        columns={footerColumns}
        legal={footerLegal}
      />
    </>
  );
}
{% endraw %}
