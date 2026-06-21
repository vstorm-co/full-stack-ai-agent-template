import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { PrivacyBodyEn, PrivacyBodyPl } from "@/components/legal/privacy-content";
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
    title: "Privacy Policy",
    description: `How ${APP_NAME} collects, uses, and protects your data.`,
    path: "/legal/privacy",
    locale,
  });
}

export default async function PrivacyPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations("marketing.legal.privacy");

  return (
    <LegalPage
      title={t("title")}
      summary={t("summary", { appName: APP_NAME })}
      lastUpdated={LAST_UPDATED}
      locale={locale}
    >
      {locale === "pl" ? <PrivacyBodyPl /> : <PrivacyBodyEn />}
    </LegalPage>
  );
}
