"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

import { apiClient, ApiError } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";

/**
 * Magic-link verification page.
 *
 * Flow: user clicks the email link → arrives here with `?token=...` →
 * we POST the token to `/auth/magic-link/verify`, which signs them in via
 * the standard Set-Cookie flow → redirect to /chat.
 */
export default function MagicLinkVerifyPage() {
  const t = useTranslations("auth.magicLink");
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token");
  const [state, setState] = useState<"verifying" | "success" | "error">("verifying");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!token) {
      setState("error");
      setError(t("errorMissingToken"));
      return;
    }
    let active = true;
    apiClient
      .post("/auth/magic-link/verify", { token })
      .then(() => {
        if (!active) return;
        setState("success");
        router.replace(ROUTES.CHAT);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setState("error");
        setError(err instanceof ApiError ? err.message : t("errorInvalid"));
      });
    return () => {
      active = false;
    };
  }, [token, router, t]);

  return (
    <main
      id="main"
      className="bg-background flex min-h-screen flex-col items-center justify-center px-6"
    >
      <div className="w-full max-w-md space-y-6 text-center">
        {state === "verifying" && (
          <>
            <Loader2 className="text-foreground/70 mx-auto h-10 w-10 animate-spin" />
            <h1 className="font-display text-foreground text-2xl font-bold tracking-tight">
              {t("verifying")}
            </h1>
            <p className="text-foreground/65 text-sm">{t("verifyingHint")}</p>
          </>
        )}
        {state === "success" && (
          <>
            <CheckCircle2 className="text-brand mx-auto h-10 w-10" />
            <h1 className="font-display text-foreground text-2xl font-bold tracking-tight">
              {t("success")}
            </h1>
            <p className="text-foreground/65 text-sm">{t("successHint")}</p>
          </>
        )}
        {state === "error" && (
          <>
            <AlertCircle className="text-destructive mx-auto h-10 w-10" />
            <h1 className="font-display text-foreground text-2xl font-bold tracking-tight">
              {t("errorHeading")}
            </h1>
            <p className="text-foreground/65 text-sm">{error}</p>
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
              <Link
                href={ROUTES.LOGIN}
                className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors"
              >
                {t("signInWithPassword")}
              </Link>
              <Link
                href={ROUTES.FORGOT_PASSWORD}
                className="bg-foreground text-background hover:bg-foreground/90 inline-flex h-10 items-center gap-2 rounded-full px-4 text-sm font-medium transition-colors"
              >
                {t("requestNewLink")}
              </Link>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
