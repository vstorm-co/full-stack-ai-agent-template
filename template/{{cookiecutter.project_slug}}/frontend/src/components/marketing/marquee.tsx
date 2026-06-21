import { cn } from "@/lib/utils";

interface MarqueeProps {
  /** First row items. Defaults to scrolling right→left. */
  items: string[];
  /** Optional second row. If provided, scrolls in the opposite direction. */
  itemsBottom?: string[];
  /** Highlight every Nth item with the brand color. */
  highlightEvery?: number;
  className?: string;
}

export function Marquee({ items, itemsBottom, highlightEvery = 4, className }: MarqueeProps) {
  return (
    <div
      className={cn(
        "marquee-strip bg-foreground text-background relative isolate overflow-hidden py-6 select-none md:py-8",
        className,
      )}
    >
      <Row items={items} highlightEvery={highlightEvery} direction="left" />
      {itemsBottom && itemsBottom.length > 0 && (
        <div className="mt-4 md:mt-6">
          <Row items={itemsBottom} highlightEvery={highlightEvery} direction="right" />
        </div>
      )}
    </div>
  );
}

interface RowProps {
  items: string[];
  highlightEvery: number;
  direction: "left" | "right";
}

function Row({ items, highlightEvery, direction }: RowProps) {
  // Duplicate so the scroll loop is seamless
  const doubled = [...items, ...items];
  return (
    <div className="marquee">
      <div
        className={cn(
          "marquee-track text-3xl font-bold tracking-tight md:text-5xl",
          direction === "right" && "marquee-track-rev",
        )}
      >
        {doubled.map((item, i) => {
          const highlighted = i % highlightEvery === 0;
          return (
            <span
              key={`${item}-${i}`}
              className={cn(
                "flex shrink-0 items-center gap-10 md:gap-14",
                highlighted && "text-brand",
              )}
            >
              {item}
              <span aria-hidden className="text-background/35 text-2xl md:text-3xl">
                ✦
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}
