import { Quote } from "lucide-react";

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
          className="border-foreground/15 bg-card flex flex-col gap-6 rounded-2xl border p-7"
        >
          <Quote className="text-brand h-6 w-6" />
          <blockquote className="text-foreground flex-1 text-base leading-relaxed">
            &ldquo;{t.quote}&rdquo;
          </blockquote>
          <figcaption className="border-foreground/10 flex items-center gap-3 border-t pt-5">
            <span className="bg-foreground text-background flex h-9 w-9 items-center justify-center rounded-full font-mono text-xs font-semibold">
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
