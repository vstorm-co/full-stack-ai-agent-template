"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { cn } from "@/lib/utils";

interface Plan {
  name: string;
  price: string;
  cadence?: string;
  description: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
  badge?: string;
}

interface PricingTeaserProps {
  plans: Plan[];
  fullPricingHref?: string;
}

/** Extracts the first integer from a price string ("$29" → 29, "129 zł" → 129).
 *  Returns -1 when there's no number (e.g. "Custom" tier). */
function parsePerSeat(priceStr: string): number {
  const m = priceStr.replace(/\s/g, "").match(/(\d+)/);
  return m?.[1] ? parseInt(m[1], 10) : -1;
}

/** Currency wrapping a parsed number — preserves the original prefix/suffix
 *  ("$" prefix vs. "zł" suffix). */
function currencyWrap(priceStr: string, value: number): string {
  const prefix = priceStr.startsWith("$") ? "$" : "";
  const suffix = priceStr.endsWith("zł") ? " zł" : "";
  return `${prefix}${value.toLocaleString()}${suffix}`;
}

/** Heuristic tier-from-seats: 1 seat → first tier (Starter / free),
 *  ≥ MID_SEATS → last tier, otherwise middle (Pro). */
const MID_SEATS = 50;
function inferTierIndex(seats: number, planCount: number): number {
  if (planCount <= 1) return 0;
  if (seats <= 1) return 0;
  if (seats >= MID_SEATS) return planCount - 1;
  return Math.min(1, planCount - 1);
}

export function PricingTeaser({ plans, fullPricingHref = "/pricing" }: PricingTeaserProps) {
  const t = useTranslations("marketing.landing.pricing.teaser");
  const [seats, setSeats] = useState(8);
  const [pinnedTier, setPinnedTier] = useState<number | null>(null);

  const activeIndex = pinnedTier ?? inferTierIndex(seats, plans.length);
  const activePlan = plans[activeIndex];
  // Empty plans list — nothing to render. (TS also needs this guard for
  // `noUncheckedIndexedAccess` to narrow `activePlan` below.)
  if (!activePlan) return null;
  const perSeat = parsePerSeat(activePlan.price);
  const isCustom = perSeat < 0;
  const total = isCustom ? null : perSeat * seats;

  return (
    <div className="border-foreground/10 bg-foreground/[0.02] relative isolate overflow-hidden rounded-3xl border p-8 md:p-14">
      {/* Brand glow under the price */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 -right-40 -z-10 h-[520px] w-[520px] rounded-full blur-3xl"
        style={{
          background:
            "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.3), transparent 65%)",
        }}
      />
      <div aria-hidden className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-50" />

      <div className="grid gap-12 md:grid-cols-[1.1fr_1fr] md:items-center">
        {/* LEFT — slider + price */}
        <div>
          <div className="mb-5 flex items-baseline justify-between gap-4">
            <label htmlFor="pricing-seats" className="eyebrow text-foreground/55">
              {t("seats")}
            </label>
            <span className="font-mono text-2xl tabular-nums">
              <span className="text-foreground">{seats}</span>{" "}
              <span className="text-foreground/55 text-base">{t("seatsUnit")}</span>
            </span>
          </div>
          <input
            id="pricing-seats"
            type="range"
            min={1}
            max={100}
            value={seats}
            onChange={(e) => {
              setSeats(parseInt(e.target.value, 10));
              setPinnedTier(null);
            }}
            className="bg-foreground/10 h-2 w-full cursor-pointer appearance-none rounded-full accent-[var(--color-brand)]"
          />

          <div className="mt-12 flex items-baseline gap-3">
            <div className="text-foreground font-mono text-[clamp(4.5rem,14vw,9.5rem)] leading-[0.85] font-medium tracking-tighter tabular-nums">
              {isCustom ? t("custom") : currencyWrap(activePlan.price, total ?? 0)}
            </div>
            {!isCustom && (
              <span className="text-foreground/55 font-mono text-lg">{t("perMonth")}</span>
            )}
          </div>
          <p className="text-foreground/50 mt-3 font-mono text-xs">{t("billedMonthly")}</p>
        </div>

        {/* RIGHT — tier pills, description, features, CTA */}
        <div>
          <div className="mb-6 flex flex-wrap gap-2">
            {plans.map((plan, i) => (
              <button
                key={plan.name}
                type="button"
                onClick={() => setPinnedTier(i)}
                className={cn(
                  "rounded-full border px-4 py-1.5 text-sm font-medium transition-all",
                  i === activeIndex
                    ? "border-brand bg-brand text-brand-foreground"
                    : "border-foreground/15 text-foreground/70 hover:border-foreground/40 hover:text-foreground",
                )}
              >
                {plan.name}
              </button>
            ))}
          </div>

          <p className="text-foreground/70 mb-6 text-base leading-relaxed">
            {activePlan.description}
          </p>

          <ul className="mb-8 space-y-2.5">
            {activePlan.features.slice(0, 4).map((f) => (
              <li key={f} className="text-foreground/85 flex items-start gap-3 text-sm">
                <span
                  aria-hidden
                  className="bg-brand mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                />
                {f}
              </li>
            ))}
          </ul>

          <div className="flex flex-wrap items-center gap-4">
            <Link
              href={activePlan.cta.href}
              className="bg-foreground text-background hover:bg-foreground/90 group inline-flex items-center gap-3 rounded-full py-2 pr-2 pl-6 text-base font-medium transition-colors"
            >
              <span>{activePlan.cta.label}</span>
              <span className="bg-brand text-brand-foreground flex h-9 w-9 items-center justify-center rounded-full transition-transform group-hover:rotate-45">
                <ArrowUpRight className="h-4 w-4" />
              </span>
            </Link>
            <Link
              href={fullPricingHref}
              className="text-foreground/65 hover:text-foreground border-foreground/15 hover:border-foreground/40 inline-flex items-center gap-2 border-b pb-1 text-sm font-medium transition-colors"
            >
              {t("seeFull")}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
