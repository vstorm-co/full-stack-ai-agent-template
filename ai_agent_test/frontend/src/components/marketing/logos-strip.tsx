import { cn } from "@/lib/utils";

import { BrandIcon } from "./brand-icon";

type LogoBrand = Parameters<typeof BrandIcon>[0]["name"];

interface LogoEntry {
  brand?: LogoBrand;
  name: string;
}

interface LogosStripProps {
  label?: string;
  logos: LogoEntry[];
  className?: string;
}

/** Customer-logos strip. Each entry pairs a brand glyph with a wordmark.
 *  Renders monochrome (grayscale-ish via opacity) so the strip reads as a
 *  cohesive band, not a kaleidoscope. */
export function LogosStrip({ label, logos, className }: LogosStripProps) {
  return (
    <div className={cn("space-y-8", className)}>
      {label && <p className="eyebrow text-foreground/55 text-center">{label}</p>}
      <ul className="grid grid-cols-2 items-center gap-x-8 gap-y-8 md:flex md:flex-wrap md:justify-center md:gap-x-12">
        {logos.map((logo) => (
          <li
            key={logo.name}
            className="text-foreground/55 hover:text-foreground/85 flex items-center justify-center gap-2 transition-colors"
          >
            {logo.brand && <BrandIcon name={logo.brand} className="h-5 w-5 md:h-6 md:w-6" />}
            <span className="font-display text-xl font-bold tracking-tight md:text-2xl">
              {logo.name}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
