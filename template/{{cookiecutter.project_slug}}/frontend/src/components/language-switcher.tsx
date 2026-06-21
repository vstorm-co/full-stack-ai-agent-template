"use client";

import { Check, Globe } from "lucide-react";
import { useLocale } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { locales, defaultLocale, type Locale, getLocaleLabel, getLocaleFlag } from "@/i18n";
import { cn } from "@/lib/utils";

/**
 * Build a path for the given locale, preserving the rest of the route.
 * Handles `localePrefix: "as-needed"` — default locale has no prefix.
 */
function buildLocalizedPath(pathname: string, newLocale: Locale): string {
  const segments = pathname.split("/").filter(Boolean);
  const first = segments[0];
  if (first && (locales as readonly string[]).includes(first)) {
    segments.shift();
  }
  const rest = segments.join("/");
  if (newLocale === defaultLocale) {
    return rest ? `/${rest}` : "/";
  }
  return rest ? `/${newLocale}/${rest}` : `/${newLocale}`;
}

/**
 * Default language switcher — segmented pills (EN | PL).
 * Used in the dashboard footer / settings, where space allows two buttons.
 */
export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleChange = (newLocale: Locale) => {
    router.push(buildLocalizedPath(pathname, newLocale));
  };

  return (
    <div className="flex gap-1">
      {locales.map((loc) => (
        <button
          key={loc}
          onClick={() => handleChange(loc)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            locale === loc
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-label={getLocaleLabel(loc)}
          aria-pressed={locale === loc}
        >
          {loc.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

/**
 * Compact language switcher — globe icon + dropdown.
 * Designed to sit in pill-nav between links and CTAs. The trigger matches
 * the pill aesthetic; the menu uses the dark/light theme tokens so it
 * inherits whichever section it's rendered in.
 */
export function LanguageSwitcherCompact() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!wrapperRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const handleChange = (newLocale: Locale) => {
    router.push(buildLocalizedPath(pathname, newLocale));
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Language"
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          "border-foreground/15 hover:border-foreground/40 hover:bg-foreground/[0.04]",
          "text-foreground/85 inline-flex items-center gap-1.5 rounded-full border bg-transparent",
          "px-3 py-1.5 text-xs font-medium tracking-wider uppercase transition-colors",
          "focus-visible:ring-brand/50 focus-visible:ring-2 focus-visible:outline-none",
        )}
      >
        <Globe className="h-3.5 w-3.5" aria-hidden />
        {locale}
      </button>

      {open && (
        <div
          role="menu"
          className={cn(
            "border-foreground/10 bg-card text-card-foreground absolute top-full right-0",
            "mt-2 min-w-[180px] origin-top-right overflow-hidden rounded-2xl border",
            "shadow-lg shadow-black/5 backdrop-blur",
          )}
          style={ {
            animation: "lsFadeIn 140ms cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        >
          {locales.map((loc) => {
            const active = loc === locale;
            return (
              <button
                key={loc}
                type="button"
                role="menuitemradio"
                aria-checked={active}
                onClick={() => handleChange(loc)}
                className={cn(
                  "flex w-full items-center gap-3 px-3.5 py-2.5 text-left text-sm transition-colors",
                  active
                    ? "bg-foreground/[0.06] text-foreground font-medium"
                    : "text-foreground/75 hover:bg-foreground/[0.04] hover:text-foreground",
                )}
              >
                <span aria-hidden className="text-base leading-none">
                  {getLocaleFlag(loc)}
                </span>
                <span className="flex-1">{getLocaleLabel(loc)}</span>
                <span
                  aria-hidden
                  className={cn(
                    "font-mono text-[10px] tracking-wider uppercase",
                    active ? "text-brand" : "text-foreground/40",
                  )}
                >
                  {loc}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Icon-button language switcher — globe icon trigger + Radix dropdown.
 * Designed for the app toolbar (header), where it sits alongside other
 * icon-only controls. Matches the flat toolbar aesthetic (h-9 w-9, rounded-lg,
 * hover:bg-accent) and reuses the shared DropdownMenu so its menu styling is
 * consistent with the org/user menus.
 */
export function LanguageSwitcherIcon() {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();

  const handleChange = (newLocale: Locale) => {
    router.push(buildLocalizedPath(pathname, newLocale));
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Language"
          className={cn(
            "text-muted-foreground hover:text-foreground hover:bg-accent",
            "focus-visible:ring-ring inline-flex h-9 w-9 items-center justify-center rounded-lg",
            "transition-colors outline-none focus-visible:ring-1",
          )}
        >
          <Globe className="h-[1.1rem] w-[1.1rem]" aria-hidden />
          <span className="sr-only">{getLocaleLabel(locale)}</span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {locales.map((loc) => {
          const active = loc === locale;
          return (
            <DropdownMenuItem
              key={loc}
              onSelect={() => handleChange(loc)}
              className="gap-2.5"
            >
              <span aria-hidden className="text-base leading-none">
                {getLocaleFlag(loc)}
              </span>
              <span className="flex-1">{getLocaleLabel(loc)}</span>
              {active ? (
                <Check className="text-foreground h-4 w-4" />
              ) : (
                <span className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">
                  {loc}
                </span>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
