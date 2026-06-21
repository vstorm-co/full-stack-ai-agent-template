import type { Metadata } from "next";

import { JsonLd } from "@/components/seo/json-ld";
import type { Locale } from "@/i18n";
import { APP_NAME } from "@/lib/constants";
import { softwareApplicationSchema } from "@/lib/schema-org";
import { pageMetadata, SITE } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Pricing",
    description:
      "Simple plans that scale with your team — start free, upgrade when you're ready. No credit card required for the trial.",
    path: "/pricing",
    locale,
  });
}

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLd
        data={softwareApplicationSchema({
          name: APP_NAME,
          description: SITE.description,
          url: `${SITE.url}/pricing`,
          offers: [
            { price: "0", priceCurrency: "USD", name: "Starter" },
            { price: "29", priceCurrency: "USD", name: "Pro" },
            { price: "99", priceCurrency: "USD", name: "Business" },
          ],
        })}
      />
      {children}
    </>
  );
}
