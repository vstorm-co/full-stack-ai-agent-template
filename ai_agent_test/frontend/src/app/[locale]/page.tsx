import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

import { DataFlowDiagram } from "@/components/marketing/data-flow-diagram";
import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { FeatureMockup } from "@/components/marketing/feature-mockup";
import { FeatureSection } from "@/components/marketing/feature-section";
import { FinalCta } from "@/components/marketing/final-cta";
import {
  buildFooterColumns,
  buildFooterLegal,
  buildMarketingNavLinks,
} from "@/components/marketing/footer-config";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { LogosStrip } from "@/components/marketing/logos-strip";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { Marquee } from "@/components/marketing/marquee";
import { PillNav } from "@/components/marketing/pill-nav";
import { PricingTeaser } from "@/components/marketing/pricing-teaser";
import { Reveal } from "@/components/marketing/reveal";
import { Section } from "@/components/marketing/section";
import { TestimonialGrid } from "@/components/marketing/testimonial-grid";
import { JsonLd } from "@/components/seo/json-ld";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { faqSchema, organizationSchema, websiteSchema } from "@/lib/schema-org";

const LOGOS = [
  { brand: "google" as const, name: "Google" },
  { brand: "microsoft" as const, name: "Microsoft" },
  { brand: "stripe" as const, name: "Stripe" },
  { brand: "notion" as const, name: "Notion" },
  { brand: "linear" as const, name: "Linear" },
  { brand: "vercel" as const, name: "Vercel" },
  { brand: "figma" as const, name: "Figma" },
  { brand: "loom" as const, name: "Loom" },
];

const MARQUEE_ITEMS = [
  "Discover",
  "Search",
  "Summarize",
  "Decide",
  "Connect",
  "Automate",
  "Track",
  "Improve",
  "Onboard",
  "Analyze",
  "Translate",
  "Draft",
  "Schedule",
  "Resolve",
  "Forecast",
  "Iterate",
];

const TESTIMONIALS = [
  {
    quote:
      "Our team finds answers in seconds instead of digging through Notion and Google Drive. It paid for itself in the first week.",
    name: "Marta Kowal",
    title: "Head of Operations",
    company: "Northwind Labs",
  },
  {
    quote:
      "We rolled it out to support, then sales picked it up, then everyone wanted access. It just keeps surprising us.",
    name: "Daniel Reyes",
    title: "VP Customer Success",
    company: "Acme Studios",
  },
  {
    quote:
      "The chat is great — the analytics dashboard is what sold it to me. We finally see how the team is using AI.",
    name: "Priya Anand",
    title: "Chief of Staff",
    company: "Helios",
  },
];

const PLANS = [
  {
    name: "Starter",
    price: "$0",
    cadence: "/ month",
    description: "For individuals exploring the product.",
    features: ["100 messages / day", "1 connected data source", "Community support"],
    cta: { label: "Start free", href: ROUTES.REGISTER },
  },
  {
    name: "Pro",
    price: "$29",
    cadence: "/ user / month",
    description: "For small teams getting real work done.",
    features: [
      "Unlimited messages",
      "10 connected sources",
      "Email + chat support",
      "Workflow automations",
    ],
    cta: { label: "Start 14-day trial", href: ROUTES.REGISTER },
    featured: true,
    badge: "Most popular",
  },
  {
    name: "Business",
    price: "$99",
    cadence: "/ user / month",
    description: "For organisations rolling out across teams.",
    features: [
      "Everything in Pro",
      "SSO + audit log",
      "Role-based access control",
      "Dedicated success manager",
    ],
    cta: { label: "Talk to sales", href: "/contact" },
  },
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "marketing.landing" });
  return pageMetadata({
    title: APP_NAME,
    description: t("metaDescription"),
    path: "/",
    locale,
  });
}

