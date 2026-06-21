import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CreditCard,
  KeyRound,
  MessageSquare,
  Settings,
  Shield,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { FaqAccordion } from "@/components/marketing/faq-accordion";
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
    title: "Help center",
    description: `Guides, FAQs, and how-tos for ${APP_NAME}.`,
    path: "/help",
    locale,
  });
}

const ICON_MAP: Record<string, LucideIcon> = {
  key: KeyRound,
  message: MessageSquare,
  book: BookOpen,
  credit: CreditCard,
  settings: Settings,
  shield: Shield,
};

interface Topic {
  id: string;
  iconKey: string;
  title: string;
  description: string;
}

interface FaqGroup {
  id: string;
  title: string;
  items: { q: string; a: string }[];
}

export default async function HelpPage() {
  const t = await getTranslations("marketing.help");
  const topics = t.raw("topics") as Topic[];
  const faqGroups = t.raw("faqGroups") as FaqGroup[];

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      width="wide"
    >
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {topics.map((topic) => {
          const Icon = ICON_MAP[topic.iconKey] ?? BookOpen;
          return (
            <Link
              key={topic.id}
              href={`#${topic.id}`}
              className="lift border-foreground/10 hover:border-foreground/30 bg-card group flex flex-col gap-3 rounded-2xl border p-5 transition-colors"
            >
              <span className="bg-brand/15 text-foreground inline-flex h-10 w-10 items-center justify-center rounded-full">
                <Icon className="h-4 w-4" />
              </span>
              <p className="text-foreground font-display text-base font-semibold">{topic.title}</p>
              <p className="text-foreground/65 text-sm">{topic.description}</p>
              <span className="text-foreground/45 group-hover:text-foreground mt-auto inline-flex items-center gap-1 font-mono text-[11px] tracking-wider uppercase transition-colors">
                {t("browseLabel")}
                <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          );
        })}
      </div>

      <div className="mt-20 space-y-16">
        {faqGroups.map((group) => (
          <section key={group.id} id={group.id}>
            <h2 className="font-display text-foreground text-2xl font-bold tracking-tight">
              {group.title}
            </h2>
            <div className="mt-4">
              <FaqAccordion items={group.items} />
            </div>
          </section>
        ))}
      </div>

      <Section theme="dark" className="-mx-6 mt-24 rounded-3xl md:-mx-10" padding="py-16 md:py-20">
        <div className="mx-auto max-w-2xl px-2 text-center md:px-6">
          <span className="eyebrow-badge mb-6">{t("stillStuckEyebrow")}</span>
          <h2 className="text-display-md mb-4">{t("stillStuckTitle")}</h2>
          <p className="text-foreground/65 mx-auto max-w-md text-base">{t("stillStuckBody")}</p>
          <Link
            href={ROUTES.HOME + "contact"}
            className="bg-brand text-brand-foreground hover:bg-brand-hover mt-8 inline-flex h-12 items-center gap-2 rounded-full px-6 text-sm font-semibold transition-colors"
          >
            {t("stillStuckCta")}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </Section>
    </MarketingPageLayout>
  );
}
