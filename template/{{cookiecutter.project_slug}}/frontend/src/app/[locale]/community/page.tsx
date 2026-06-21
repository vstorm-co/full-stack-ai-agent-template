import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { ArrowUpRight, Github, MessageCircle, Twitter, Youtube } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { MarketingPageLayout } from "@/components/marketing/marketing-page-layout";
import type { Locale } from "@/i18n";
import { APP_NAME } from "@/lib/constants";
import { CONTACT_INFO } from "@/lib/contact-info";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Community",
    description: `Join the ${APP_NAME} community — Discord, GitHub, newsletter, and meetups.`,
    path: "/community",
    locale,
  });
}

const CHANNEL_META: Record<string, { icon: LucideIcon; href: string; accent?: boolean }> = {
  discord: { icon: MessageCircle, href: CONTACT_INFO.socials.discord, accent: true },
  github: { icon: Github, href: CONTACT_INFO.socials.github },
  twitter: { icon: Twitter, href: CONTACT_INFO.socials.twitter },
  youtube: { icon: Youtube, href: CONTACT_INFO.socials.youtube },
};

interface Channel {
  key: string;
  title: string;
  description: string;
  cta: string;
  eyebrow?: string;
}

interface Guideline {
  title: string;
  description: string;
}

export default async function CommunityPage() {
  const t = await getTranslations("marketing.community");
  const channels = t.raw("channels") as Channel[];
  const guidelines = t.raw("guidelines") as Guideline[];

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      width="wide"
    >
      <section className="grid gap-3 md:grid-cols-2">
        {channels.map((c) => {
          const meta = CHANNEL_META[c.key];
          if (!meta) return null;
          return (
            <Link
              key={c.key}
              href={meta.href}
              target="_blank"
              rel="noopener noreferrer"
              className={`lift group relative flex flex-col gap-4 rounded-3xl border p-7 transition-colors ${
                meta.accent
                  ? "border-brand/40 bg-brand/[0.06]"
                  : "border-foreground/10 bg-card hover:border-foreground/30"
              }`}
            >
              {c.eyebrow && (
                <span className="bg-brand text-brand-foreground absolute -top-3 left-7 rounded-full px-3 py-1 font-mono text-[10px] font-semibold tracking-wider uppercase">
                  {c.eyebrow}
                </span>
              )}
              <span
                className={`inline-flex h-11 w-11 items-center justify-center rounded-full ${
                  meta.accent ? "bg-brand text-brand-foreground" : "bg-foreground/8 text-foreground"
                }`}
              >
                <meta.icon className="h-5 w-5" />
              </span>
              <div>
                <h2 className="text-foreground font-display text-xl font-bold tracking-tight">
                  {c.title}
                </h2>
                <p className="text-foreground/65 mt-1.5 text-sm leading-relaxed">{c.description}</p>
              </div>
              <span className="text-foreground/55 group-hover:text-foreground mt-auto inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors">
                {c.cta}
                <ArrowUpRight className="h-3.5 w-3.5" />
              </span>
            </Link>
          );
        })}
      </section>

      <section className="mt-20">
        <h2 className="font-display text-foreground text-2xl font-bold tracking-tight">
          {t("guidelinesTitle")}
        </h2>
        <p className="text-foreground/65 mt-2 max-w-2xl">{t("guidelinesIntro")}</p>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2">
          {guidelines.map((g) => (
            <li key={g.title} className="border-foreground/10 bg-card rounded-2xl border p-5">
              <p className="text-foreground font-display text-base font-semibold">{g.title}</p>
              <p className="text-foreground/65 mt-1 text-sm leading-relaxed">{g.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </MarketingPageLayout>
  );
}