export default async function HomePage() {
  const t = await getTranslations("marketing.landing");
  const tNav = await getTranslations("marketing");

  const navLinks = buildMarketingNavLinks((k) => tNav(k));
  const footerColumns = buildFooterColumns((k) => tNav(k));
  const footerLegal = buildFooterLegal((k) => tNav(k));

  const heroStats = [
    { value: "10k", label: t("hero.stat_teams") },
    { value: "98%", label: t("hero.stat_speed") },
    { value: "24/7", label: t("hero.stat_uptime") },
  ];
  const faqItems = t.raw("faq.items") as { q: string; a: string }[];

  return (
    <>
      <JsonLd data={[organizationSchema(), websiteSchema(), faqSchema(faqItems)]} />

      <PillNav
        brand={APP_NAME}
        links={navLinks}
        ctaLabel={tNav("nav.getStarted")}
        ctaHref={ROUTES.REGISTER}
        secondaryCta={{ label: tNav("nav.signIn"), href: ROUTES.LOGIN }}
      />

      <main id="main">
        {/* Hero (dark) */}
        <Hero
          eyebrow={t("hero.eyebrow")}
          title={
            <>
              {t("hero.titlePre")} <em>{t("hero.titleHighlight")}</em> <em>{t("hero.titleEm")}</em>
            </>
          }
          description={t("hero.description")}
          primaryCta={{ label: t("hero.ctaPrimary"), href: ROUTES.REGISTER }}
          stats={heroStats}
          theme="dark"
        />

        {/* Marquee */}
        <Marquee items={MARQUEE_ITEMS} />

        {/* Social proof (light) */}
        <Section theme="light" padding="py-16 md:py-20">
          <Reveal>
            <LogosStrip label="Trusted by teams across industries" logos={LOGOS} />
          </Reveal>
        </Section>

        {/* How it works (dark) */}
        <Section theme="dark" id="how">
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">How it works</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              Get started in <em>three steps.</em>
            </h2>
          </div>
          <Reveal>
            <HowItWorks />
          </Reveal>
        </Section>

        {/* Features — alternating */}
        <Section theme="dark" id="features">
          <Reveal>
            <FeatureSection
              eyebrow="Connected knowledge"
              title={
                <>
                  All your data, <em>one assistant.</em>
                </>
              }
              description="Sync from Google Drive, Notion, Slack, S3 and more. Files stay where they are — we keep them indexed and ready to answer questions in real time."
              bullets={[
                {
                  title: "Always up to date",
                  body: "Documents re-index automatically when they change at the source.",
                },
                {
                  title: "Granular permissions",
                  body: "Each user only sees what they're allowed to see. Nothing leaks.",
                },
                {
                  title: "Built-in search",
                  body: "Find anything across every connected source from a single search box.",
                },
              ]}
              visual={<FeatureMockup kind="rag" />}
              cta={{ label: "See connected sources", href: ROUTES.RAG }}
              visualSide="left"
            />
          </Reveal>
        </Section>

        <Section theme="light">
          <Reveal>
            <FeatureSection
              eyebrow="AI Chat"
              title={
                <>
                  Answers grounded in <em>your own work.</em>
                </>
              }
              description="Ask questions in plain English and get answers with citations. Your assistant remembers context across conversations and adapts as your work evolves."
              bullets={[
                {
                  title: "Cites sources, every time",
                  body: "Every answer links back to the document, message, or ticket it came from.",
                },
                {
                  title: "Multi-step reasoning",
                  body: "Handles complex requests by breaking them into steps and acting on each.",
                },
                {
                  title: "Works on web and mobile",
                  body: "Identical experience across devices, plus integrations with Slack and Teams.",
                },
              ]}
              visual={<FeatureMockup kind="agents" />}
              cta={{ label: "Try the chat", href: ROUTES.CHAT }}
              visualSide="right"
            />
          </Reveal>
        </Section>

        <Section theme="dark">
          <Reveal>
            <FeatureSection
              eyebrow="Insights"
              title={
                <>
                  Know what your team <em>is asking.</em>
                </>
              }
              description="A live dashboard of every question asked, answer rated, and workflow run. Spot gaps in your knowledge base, identify your power users, and prove the ROI."
              bullets={[
                {
                  title: "Usage by team or person",
                  body: "Drill down to see who's getting value and where the questions concentrate.",
                },
                {
                  title: "Quality feedback loop",
                  body: "Users rate answers; you see what's working and what to improve.",
                },
                {
                  title: "Export to your warehouse",
                  body: "Stream events to BigQuery, Snowflake or your own tools via the API.",
                },
              ]}
              visual={<FeatureMockup kind="billing" />}
              cta={{ label: "Explore the dashboard", href: ROUTES.DASHBOARD }}
              visualSide="left"
            />
          </Reveal>
        </Section>

        {/* Data flow diagram — anchors the "your data → assistant" pipeline after the feature trio. */}
        <Section theme="light" className="relative overflow-hidden">
          <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10" />
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">How it connects</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              Your data flows in. <em>Answers come back.</em>
            </h2>
            <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
              Source documents, conversations, and cloud files are continuously indexed. Every
              answer is grounded in your own work — with citations back to the source.
            </p>
          </div>
          <Reveal>
            <DataFlowDiagram />
          </Reveal>
        </Section>

        {/* Testimonials (light) — grid of 3 */}
        <Section theme="light">
          <div className="mb-14 text-center">
            <p className="eyebrow text-foreground/55 mb-4">{t("testimonials.eyebrow")}</p>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent mx-auto max-w-2xl [&_em]:font-normal [&_em]:italic">
              {t("testimonials.titlePre")} <em>{t("testimonials.titleEm")}</em>
            </h2>
          </div>
          <Reveal>
            <TestimonialGrid items={TESTIMONIALS} />
          </Reveal>
        </Section>

        {/* Pricing (dark) */}
        <Section theme="dark" id="pricing">
          <div className="mb-14 max-w-2xl">
            <div className="mb-5">
              <span className="eyebrow-badge">{t("pricing.eyebrow")}</span>
            </div>
            <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
              {t("pricing.titlePre")} <em>{t("pricing.titleEm")}</em>
            </h2>
            <p className="text-foreground/70 mt-5 max-w-xl text-lg leading-relaxed">
              {t("pricing.subtitle")}
            </p>
          </div>
          <Reveal>
            <PricingTeaser plans={PLANS} fullPricingHref={ROUTES.PRICING} />
          </Reveal>
        </Section>

        {/* FAQ (light) */}
        <Section theme="light" id="faq">
          <div className="mb-14 text-center">
            <p className="eyebrow text-foreground/55 mb-4">{t("faq.eyebrow")}</p>
            <h2 className="text-display-lg text-foreground">{t("faq.title")}</h2>
          </div>
          <Reveal>
            <FaqAccordion
              items={faqItems.map((it) => ({ ...it, q: it.q.replace("{appName}", APP_NAME) }))}
            />
          </Reveal>
        </Section>

        {/* Final CTA */}
        <Section theme="light" padding="pb-24 md:pb-32">
          <Reveal>
            <FinalCta
              stat={{ value: t("finalCta.statValue"), label: t("finalCta.statLabel") }}
              title={
                <>
                  {t("finalCta.titlePre")} <em>{t("finalCta.titleEm")}</em>
                </>
              }
              description={t("finalCta.description")}
              primary={{ label: t("finalCta.primary"), href: ROUTES.REGISTER }}
              secondary={{ label: t("finalCta.secondary"), href: ROUTES.PRICING }}
            />
          </Reveal>
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
