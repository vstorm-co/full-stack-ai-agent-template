import { cn } from "@/lib/utils";

type Glyph = "agents" | "rag" | "billing";

interface FeatureGlyphProps {
  glyph: Glyph;
  className?: string;
}

/** Decorative SVG illustrations used as visual fillers for FeatureSection.
 *  Two-color (foreground + brand), 1.5px stroke, abstract — not literal. */
export function FeatureGlyph({ glyph, className }: FeatureGlyphProps) {
  const cls = cn("h-auto w-full max-w-md", className);

  if (glyph === "agents") {
    return (
      <svg
        viewBox="0 0 480 360"
        className={cls}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        <rect x="60" y="60" width="360" height="240" rx="24" className="text-foreground/15" />
        <rect x="100" y="100" width="160" height="80" rx="12" className="text-foreground/40" />
        <rect x="100" y="200" width="120" height="60" rx="12" className="text-foreground/30" />
        <rect
          x="280"
          y="100"
          width="120"
          height="160"
          rx="12"
          className="text-brand fill-brand/15"
        />
        <circle cx="340" cy="140" r="14" className="text-foreground" />
        <path
          d="M310 200 L370 200 M310 220 L350 220 M310 240 L360 240"
          className="text-foreground/60"
        />
      </svg>
    );
  }

  if (glyph === "rag") {
    return (
      <svg
        viewBox="0 0 480 360"
        className={cls}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        {[0, 1, 2].map((i) => (
          <rect
            key={i}
            x={80 + i * 18}
            y={80 + i * 18}
            width="200"
            height="240"
            rx="12"
            className="text-foreground/25"
          />
        ))}
        <rect
          x="116"
          y="116"
          width="200"
          height="240"
          rx="12"
          className="text-foreground bg-card"
          fill="currentColor"
          fillOpacity="0.04"
        />
        <path
          d="M140 160 L290 160 M140 190 L260 190 M140 220 L280 220 M140 250 L240 250"
          className="text-foreground/50"
        />
        <circle cx="380" cy="100" r="48" className="text-brand fill-brand/20" />
        <path d="M362 100 L380 118 L406 88" strokeWidth="2" className="text-brand-foreground" />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 480 360"
      className={cls}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <rect
        x="60"
        y="80"
        width="360"
        height="200"
        rx="20"
        className="text-foreground/15 fill-card"
        fill="currentColor"
        fillOpacity="0.4"
      />
      <text
        x="100"
        y="150"
        fontFamily="ui-monospace"
        fontSize="36"
        fontWeight="700"
        className="text-foreground"
        fill="currentColor"
      >
        $2,840
      </text>
      <text
        x="100"
        y="178"
        fontFamily="ui-monospace"
        fontSize="13"
        className="text-foreground/55"
        fill="currentColor"
      >
        Monthly recurring
      </text>
      <path
        d="M100 230 L150 215 L200 220 L250 200 L300 195 L350 175 L390 160"
        className="text-brand"
        strokeWidth="2.5"
      />
      <circle cx="390" cy="160" r="6" className="fill-brand text-brand" fill="currentColor" />
      <rect x="100" y="250" width="60" height="14" rx="3" className="text-foreground/25" />
      <rect x="170" y="250" width="40" height="14" rx="3" className="text-foreground/25" />
      <rect x="220" y="250" width="80" height="14" rx="3" className="text-foreground/25" />
    </svg>
  );
}
