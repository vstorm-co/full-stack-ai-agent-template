import type { ReactNode } from "react";
import { getTranslations } from "next-intl/server";

import { buildFooterColumns, buildFooterLegal, buildMarketingNavLinks } from "./footer-config";
import { MarketingFooter } from "./marketing-footer";
import { PillNav } from "./pill-nav";
import { Section } from "./section";
import { APP_NAME, ROUTES } from "@/lib/constants";

type Width = "narrow" | "wide" | "full";

const WIDTH_CLASS: Record<Width, string> = {
  narrow: "max-w-3xl",
  wide: "max-w-5xl",
  full: "max-w-7xl",
};

interface MarketingPageLayoutProps {
  eyebrow?: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  children: ReactNode;
  wrap?: boolean;
  width?: Width;
}

export async function MarketingPageLayout({
  eyebrow,
  title,
  description,
  meta,
  children,
  wrap = true,
  width = "wide",
}: MarketingPageLayoutProps) {
  const t = await getTranslations("marketing");
  const navLinks = buildMarketingNavLinks((k) => t(k));
  const footerColumns = buildFooterColumns((k) => t(k));
  const footerLegal = buildFooterLegal((k) => t(k));

  const bodyClass = WIDTH_CLASS[width];

  return (
    <>
      <PillNav
        brand={APP_NAME}
        links={navLinks}
        ctaLabel={t("nav.getStarted")}
        ctaHref={ROUTES.REGISTER}
        secondaryCta={{ label: t("nav.signIn"), href: ROUTES.LOGIN }}
      />

      <main id="main">
        <Section theme="light" padding="pt-40 pb-12 md:pt-48 md:pb-16">
          <div className="mx-auto max-w-3xl">
            {eyebrow && <span className="eyebrow-badge mb-6">{eyebrow}</span>}
            <h1 className="text-display-xl mb-5">{title}</h1>
            {description && (
              <p className="text-foreground/70 max-w-2xl text-lg leading-relaxed">{description}</p>
            )}
            {meta && (
              <div className="text-foreground/50 mt-6 font-mono text-xs tracking-wider uppercase">
                {meta}
              </div>
            )}
          </div>
        </Section>

        {wrap ? (
          <Section theme="light" padding="pb-32 md:pb-40">
            <div className={`mx-auto ${bodyClass}`}>{children}</div>
          </Section>
        ) : (
          children
        )}
      </main>

      <MarketingFooter
        brand={APP_NAME}
        tagline={t("footer.tagline")}
        operationalLabel={t("footer.operational")}
        columns={footerColumns}
        legal={footerLegal}
      />
    </>
  );
}
