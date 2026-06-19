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
    <div
      className={cn(
        "border-foreground/10 bg-card/40 rounded-2xl border px-6 py-10 backdrop-blur-sm md:px-10",
        className,
      )}
    >
      {label && <p className="eyebrow text-foreground/50 mb-8 text-center">{label}</p>}
      <ul className="grid grid-cols-2 items-center gap-y-8 sm:grid-cols-4 md:flex md:flex-wrap md:justify-between md:gap-x-4">
        {logos.map((logo, i) => (
          <li
            key={logo.name}
            className={cn(
              "text-foreground/50 hover:text-foreground flex items-center justify-center gap-2 transition-colors md:flex-1",
              i > 0 && "md:border-foreground/10 md:border-l",
            )}
          >
            {logo.brand && <BrandIcon name={logo.brand} className="h-5 w-5 md:h-6 md:w-6" />}
            <span className="font-display text-lg font-bold tracking-tight md:text-xl">
              {logo.name}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
