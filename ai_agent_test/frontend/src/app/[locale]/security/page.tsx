import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { ArrowUpRight, Database, Eye, KeyRound, Lock, ShieldCheck, UserCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { MarketingPageLayout } from "@/components/marketing/marketing-page-layout";
import type { Locale } from "@/i18n";
import { CONTACT_INFO } from "@/lib/contact-info";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Security",
    description:
      "How we protect your data: encryption, access control, infrastructure, and policies.",
    path: "/security",
    locale,
  });
}

const ICON_MAP: Record<string, LucideIcon> = {
  lock: Lock,
  key: KeyRound,
  userCheck: UserCheck,
  database: Database,
  eye: Eye,
  shield: ShieldCheck,
};

interface Pillar {
  iconKey: string;
  title: string;
  description: string;
}

export default async function SecurityPage() {
  const t = await getTranslations("marketing.security");
  const pillars = t.raw("pillars") as Pillar[];
  const checklist = t.raw("checklist") as string[];

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      width="wide"
    >
      <section className="grid gap-3 sm:grid-cols-2">
        {pillars.map((p) => {
          const Icon = ICON_MAP[p.iconKey] ?? ShieldCheck;
          return (
            <article
              key={p.title}
              className="border-foreground/10 bg-card flex flex-col gap-3 rounded-2xl border p-6"
            >
              <span className="bg-brand/15 text-foreground inline-flex h-10 w-10 items-center justify-center rounded-full">
                <Icon className="h-4 w-4" />
              </span>
              <h2 className="text-foreground font-display text-base font-semibold">{p.title}</h2>
              <p className="text-foreground/70 text-sm leading-relaxed">{p.description}</p>
            </article>
          );
        })}
      </section>

      <section className="mt-20">
        <h2 className="font-display text-foreground text-2xl font-bold tracking-tight">
          {t("checklistTitle")}
        </h2>
        <ul className="border-foreground/10 divide-foreground/10 mt-5 divide-y rounded-2xl border">
          {checklist.map((c) => (
            <li
              key={c}
              className="text-foreground/85 flex items-start gap-3 px-5 py-4 text-sm leading-relaxed"
            >
              <span aria-hidden className="bg-brand mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" />
              {c}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-20">
        <h2 className="font-display text-foreground text-2xl font-bold tracking-tight">
          {t("vulnTitle")}
        </h2>
        <p className="text-foreground/75 mt-3 leading-relaxed">
          {t("vulnBody", { email: CONTACT_INFO.emails.security })}
        </p>
        <p className="mt-3 text-sm">
          <a
            href={`mailto:${CONTACT_INFO.emails.security}`}
            className="text-foreground font-mono underline-offset-4 hover:underline"
          >
            {CONTACT_INFO.emails.security}
          </a>
        </p>
        <Link
          href="/contact"
          className="text-foreground hover:text-foreground/80 mt-6 inline-flex items-center gap-1.5 font-medium underline-offset-4 hover:underline"
        >
          {t("vulnContactCta")}
          <ArrowUpRight className="h-4 w-4" />
        </Link>
      </section>
    </MarketingPageLayout>
  );
}
