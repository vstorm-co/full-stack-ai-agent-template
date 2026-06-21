"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  BarChart3,
  ChevronDown,
  Code,
  Database,
  FlaskConical,
  LifeBuoy,
  Menu,
  Newspaper,
  ShieldCheck,
  Sparkles,
  Tag,
  TrendingUp,
  Users,
  Workflow,
  X,
  type LucideIcon,
} from "lucide-react";

{% if cookiecutter.enable_i18n -%}
import { LanguageSwitcherCompact } from "@/components/language-switcher";
{% endif -%}
import type { NavIcon, NavItem } from "@/components/marketing/footer-config";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface PillNavProps {
  brand: string;
  links: NavItem[];
  ctaLabel: string;
  ctaHref: string;
  secondaryCta?: { label: string; href: string };
}

const ICONS: Record<NavIcon, LucideIcon> = {
  sparkles: Sparkles,
  workflow: Workflow,
  insights: BarChart3,
  changelog: Tag,
  support: LifeBuoy,
  sales: TrendingUp,
  knowledge: Database,
  research: FlaskConical,
  help: LifeBuoy,
  api: Code,
  security: ShieldCheck,
  community: Users,
  blog: Newspaper,
};

const isExternal = (href: string) => /^https?:\/\//.test(href);

export function PillNav({ brand, links, ctaLabel, ctaHref, secondaryCta }: PillNavProps) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false); // mobile overlay
  const [openMenu, setOpenMenu] = useState<number | null>(null); // desktop dropdown
  const [mobileSection, setMobileSection] = useState<number | null>(null);
  const pathname = usePathname();
  const headerRef = useRef<HTMLElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
    setOpenMenu(null);
  }, [pathname]);

  // Lock scroll + Escape while the mobile overlay is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Close desktop dropdown on Escape / outside click.
  useEffect(() => {
    if (openMenu === null) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpenMenu(null);
    const onClick = (e: MouseEvent) => {
      if (headerRef.current && !headerRef.current.contains(e.target as Node)) setOpenMenu(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [openMenu]);

  const hoverOpen = (i: number) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpenMenu(i);
  };
  const hoverClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setOpenMenu(null), 140);
  };

  return (
    <header
      ref={headerRef}
      className={cn(
        "theme-dark fixed inset-x-0 top-0 z-50 border-b transition-colors duration-300",
        scrolled || open
          ? "border-border bg-background/85 shadow-[0_8px_30px_-12px_oklch(0%_0_0_/_0.5)] backdrop-blur-xl"
          : "border-foreground/10 bg-background/55 backdrop-blur-md",
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-6 md:px-10">
        <Link
          href={ROUTES.HOME}
          className="font-display text-foreground flex shrink-0 items-center gap-2.5 text-base font-bold tracking-tight"
        >
          <span
            aria-hidden
            className="inline-flex h-7 w-7 items-center justify-center rounded-[0.6rem]"
            {% raw %}style={{
              background:
                "linear-gradient(135deg, var(--color-brand), oklch(from var(--color-brand) calc(l - 0.14) c h))",
              boxShadow:
                "inset 0 1px 0 oklch(100% 0 0 / 0.25), 0 6px 16px -8px oklch(from var(--color-brand) l c h / 0.8)",
            }}{% endraw %}
          >
            <span className="text-brand-foreground font-display text-sm leading-none font-extrabold">
              {brand.charAt(0).toUpperCase()}
            </span>
          </span>
          {brand}
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((item, i) =>
            item.items ? (
              <div
                key={item.label}
                className="relative"
                onMouseEnter={() => hoverOpen(i)}
                onMouseLeave={hoverClose}
              >
                <button
                  type="button"
                  onClick={() => setOpenMenu((v) => (v === i ? null : i))}
                  aria-expanded={openMenu === i}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full px-3.5 py-2 text-sm font-medium transition-colors",
                    openMenu === i
                      ? "text-foreground bg-foreground/5"
                      : "text-foreground/70 hover:text-foreground hover:bg-foreground/5",
                  )}
                >
                  {item.label}
                  <ChevronDown
                    className={cn(
                      "h-3.5 w-3.5 transition-transform duration-200",
                      openMenu === i && "rotate-180",
                    )}
                  />
                </button>

                {openMenu === i && (
                  <MegaPanel item={item} align={i >= links.length - 1 ? "right" : "left"} />
                )}
              </div>
            ) : (
              <Link
                key={item.label}
                href={item.href!}
                className="text-foreground/70 hover:text-foreground hover:bg-foreground/5 rounded-full px-3.5 py-2 text-sm font-medium transition-colors"
              >
                {item.label}
              </Link>
            ),
          )}
        </nav>

        <div className="flex items-center gap-1.5">
{%- if cookiecutter.enable_i18n %}
          <div className="hidden md:block">
            <LanguageSwitcherCompact />
          </div>
{%- endif %}
          {secondaryCta && (
            <Link
              href={secondaryCta.href}
              className="text-foreground/75 hover:text-foreground hover:bg-foreground/5 hidden rounded-full px-4 py-2 text-sm font-medium transition-colors md:inline-flex"
            >
              {secondaryCta.label}
            </Link>
          )}
          <Link
            href={ctaHref}
            className="bg-brand text-brand-foreground hover:bg-brand-hover group hidden items-center gap-1.5 rounded-full py-2 pr-2.5 pl-4 text-sm font-medium transition-colors md:inline-flex"
          >
            {ctaLabel}
            <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>

          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            className="text-foreground/80 hover:text-foreground hover:bg-foreground/5 inline-flex h-10 w-10 items-center justify-center rounded-full transition-colors md:hidden"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="theme-dark bg-background fixed inset-0 top-16 z-40 animate-[lsFadeIn_180ms_var(--ease-out)] overflow-y-auto md:hidden">
          <div className="flex min-h-full flex-col px-6 py-6">
            <nav className="flex flex-col gap-1">
              {links.map((item, i) =>
                item.items ? (
                  <div key={item.label} className="border-foreground/10 border-b py-1">
                    <button
                      type="button"
                      onClick={() => setMobileSection((v) => (v === i ? null : i))}
                      aria-expanded={mobileSection === i}
                      className="text-foreground flex w-full items-center justify-between py-3 text-lg font-semibold"
                    >
                      {item.label}
                      <ChevronDown
                        className={cn(
                          "text-foreground/50 h-5 w-5 transition-transform duration-200",
                          mobileSection === i && "rotate-180",
                        )}
                      />
                    </button>
                    {mobileSection === i && (
                      <div className="flex flex-col pb-3">
                        {item.items.map((sub) => {
                          const Icon = sub.icon ? ICONS[sub.icon] : null;
                          return (
                            <Link
                              key={sub.href + sub.label}
                              href={sub.href}
                              target={isExternal(sub.href) ? "_blank" : undefined}
                              rel={isExternal(sub.href) ? "noopener noreferrer" : undefined}
                              onClick={() => setOpen(false)}
                              className="hover:bg-foreground/5 flex items-start gap-3 rounded-xl px-2 py-2.5"
                            >
                              {Icon && (
                                <span className="bg-foreground/5 text-foreground/80 mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
                                  <Icon className="h-4 w-4" />
                                </span>
                              )}
                              <span>
                                <span className="text-foreground block text-sm font-medium">
                                  {sub.label}
                                </span>
                                {sub.description && (
                                  <span className="text-foreground/55 block text-xs">
                                    {sub.description}
                                  </span>
                                )}
                              </span>
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ) : (
                  <Link
                    key={item.label}
                    href={item.href!}
                    onClick={() => setOpen(false)}
                    className="text-foreground border-foreground/10 border-b py-4 text-lg font-semibold"
                  >
                    {item.label}
                  </Link>
                ),
              )}
            </nav>

            <div className="mt-auto flex flex-col gap-3 pt-8">
{%- if cookiecutter.enable_i18n %}
              <LanguageSwitcherCompact />
{%- endif %}
              {secondaryCta && (
                <Link
                  href={secondaryCta.href}
                  onClick={() => setOpen(false)}
                  className="border-foreground/15 text-foreground hover:bg-foreground/5 inline-flex items-center justify-center rounded-full border px-5 py-3 text-sm font-medium transition-colors"
                >
                  {secondaryCta.label}
                </Link>
              )}
              <Link
                href={ctaHref}
                onClick={() => setOpen(false)}
                className="bg-brand text-brand-foreground hover:bg-brand-hover inline-flex items-center justify-center gap-1.5 rounded-full px-5 py-3 text-sm font-medium transition-colors"
              >
                {ctaLabel}
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

function MegaPanel({ item, align }: { item: NavItem; align: "left" | "right" }) {
  return (
    <div
      className={cn(
        "absolute top-full animate-[lsFadeIn_160ms_var(--ease-out)] pt-3",
        align === "right" ? "right-0" : "left-0",
      )}
    >
      <div className="border-border bg-card/95 w-[min(92vw,420px)] overflow-hidden rounded-2xl border shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col p-2">
          {item.items!.map((sub) => {
            const Icon = sub.icon ? ICONS[sub.icon] : null;
            return (
              <Link
                key={sub.href + sub.label}
                href={sub.href}
                target={isExternal(sub.href) ? "_blank" : undefined}
                rel={isExternal(sub.href) ? "noopener noreferrer" : undefined}
                className="group/item hover:bg-foreground/5 flex items-start gap-3 rounded-xl p-3 transition-colors"
              >
                {Icon && (
                  <span className="border-border bg-background text-foreground/80 group-hover/item:text-brand group-hover/item:border-brand/30 mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-colors">
                    <Icon className="h-4 w-4" />
                  </span>
                )}
                <span className="min-w-0">
                  <span className="text-foreground flex items-center gap-1 text-sm font-medium">
                    {sub.label}
                    {isExternal(sub.href) && (
                      <ArrowUpRight className="text-foreground/40 h-3 w-3" />
                    )}
                  </span>
                  {sub.description && (
                    <span className="text-foreground/55 mt-0.5 block text-xs leading-relaxed">
                      {sub.description}
                    </span>
                  )}
                </span>
              </Link>
            );
          })}
        </div>

        {item.featured && (
          <Link
            href={item.featured.href}
            className="border-border text-foreground/80 hover:text-foreground hover:bg-foreground/5 flex items-center justify-between border-t px-5 py-3.5 text-sm font-medium transition-colors"
          >
            {item.featured.label}
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        )}
      </div>
    </div>
  );
}
