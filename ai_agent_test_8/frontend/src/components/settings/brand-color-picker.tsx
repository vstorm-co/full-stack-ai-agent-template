"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

interface Preset {
  key: string;
  label: string;
  description: string;
  /** OKLCH parts */
  h: number;
  c: number;
  l: number;
  /** Foreground color paired with the brand fill (oklch lightness 0-100). */
  fgL: number;
}

// Presets aligned with the CLI `--brand-color` choices so the in-app picker
// can return to whatever the project was generated with.
const PRESETS: Preset[] = [
  {
    key: "blue",
    label: "Blue",
    description: "Stripe / Vercel — classic SaaS",
    h: 250,
    c: 0.2,
    l: 65,
    fgL: 98,
  },
  {
    key: "green",
    label: "Green",
    description: "Calm, fresh, healthtech",
    h: 155,
    c: 0.18,
    l: 65,
    fgL: 98,
  },
  {
    key: "red",
    label: "Red",
    description: "Warm, energetic",
    h: 25,
    c: 0.2,
    l: 60,
    fgL: 98,
  },
  {
    key: "violet",
    label: "Violet",
    description: "Linear / Anthropic — modern AI",
    h: 295,
    c: 0.22,
    l: 65,
    fgL: 98,
  },
  {
    key: "orange",
    label: "Orange",
    description: "Warm, friendly, B2C",
    h: 55,
    c: 0.18,
    l: 72,
    fgL: 15,
  },
];

// Default preset chosen at template-generation time via `--brand-color`.
const DEFAULT_PRESET_KEY = "blue";

const STORAGE_KEY = "settings.brand_color_preset";

function applyPreset(p: Preset) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  // Tailwind v4 resolves the `oklch(var(--brand-l)...)` composition at build
  // time, so overriding the parts at runtime has no effect on utilities. Set
  // the final color tokens directly — those are what `bg-brand` / `text-brand`
  // / charts read.
  const brand = `oklch(${p.l}% ${p.c} ${p.h})`;
  const brandHover = `oklch(${Math.max(0, p.l - 8)}% ${p.c} ${p.h})`;
  const brandMuted = `oklch(${p.l}% ${p.c * 0.4} ${p.h})`;
  const brandFg = `oklch(${p.fgL}% 0 0)`;
  // Charts: use a darker brand variant on light themes (so the brand stays
  // readable on white surfaces), but full brand on dark themes — matches the
  // logic baked into globals.css.
  const chart = `oklch(55% ${p.c} ${p.h})`;
  root.style.setProperty("--brand-h", String(p.h));
  root.style.setProperty("--brand-c", String(p.c));
  root.style.setProperty("--brand-l", `${p.l}%`);
  root.style.setProperty("--color-brand", brand);
  root.style.setProperty("--color-brand-hover", brandHover);
  root.style.setProperty("--color-brand-muted", brandMuted);
  root.style.setProperty("--color-brand-foreground", brandFg);
  root.style.setProperty("--color-chart", chart);
}

export function BrandColorPicker() {
  const defaultPreset = PRESETS.find((p) => p.key === DEFAULT_PRESET_KEY) ?? PRESETS[0]!;
  const [active, setActive] = useState<string>(defaultPreset.key);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const preset = PRESETS.find((p) => p.key === saved);
      if (preset) {
        setActive(preset.key);
        applyPreset(preset);
      }
    }
  }, []);

  const handlePick = (preset: Preset) => {
    setActive(preset.key);
    applyPreset(preset);
    document.documentElement.setAttribute("data-brand", preset.key);
    window.localStorage.setItem(STORAGE_KEY, preset.key);
  };

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {PRESETS.map((p) => {
        const swatch = `oklch(${p.l}% ${p.c} ${p.h})`;
        const isActive = active === p.key;
        return (
          <button
            key={p.key}
            type="button"
            onClick={() => handlePick(p)}
            className={cn(
              "lift flex items-center gap-3 rounded-xl border p-3.5 text-left transition-colors",
              isActive
                ? "border-foreground bg-foreground/[0.04]"
                : "border-foreground/10 bg-background hover:border-foreground/30",
            )}
          >
            <span
              aria-hidden
              className="border-foreground/15 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border"
              style={{ background: swatch }}
            >
              {isActive && <Check className="h-4 w-4" style={{ color: `oklch(${p.fgL}% 0 0)` }} />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-foreground text-sm font-semibold">{p.label}</p>
              <p className="text-foreground/55 truncate text-xs">{p.description}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}
