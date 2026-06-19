{% raw %}import { Star } from "lucide-react";

interface Testimonial {
  quote: string;
  name: string;
  title: string;
  company: string;
}

interface TestimonialGridProps {
  items: Testimonial[];
}

const INITIALS = (name: string) =>
  name
    .split(" ")
    .map((n) => n[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

export function TestimonialGrid({ items }: TestimonialGridProps) {
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {items.map((t, i) => (
        <figure
          key={`${t.name}-${i}`}
          className="border-foreground/15 bg-card lift hover:border-foreground/25 flex flex-col gap-5 rounded-2xl border p-7 transition-colors"
        >
          <div className="flex items-center gap-0.5" aria-label="Rated 5 out of 5">
            {Array.from({ length: 5 }).map((_, s) => (
              <Star key={s} className="fill-brand text-brand h-4 w-4" />
            ))}
          </div>
          <blockquote className="text-foreground/90 flex-1 text-base leading-relaxed">
            &ldquo;{t.quote}&rdquo;
          </blockquote>
          <figcaption className="border-foreground/10 flex items-center gap-3 border-t pt-5">
            <span
              aria-hidden
              className="text-brand-foreground flex h-10 w-10 items-center justify-center rounded-full font-mono text-xs font-semibold"
              style={{
                background: `linear-gradient(135deg, oklch(from var(--color-brand) l c calc(h + ${i * 40})), oklch(from var(--color-brand) calc(l - 0.12) c calc(h + ${i * 40})))`,
              }}
            >
              {INITIALS(t.name)}
            </span>
            <div>
              <p className="text-foreground text-sm font-semibold">{t.name}</p>
              <p className="text-foreground/55 text-xs">
                {t.title} · {t.company}
              </p>
            </div>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
{% endraw %}
