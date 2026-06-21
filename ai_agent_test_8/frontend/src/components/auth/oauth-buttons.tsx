"use client";

import { BACKEND_URL } from "@/lib/constants";

import { BrandIcon } from "@/components/marketing/brand-icon";

type Provider = "google" | "github" | "microsoft";

const LABELS: Record<Provider, string> = {
  google: "Continue with Google",
  github: "Continue with GitHub",
  microsoft: "Continue with Microsoft",
};

const ICON: Record<Provider, "google" | "github" | "microsoft"> = {
  google: "google",
  github: "github",
  microsoft: "microsoft",
};

function readProviders(): Provider[] {
  const raw = process.env.NEXT_PUBLIC_OAUTH_PROVIDERS;
  if (!raw) return [];
  return raw
    .split(",")
    .map((p) => p.trim().toLowerCase())
    .filter((p): p is Provider => p === "google" || p === "github" || p === "microsoft");
}

interface OAuthButtonsProps {
  next?: string;
  /** Override label suffix when used in register page. */
  variant?: "signin" | "signup";
}

export function OAuthButtons({ next, variant = "signin" }: OAuthButtonsProps) {
  const providers = readProviders();
  if (providers.length === 0) return null;

  return (
    <div className="space-y-2.5">
      {providers.map((provider) => {
        const url = `${BACKEND_URL}/api/v1/oauth/${provider}/login${
          next ? `?next=${encodeURIComponent(next)}` : ""
        }`;
        const label =
          variant === "signup" ? LABELS[provider].replace("Continue", "Sign up") : LABELS[provider];
        return (
          <a
            key={provider}
            href={url}
            className="border-foreground/15 hover:border-foreground/40 hover:bg-foreground/[0.03] text-foreground inline-flex h-11 w-full items-center justify-center gap-3 rounded-full border px-5 text-sm font-medium transition-colors"
          >
            <BrandIcon name={ICON[provider]} className="h-4 w-4" aria-hidden />
            {label}
          </a>
        );
      })}
    </div>
  );
}

export function OAuthBlock({ label, variant }: { label: string; variant?: "signin" | "signup" }) {
  if (!process.env.NEXT_PUBLIC_OAUTH_PROVIDERS) return null;
  return (
    <div className="space-y-5">
      <OAuthDivider label={label} />
      <OAuthButtons variant={variant} />
    </div>
  );
}

export function OAuthDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="bg-foreground/15 h-px flex-1" />
      <span className="text-foreground/45 font-mono text-[11px] tracking-wider uppercase">
        {label}
      </span>
      <span className="bg-foreground/15 h-px flex-1" />
    </div>
  );
}
