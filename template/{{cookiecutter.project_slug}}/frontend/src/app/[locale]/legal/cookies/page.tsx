import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { CookiesBodyEn, CookiesBodyPl } from "@/components/legal/cookies-content";
import { LegalPage } from "@/components/marketing/legal-page";
import type { Locale } from "@/i18n";
import { APP_NAME } from "@/lib/constants";
import { pageMetadata } from "@/lib/seo";

const LAST_UPDATED = "2026-05-08";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Cookie Policy",
    description: `How ${APP_NAME} uses cookies and similar technologies.`,
    path: "/legal/cookies",
    locale,
  });
}

export default async function CookiesPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations("marketing.legal.cookies");

  return (
    <LegalPage title={t("title")} summary={t("summary")} lastUpdated={LAST_UPDATED} locale={locale}>
      {locale === "pl" ? <CookiesBodyPl /> : <CookiesBodyEn />}
    </LegalPage>
  );
}
