import Link from "next/link";
import { Sparkles } from "lucide-react";

import { APP_NAME, ROUTES } from "@/lib/constants";

const HIGHLIGHTS = [
  "Streaming chat with tool calls",
  "Knowledge base over your docs",
  "Stripe billing & teams in a click",
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background text-foreground min-h-screen lg:grid lg:grid-cols-[1.1fr_minmax(0,560px)]">
      {/* LEFT — form panel (always light, regardless of system theme) */}
      <main id="main" className="theme-light bg-background text-foreground relative flex flex-col">
        <header className="flex h-16 items-center px-6 sm:px-10">
          <Link
            href={ROUTES.HOME}
            className="font-display text-foreground inline-flex items-center gap-2 text-base font-bold tracking-tight"
          >
            <span aria-hidden className="bg-brand inline-block h-2.5 w-2.5 rounded-full" />
            {APP_NAME}
          </Link>
        </header>

        <div className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
          <div className="w-full max-w-md">{children}</div>
        </div>

        <footer className="text-foreground/50 px-6 py-6 font-mono text-[11px] tracking-wider uppercase sm:px-10">
          © {new Date().getFullYear()} {APP_NAME}
        </footer>
      </main>

      {/* RIGHT — brand island (floating rounded card, hidden on mobile) */}
      <aside className="hidden p-5 lg:block lg:p-6">
        <div className="theme-dark bg-background text-foreground border-foreground/10 relative flex h-full flex-col justify-between overflow-hidden rounded-3xl border p-10 shadow-2xl lg:p-12">
          {/* Background visuals */}
          <div aria-hidden className="pointer-events-none absolute inset-0">
            <div className="bg-grid absolute inset-0 opacity-[0.55]" />
            <div className="bg-brand/[0.28] absolute -top-32 -right-20 h-[460px] w-[460px] rounded-full blur-[120px]" />
            <div className="bg-brand/[0.12] absolute -bottom-20 -left-10 h-[320px] w-[420px] rounded-full blur-[140px]" />
          </div>

          {/* TOP — eyebrow chip */}
          <div className="relative z-10">
            <span className="eyebrow-badge inline-flex items-center gap-2">
              <Sparkles className="h-3 w-3" aria-hidden />
              An AI assistant that knows your team&apos;s work
            </span>
          </div>

          {/* MIDDLE — headline + highlights */}
          <div className="relative z-10 max-w-[28rem]">
            <h2 className="text-display-lg text-foreground [&_em]:font-accent mb-6 leading-[1.05] [&_em]:font-normal [&_em]:italic">
              Ship the AI feature <em>your team</em> actually wants.
            </h2>
            <p className="text-foreground/65 max-w-md text-base leading-relaxed">
              Auth, billing, vector search, agents — already wired. You ship the product, not the
              plumbing.
            </p>

            <ul className="mt-10 space-y-3">
              {HIGHLIGHTS.map((line) => (
                <li key={line} className="text-foreground/85 flex items-center gap-3 text-sm">
                  <span aria-hidden className="bg-brand h-1.5 w-1.5 shrink-0 rounded-full" />
                  {line}
                </li>
              ))}
            </ul>
          </div>

          {/* BOTTOM — glass testimonial card */}
          <figure className="border-foreground/10 bg-card/40 relative z-10 max-w-md rounded-2xl border p-5 backdrop-blur-xl">
            <blockquote className="text-foreground/90 text-sm leading-relaxed">
              &ldquo;Replaced four SaaS tools and shipped our first AI feature in two weeks.&rdquo;
            </blockquote>
            <figcaption className="mt-4 flex items-center gap-3">
              <span
                className="bg-brand text-brand-foreground flex h-9 w-9 items-center justify-center rounded-full font-mono text-xs font-semibold"
                style={{ boxShadow: "0 0 16px var(--color-brand)" }}
              >
                EP
              </span>
              <div>
                <p className="text-foreground text-sm font-semibold">Eli Park</p>
                <p className="text-foreground/55 text-xs">Founder · Vellum Labs</p>
              </div>
            </figcaption>
          </figure>
        </div>
      </aside>
    </div>
  );
}
