"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Cookie, X } from "lucide-react";

const STORAGE_KEY = "cookie.consent";

interface CookieConsent {
  essential: true; // always required
  analytics: boolean;
  functional: boolean;
  decided_at: string;
}

function readConsent(): CookieConsent | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed.decided_at !== "string") return null;
    return parsed as CookieConsent;
  } catch {
    return null;
  }
}

function writeConsent(consent: CookieConsent) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(consent));
  window.dispatchEvent(new Event("cookie-consent-change"));
}

export function CookieBanner() {
  const [show, setShow] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [analytics, setAnalytics] = useState(true);
  const [functional, setFunctional] = useState(true);

  useEffect(() => {
    const decide = () => {
      const consent = readConsent();
      setShow(!consent);
    };
    decide();
    window.addEventListener("storage", decide);
    window.addEventListener("cookie-consent-change", decide);
    return () => {
      window.removeEventListener("storage", decide);
      window.removeEventListener("cookie-consent-change", decide);
    };
  }, []);

  const close = () => setShow(false);

  const acceptAll = () => {
    writeConsent({
      essential: true,
      analytics: true,
      functional: true,
      decided_at: new Date().toISOString(),
    });
    close();
  };

  const rejectAll = () => {
    writeConsent({
      essential: true,
      analytics: false,
      functional: false,
      decided_at: new Date().toISOString(),
    });
    close();
  };

  const savePrefs = () => {
    writeConsent({
      essential: true,
      analytics,
      functional,
      decided_at: new Date().toISOString(),
    });
    close();
  };

  if (!show) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="cookie-banner-title"
      className="fixed inset-x-0 bottom-0 z-[55] p-4 md:right-4 md:bottom-4 md:left-auto md:max-w-md"
    >
      <div className="border-foreground/15 bg-card text-foreground rounded-2xl border shadow-2xl">
        <div className="flex items-start gap-3 p-5">
          <span className="bg-brand/15 text-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full">
            <Cookie className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p
              id="cookie-banner-title"
              className="text-foreground font-display text-sm font-semibold tracking-tight"
            >
              We use cookies
            </p>
            <p className="text-foreground/65 mt-1 text-xs leading-relaxed">
              Essential cookies keep you signed in. Optional ones help us understand how the product
              is used. See our{" "}
              <Link
                href="/legal/cookies"
                className="text-foreground underline-offset-4 hover:underline"
              >
                cookie policy
              </Link>
              .
            </p>
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={close}
            className="text-foreground/45 hover:text-foreground hover:bg-foreground/5 -mt-1 -mr-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {showPrefs && (
          <div className="border-foreground/10 space-y-3 border-t px-5 py-4">
            <Toggle
              label="Essential"
              description="Required to keep you signed in. Cannot be disabled."
              checked
              disabled
              onChange={() => {}}
            />
            <Toggle
              label="Analytics"
              description="Aggregated, anonymized usage data."
              checked={analytics}
              onChange={setAnalytics}
            />
            <Toggle
              label="Functional"
              description="Remembers preferences (theme, onboarding state)."
              checked={functional}
              onChange={setFunctional}
            />
          </div>
        )}

        <div className="border-foreground/10 flex flex-wrap items-center gap-2 border-t px-5 py-3">
          {showPrefs ? (
            <>
              <button
                type="button"
                onClick={savePrefs}
                className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center rounded-full px-4 py-1.5 text-xs font-medium transition-colors"
              >
                Save preferences
              </button>
              <button
                type="button"
                onClick={() => setShowPrefs(false)}
                className="text-foreground/55 hover:text-foreground text-xs font-medium"
              >
                Back
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={acceptAll}
                className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center rounded-full px-4 py-1.5 text-xs font-medium transition-colors"
              >
                Accept all
              </button>
              <button
                type="button"
                onClick={rejectAll}
                className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex items-center rounded-full border px-4 py-1.5 text-xs font-medium transition-colors"
              >
                Reject optional
              </button>
              <button
                type="button"
                onClick={() => setShowPrefs(true)}
                className="text-foreground/55 hover:text-foreground ml-auto text-xs font-medium"
              >
                Preferences
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Toggle({
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start justify-between gap-3">
      <span className="min-w-0 flex-1">
        <span className="text-foreground block text-xs font-semibold">{label}</span>
        <span className="text-foreground/55 mt-0.5 block text-[11px] leading-snug">
          {description}
        </span>
      </span>
      <span
        className={`relative inline-block h-5 w-9 shrink-0 rounded-full transition-colors ${
          checked ? "bg-brand" : "bg-foreground/20"
        } ${disabled ? "opacity-50" : ""}`}
      >
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <span
          aria-hidden
          className={`bg-card absolute top-0.5 h-4 w-4 rounded-full shadow transition-transform ${
            checked ? "translate-x-[1.125rem]" : "translate-x-0.5"
          }`}
        />
      </span>
    </label>
  );
}
