import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { notFound } from "next/navigation";

import { CookieBanner } from "@/components/marketing/cookie-banner";
import { locales, type Locale } from "@/i18n";
import { OG_LOCALE, SITE } from "@/lib/seo";

import { Providers } from "../providers";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const safeLocale: Locale = locales.includes(locale as Locale)
    ? (locale as Locale)
    : SITE.defaultLocale;

  return {
    alternates: {
      // x-default points to the canonical default-locale tree.
      languages: {
        ...Object.fromEntries(SITE.locales.map((l) => [l, `${SITE.url}/${l}`])),
        "x-default": `${SITE.url}/${SITE.defaultLocale}`,
      },
    },
    openGraph: {
      locale: OG_LOCALE[safeLocale],
      alternateLocale: SITE.locales.filter((l) => l !== safeLocale).map((l) => OG_LOCALE[l]),
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <Providers>
      <NextIntlClientProvider messages={messages}>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        {children}
        <CookieBanner />
      </NextIntlClientProvider>
    </Providers>
  );
}
