import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface SectionProps {
  children: ReactNode;
  theme?: "light" | "dark";
  className?: string;
  id?: string;
  /** Inner padding override. Default: py-32 md:py-44. */
  padding?: string;
  /** When true, the section reaches at least 90vh for a "full-screen" feel. */
  fullHeight?: boolean;
}

/** Marketing section wrapper. Sets local theme tokens via `.theme-light`/`.theme-dark`,
 *  applies background + foreground from those tokens, and provides a max-width container.
 *  Renders a subtle hairline + radial glow at the top edge so adjacent dark/light
 *  sections separate cleanly without a hard cut. */
export function Section({
  children,
  theme = "light",
  className,
  id,
  padding = "py-32 md:py-44",
  fullHeight = false,
}: SectionProps) {
  return (
    <section
      id={id}
      className={cn(
        theme === "dark" ? "theme-dark" : "theme-light",
        "bg-background text-foreground relative",
        padding,
        fullHeight && "flex min-h-[90vh] flex-col justify-center",
        className,
      )}
    >
      {/* Top hairline with radial fade — softens the dark↔light transition */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            "radial-gradient(ellipse 50% 100% at 50% 0%, oklch(from var(--color-foreground) l c h / 0.15), transparent 70%)",
        }}
      />
      <div className="mx-auto w-full max-w-7xl px-6 md:px-10">{children}</div>
    </section>
  );
}
