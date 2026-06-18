import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth";
import type { Locale } from "@/i18n";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return pageMetadata({
    title: "Create your account",
    description: "Start your free trial — no credit card required.",
    path: "/register",
    locale,
  });
}

export default function RegisterPage() {
  return <RegisterForm />;
}
