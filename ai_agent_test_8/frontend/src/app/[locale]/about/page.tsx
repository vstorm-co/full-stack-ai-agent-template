import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { ArrowRight, Compass, Layers, Sparkles, Target } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { MarketingPageLayout } from "@/components/marketing/marketing-page-layout";
import { Section } from "@/components/marketing/section";
import type { Locale } from "@/i18n";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "About",
    description: `The story, the team, and what we're building at ${APP_NAME}.`,
    path: "/about",
    locale,
  });
}

const VALUE_ICONS: Record<string, LucideIcon> = {
  shipBoring: Compass,
  defaults: Target,
  openOpinionated: Layers,
  aiTool: Sparkles,
};

interface Value {
  key: string;
  title: string;
  description: string;
}

interface TeamMember {
  initials: string;
  role: string;
  line: string;
}

export default async function AboutPage() {
  const t = await getTranslations("marketing.about");
  const values = t.raw("values") as Value[];
  const team = t.raw("team") as TeamMember[];

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title", { appName: APP_NAME })}
      description={t("description")}
      width="wide"
    >
      <div className="grid gap-10 md:grid-cols-[1.1fr_1fr] md:gap-14">
        <div className="space-y-5">
          <h2 className="font-display text-foreground text-2xl font-bold tracking-tight">
            {t("whyTitle")}
          </h2>
          <p className="text-foreground/75 leading-relaxed">{t("why1")}</p>
          <p className="text-foreground/75 leading-relaxed">{t("why2")}</p>
          <Link
            href={ROUTES.PRICING}
            className="text-foreground hover:text-foreground/80 mt-2 inline-flex items-center gap-1.5 font-medium underline-offset-4 hover:underline"
          >
            {t("seePricing")}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="border-foreground/10 bg-card relative overflow-hidden rounded-3xl border p-8">
          <div className="bg-brand/[0.08] pointer-events-none absolute -top-20 -right-20 h-60 w-60 rounded-full blur-[100px]" />
          <div className="relative">
            <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              {t("byTheNumbers")}
            </p>
            <dl className="mt-6 space-y-5">
              {[
                { label: t("stat_apps"), value: "12+" },
                { label: t("stat_deploy"), value: "<1h" },
                { label: t("stat_frameworks"), value: "5" },
                { label: t("stat_license"), value: "MIT" },
              ].map((row, i) => (
                <div
                  key={row.label}
                  className={`flex items-baseline justify-between ${
                    i < 3 ? "border-foreground/10 border-b pb-4" : ""
                  }`}
                >
                  <dt className="text-foreground/65 text-sm">{row.label}</dt>
                  <dd className="font-display text-foreground text-2xl font-bold">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>

      <figure className="border-foreground/10 bg-card mt-16 rounded-3xl border p-8 sm:p-12">
        <span aria-hidden className="font-display text-brand block text-6xl leading-none">
          “
        </span>
        <blockquote className="font-display text-foreground -mt-2 text-2xl leading-snug tracking-tight md:text-3xl">
          {t("quoteLine1")} <em className="font-accent text-brand">{t("quoteLine2")}</em>{" "}
          {t("quoteLine3")}
        </blockquote>
        <figcaption className="text-foreground/55 mt-5 font-mono text-[11px] tracking-wider uppercase">
          {APP_NAME} · {t("quoteByline")}
        </figcaption>
      </figure>

      <Section theme="dark" className="-mx-4 mt-20 rounded-3xl md:-mx-10" padding="py-16 md:py-24">
        <div className="mx-auto max-w-4xl px-4 md:px-8">
          <div className="mb-12 max-w-2xl">
            <span className="eyebrow-badge mb-6">{t("valuesEyebrow")}</span>
            <h2 className="text-display-md">{t("valuesTitle")}</h2>
          </div>
          <ul className="grid gap-4 sm:grid-cols-2">
            {values.map((v) => {
              const Icon = VALUE_ICONS[v.key] ?? Sparkles;
              return (
                <li
                  key={v.key}
                  className="border-foreground/15 bg-card lift flex flex-col gap-3 rounded-2xl border p-6"
                >
                  <span className="bg-brand/15 text-foreground inline-flex h-10 w-10 items-center justify-center rounded-full">
                    <Icon className="h-5 w-5" />
                  </span>
                  <p className="text-foreground font-display text-lg font-semibold tracking-tight">
                    {v.title}
                  </p>
                  <p className="text-foreground/70 text-sm leading-relaxed">{v.description}</p>
                </li>
              );
            })}
          </ul>
        </div>
      </Section>

      <div className="mt-20">
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
          {t("teamLabel")}
        </p>
        <h2 className="font-display text-foreground mt-2 text-3xl font-bold tracking-tight">
          {t("teamTitle")}
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {team.map((member) => (
            <div
              key={member.role}
              className="border-foreground/10 bg-card flex items-center gap-4 rounded-2xl border p-5"
            >
              <span className="bg-foreground text-background flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-mono text-xs font-semibold">
                {member.initials}
              </span>
              <div>
                <p className="text-foreground text-sm font-semibold">{member.role}</p>
                <p className="text-foreground/55 mt-0.5 text-xs">{member.line}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-foreground/10 bg-card mt-16 flex flex-wrap items-center justify-between gap-4 rounded-3xl border p-8 sm:p-10">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            {t("ctaEyebrow")}
          </p>
          <p className="font-display text-foreground mt-2 text-2xl font-bold tracking-tight">
            {t("ctaTitle")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={ROUTES.REGISTER}
            className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-colors"
          >
            {t("ctaPrimary")}
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href={ROUTES.CONTACT}
            className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-sm font-medium transition-colors"
          >
            {t("ctaSecondary")}
          </Link>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
