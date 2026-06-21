"use client";

import { usePathname } from "next/navigation";

import { locales } from "@/i18n";

/** Strip a leading locale segment (e.g. `/pl/chat` → `/chat`, `/dashboard` → `/dashboard`). */
export function stripLocale(pathname: string): string {
  const seg = pathname.split("/")[1];
  if (seg && (locales as readonly string[]).includes(seg)) {
    const rest = pathname.slice(seg.length + 1);
    return rest || "/";
  }
  return pathname || "/";
}

/**
 * Whether `href` matches the current path.
 * - `exact`: only an exact match (after stripping locale).
 * - otherwise: matches the path itself or any sub-path (`/billing` → `/billing/usage`).
 *   The root-ish `/` and `/dashboard` always match exactly to avoid false positives.
 */
export function isRouteActive(pathname: string, href: string, exact = false): boolean {
  const path = stripLocale(pathname);
  const target = href.split("?")[0]?.split("#")[0] || href;
  if (exact || target === "/" || target === "/dashboard") return path === target;
  return path === target || path.startsWith(`${target}/`);
}

/** Hook form: returns a predicate bound to the current pathname. */
export function useActiveRoute() {
  const pathname = usePathname() ?? "/";
  return (href: string, exact = false) => isRouteActive(pathname, href, exact);
}
