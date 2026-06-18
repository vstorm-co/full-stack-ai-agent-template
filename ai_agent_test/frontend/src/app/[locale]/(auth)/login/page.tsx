import type { Metadata } from "next";

import { LoginForm } from "@/components/auth";
import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Sign in",
    description: "Sign in to your workspace.",
    path: "/login",
    locale,
    noindex: true,
  });
}

export default function LoginPage() {
  return <LoginForm />;
}
