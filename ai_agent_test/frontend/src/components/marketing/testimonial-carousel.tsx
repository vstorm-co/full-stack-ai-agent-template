"use client";

import { ChevronLeft, ChevronRight, Quote } from "lucide-react";
import { useEffect, useState } from "react";

interface Testimonial {
  quote: string;
  name: string;
  title: string;
  company: string;
}

interface TestimonialCarouselProps {
  items: Testimonial[];
  autoPlayMs?: number;
}

export function TestimonialCarousel({ items, autoPlayMs = 7000 }: TestimonialCarouselProps) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (!autoPlayMs) return;
    const t = setInterval(() => setActive((i) => (i + 1) % items.length), autoPlayMs);
    return () => clearInterval(t);
  }, [items.length, autoPlayMs]);

  const t = items[active];
  if (!t) return null;

  return (
    <div className="border-foreground/15 bg-card mx-auto max-w-3xl rounded-3xl border p-10 md:p-14">
      <Quote className="text-brand h-10 w-10" />
      <blockquote className="text-foreground font-display mt-6 text-2xl leading-snug font-medium md:text-3xl">
        &ldquo;{t.quote}&rdquo;
      </blockquote>
      <div className="mt-8 flex items-center justify-between">
        <div>
          <p className="text-foreground font-display font-semibold">{t.name}</p>
          <p className="text-foreground/55 text-sm">
            {t.title} · {t.company}
          </p>
        </div>
        {items.length > 1 && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActive((i) => (i - 1 + items.length) % items.length)}
              aria-label="Previous testimonial"
              className="border-foreground/20 hover:bg-foreground hover:text-background flex h-9 w-9 items-center justify-center rounded-full border transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setActive((i) => (i + 1) % items.length)}
              aria-label="Next testimonial"
              className="border-foreground/20 hover:bg-foreground hover:text-background flex h-9 w-9 items-center justify-center rounded-full border transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
