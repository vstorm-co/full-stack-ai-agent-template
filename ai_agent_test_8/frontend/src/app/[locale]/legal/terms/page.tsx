import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LegalPage } from "@/components/marketing/legal-page";
import { TermsBodyEn, TermsBodyPl } from "@/components/legal/terms-content";
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
    title: "Terms of Service",
    description: `Terms governing your use of ${APP_NAME}.`,
    path: "/legal/terms",
    locale,
  });
}

export default async function TermsPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations("marketing.legal.terms");

  return (
    <LegalPage
      title={t("title")}
      summary={t("summary", { appName: APP_NAME })}
      lastUpdated={LAST_UPDATED}
      locale={locale}
    >
      {locale === "pl" ? <TermsBodyPl /> : <TermsBodyEn />}
    </LegalPage>
  );
}
