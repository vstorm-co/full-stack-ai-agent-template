import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { Github, LifeBuoy, Mail, MessageCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ContactForm } from "@/components/marketing/contact-form";
import { MarketingPageLayout } from "@/components/marketing/marketing-page-layout";
import type { Locale } from "@/i18n";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { CONTACT_INFO } from "@/lib/contact-info";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Contact",
    description: `Get in touch with the ${APP_NAME} team — support, sales, partnerships.`,
    path: "/contact",
    locale,
  });
}

const CHANNEL_META: Record<
  string,
  { icon: LucideIcon; href: string; valueOverride?: string; accent?: boolean }
> = {
  support: {
    icon: Mail,
    href: `mailto:${CONTACT_INFO.emails.support}`,
    valueOverride: CONTACT_INFO.emails.support,
    accent: true,
  },
  help: { icon: LifeBuoy, href: ROUTES.HELP },
  discord: { icon: MessageCircle, href: CONTACT_INFO.socials.discord },
  github: { icon: Github, href: CONTACT_INFO.socials.github },
};

interface Channel {
  key: string;
  label: string;
  value?: string;
  description: string;
}

export default async function ContactPage() {
  const t = await getTranslations("marketing.contact");
  const channels = t.raw("channelsList") as Channel[];

  return (
    <MarketingPageLayout
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      width="wide"
    >
      <div className="grid gap-10 md:grid-cols-[1fr_1.2fr] md:gap-12">
        <div className="space-y-5">
          <h2 className="font-display text-foreground text-2xl font-bold tracking-tight">
            {t("channels")}
          </h2>
          <ul className="space-y-3">
            {channels.map((c) => {
              const meta = CHANNEL_META[c.key];
              if (!meta) return null;
              const value = meta.valueOverride ?? c.value;
              return (
                <li key={c.key}>
                  <Link
                    href={meta.href}
                    className={`lift group flex items-start gap-4 rounded-2xl border p-4 transition-colors ${
                      meta.accent
                        ? "border-brand/30 bg-brand/[0.06]"
                        : "border-foreground/10 hover:border-foreground/30 bg-card"
                    }`}
                  >
                    <span
                      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                        meta.accent
                          ? "bg-brand text-brand-foreground"
                          : "bg-foreground/8 text-foreground"
                      }`}
                    >
                      <meta.icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-foreground text-sm font-semibold">{c.label}</p>
                      {value && (
                        <p className="text-foreground/85 mt-0.5 font-mono text-xs break-all">
                          {value}
                        </p>
                      )}
                      <p className="text-foreground/55 mt-1.5 text-xs">
                        {c.description.replace("{sla}", CONTACT_INFO.responseSla)}
                      </p>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>

          <div className="border-foreground/10 bg-card mt-8 rounded-2xl border p-5">
            <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
              {t("office")}
            </p>
            <p className="text-foreground mt-2 text-sm leading-relaxed">{t("officeNote")}</p>
            {CONTACT_INFO.address && (
              <p className="text-foreground/65 mt-2 font-mono text-xs">{CONTACT_INFO.address}</p>
            )}
          </div>

          <div className="text-foreground/55 mt-2 inline-flex items-center gap-2 font-mono text-[11px] tracking-wider uppercase">
            <span aria-hidden className="bg-brand h-1.5 w-1.5 animate-pulse rounded-full" />
            {t("responseSla", { sla: CONTACT_INFO.responseSla })}
          </div>
        </div>

        <div>
          <h2 className="font-display text-foreground mb-6 text-2xl font-bold tracking-tight">
            {t("sendMessage")}
          </h2>
          <ContactForm />
          <p className="text-foreground/45 mt-4 text-xs leading-relaxed">
            {t("formNote")}{" "}
            <code className="text-foreground/65 font-mono">src/lib/contact-info.ts</code>.
          </p>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
