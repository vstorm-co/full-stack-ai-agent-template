{% raw %}import Link from "next/link";
import { Play } from "lucide-react";

interface DemoListItem {
  id: string;
  title: string | null;
  message_count: number;
  preview: string | null;
  created_at: string;
}

async function fetchDemos(): Promise<DemoListItem[]> {
  const baseUrl = process.env.BACKEND_URL || "http://localhost:{% endraw %}{{ cookiecutter.backend_port }}{% raw %}";
  try {
    const res = await fetch(`${baseUrl}/api/v1/demos`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data?.items) ? data.items : [];
  } catch {
    return [];
  }
}

function WaveTrace({ seed, count }: { seed: string; count: number }) {
  const n = Math.min(count, 22);
  const stripped = seed.replace(/-/g, "") || "abcdef";
  return (
    <div className="flex h-7 items-end gap-[2px]">
      {Array.from({ length: n }, (_, i) => {
        const c = stripped.charCodeAt(i % stripped.length) || 65;
        const h = 20 + ((c * 17 + i * 31) % 65);
        const barStyle = {
          height: `${h}%`,
          width: "3px",
          borderRadius: "9999px",
          background: "var(--color-brand)",
          opacity: i % 2 === 0 ? 0.72 : 0.28,
        };
        return <div key={i} style={barStyle} />;
      })}
    </div>
  );
}

const glowRight = {
  background: "radial-gradient(circle, oklch(65% 0.2 250 / 0.11) 0%, transparent 70%)",
};
const glowLeft = {
  background: "radial-gradient(circle, oklch(65% 0.2 250 / 0.06) 0%, transparent 70%)",
};
const cardHoverGradient = {
  background: "radial-gradient(ellipse at top left, oklch(65% 0.2 250 / 0.07) 0%, transparent 55%)",
};

export default async function DemoGalleryPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const demos = await fetchDemos();

  return (
    <div className="theme-dark bg-background min-h-screen">
      {/* Hero */}
      <div className="relative overflow-hidden px-4 pb-20 pt-24 sm:pt-32">
        {/* Ambient glow blobs */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-40 -top-40 h-[560px] w-[560px] rounded-full"
          style={glowRight}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -left-24 top-1/2 h-[380px] w-[380px] rounded-full"
          style={glowLeft}
        />

        <div className="relative mx-auto max-w-5xl">
          {/* Live indicator */}
          <div className="mb-6 inline-flex items-center gap-2 font-mono text-xs font-medium uppercase tracking-[0.18em] text-brand">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand" />
            </span>
            Live sessions · {demos.length} available
          </div>

          <h1 className="mb-6 max-w-3xl font-display text-5xl font-bold leading-[1.06] tracking-tight text-foreground sm:text-6xl">
            Watch the AI
            <br />
            work in real time.
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-muted-foreground">
            Every tool call, every decision — replayed frame by frame,
            exactly as it happened.
          </p>
        </div>
      </div>

      {/* Cards */}
      <div className="mx-auto max-w-5xl px-4 pb-24">
        {demos.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border py-20 text-center">
            <p className="text-sm text-muted-foreground">No demos available yet. Check back soon.</p>
          </div>
        ) : (
          <div className="grid gap-5 sm:grid-cols-2">
            {demos.map((demo) => (
              <Link
                key={demo.id}
                href={`/${locale}/demo/${demo.id}`}
                className="group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:border-brand/30"
              >
                {/* Hover gradient reveal */}
                <div
                  className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                  style={cardHoverGradient}
                />

                {/* Wave trace + turn count */}
                <div className="relative mb-5 flex items-end justify-between">
                  <WaveTrace seed={demo.id} count={demo.message_count} />
                  <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                    {demo.message_count} turns
                  </span>
                </div>

                {/* Title */}
                <h2 className="relative mb-3 font-display text-xl font-bold leading-tight text-foreground">
                  {demo.title || "Agent session"}
                </h2>

                {/* Preview */}
                {demo.preview && (
                  <p className="relative line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                    &ldquo;{demo.preview}&rdquo;
                  </p>
                )}

                {/* CTA */}
                <div className="relative mt-auto flex items-center justify-end pt-6">
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-brand transition-transform duration-200 group-hover:translate-x-0.5">
                    Watch replay
                    <Play className="h-3.5 w-3.5 fill-current" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
{% endraw %}
