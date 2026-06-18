"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LanguageSwitcherCompact } from "@/components/language-switcher";
import { cn } from "@/lib/utils";

interface NavLink {
  label: string;
  href: string;
}

interface PillNavProps {
  brand: string;
  links: NavLink[];
  ctaLabel: string;
  ctaHref: string;
  secondaryCta?: { label: string; href: string };
}

export function PillNav({ brand, links, ctaLabel, ctaHref, secondaryCta }: PillNavProps) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 32);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "theme-dark",
        "fixed inset-x-0 top-4 z-50 mx-auto flex w-[min(96%,1100px)] items-center justify-between gap-2 px-3 py-2 transition-all",
        scrolled ? "pill-nav shadow-lg" : "pill-nav",
      )}
    >
      <Link
        href="/"
        className="font-display text-foreground flex items-center gap-2 px-3 text-base font-bold tracking-tight"
      >
        <span aria-hidden className="bg-brand inline-block h-2.5 w-2.5 rounded-full" />
        {brand}
      </Link>

      <nav className="hidden items-center gap-1 md:flex">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="text-foreground/70 hover:text-foreground rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
          >
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="flex items-center gap-2">
        <div className="hidden md:block">
          <LanguageSwitcherCompact />
        </div>
        {secondaryCta && (
          <Link
            href={secondaryCta.href}
            className="bg-brand text-brand-foreground hover:bg-brand-hover hidden rounded-full px-4 py-2 text-sm font-medium transition-colors md:inline-flex"
          >
            {secondaryCta.label}
          </Link>
        )}
        <Link
          href={ctaHref}
          className="bg-foreground text-background hover:bg-foreground/90 rounded-full px-5 py-2 text-sm font-medium transition-colors"
        >
          {ctaLabel}
        </Link>
      </div>
    </header>
  );
}
