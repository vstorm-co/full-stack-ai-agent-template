"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { ArrowLeft, ArrowRight, Check, X } from "lucide-react";
import { toast } from "sonner";

import { Button, Input, Label } from "@/components/ui";
import { apiClient, ApiError } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";

function strengthScore(pw: string): number {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^a-zA-Z0-9]/.test(pw)) score++;
  return score;
}

interface Props {
  token: string;
}

export function ResetPasswordForm({ token }: Props) {
  const t = useTranslations("auth.resetPassword");
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const score = useMemo(() => strengthScore(password), [password]);
  const strengthLabel = useMemo(() => {
    if (!password) return "";
    if (score <= 1) return t("strengthWeak");
    if (score <= 2) return t("strengthFair");
    if (score <= 3) return t("strengthGood");
    return t("strengthStrong");
  }, [score, password, t]);
  const matches = !confirm || password === confirm;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError(t("minLength"));
      return;
    }
    if (password !== confirm) {
      setError(t("passwordsDontMatch"));
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post("/auth/password-reset/confirm", {
        token,
        new_password: password,
      });
      toast.success(t("successToast"));
      router.push(ROUTES.LOGIN);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : t("invalidLink");
      setError(msg);
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <span className="eyebrow text-foreground/55">{t("eyebrow")}</span>
        <h1 className="text-display-md text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          {t("heading")}
        </h1>
        <p className="text-foreground/65 text-sm">{t("intro")}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <Label
            htmlFor="new-pw"
            className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
          >
            {t("newPassword")}
          </Label>
          <Input
            id="new-pw"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            disabled={submitting}
            className="h-12 rounded-xl"
          />
          {password && (
            <div className="space-y-1.5 pt-1">
              <div
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={4}
                aria-valuenow={Math.min(score, 4)}
                aria-label={strengthLabel}
                className="flex gap-1"
              >
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-colors ${
                      i <= score ? "bg-brand" : "bg-foreground/10"
                    }`}
                  />
                ))}
              </div>
              <p
                aria-live="polite"
                className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase"
              >
                {strengthLabel}
              </p>
            </div>
          )}
        </div>

        <div className="space-y-1.5">
          <Label
            htmlFor="confirm-pw"
            className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
          >
            {t("confirm")}
          </Label>
          <Input
            id="confirm-pw"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            autoComplete="new-password"
            disabled={submitting}
            className={`h-12 rounded-xl ${confirm && !matches ? "border-destructive" : ""}`}
          />
          {confirm && !matches && (
            <p className="text-destructive inline-flex items-center gap-1 text-xs">
              <X className="h-3 w-3" />
              {t("passwordsDontMatch")}
            </p>
          )}
          {confirm && matches && (
            <p className="text-brand inline-flex items-center gap-1 text-xs">
              <Check className="h-3 w-3" />
              {t("passwordsMatch")}
            </p>
          )}
        </div>

        {error && (
          <p className="border-destructive/30 bg-destructive/5 text-destructive rounded-lg border px-3 py-2 text-sm">
            {error}
          </p>
        )}

        <Button
          type="submit"
          disabled={submitting}
          className="bg-foreground text-background hover:bg-foreground/90 h-12 w-full rounded-full text-base font-medium"
        >
          {submitting ? (
            t("submitting")
          ) : (
            <>
              {t("submit")}
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>

        <Link
          href={ROUTES.LOGIN}
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-2 text-sm font-medium"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("backToSignIn")}
        </Link>
      </form>
    </div>
  );
}
