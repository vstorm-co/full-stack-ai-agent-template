{% raw %}"use client";

import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { BrandIcon } from "./brand-icon";

const SOURCES = [
  { brand: "gdrive" as const, label: "Google Drive" },
  { brand: "slack" as const, label: "Slack" },
  { brand: "notion" as const, label: "Notion" },
  { brand: "github" as const, label: "GitHub" },
  { brand: "dropbox" as const, label: "Dropbox" },
];

interface Endpoints {
  /** Path strings from each source card right edge → KB left edge. */
  srcToKb: string[];
  /** Path string from KB right edge → assistant card left edge. */
  kbToAssistant: string | null;
  /** Path string from assistant top edge → user question bubble bottom. */
  assistantToQuestion: string | null;
  size: { w: number; h: number };
}

const EMPTY: Endpoints = {
  srcToKb: [],
  kbToAssistant: null,
  assistantToQuestion: null,
  size: { w: 0, h: 0 },
};

export function DataFlowDiagram() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sourceRefs = useRef<(HTMLDivElement | null)[]>([]);
  const kbRef = useRef<HTMLDivElement>(null);
  const assistantRef = useRef<HTMLDivElement>(null);
  const questionRef = useRef<HTMLDivElement>(null);
  const [paths, setPaths] = useState<Endpoints>(EMPTY);

  useEffect(() => {
    const recalc = () => {
      const c = containerRef.current?.getBoundingClientRect();
      const kb = kbRef.current?.getBoundingClientRect();
      const ai = assistantRef.current?.getBoundingClientRect();
      const q = questionRef.current?.getBoundingClientRect();
      if (!c || !kb || !ai || !q) return;

      const rel = (
        rect: DOMRect,
        side: "left" | "right" | "top" | "bottom" | "centerX" | "centerY",
      ) => {
        const x =
          side === "left" ? rect.left : side === "right" ? rect.right : rect.left + rect.width / 2;
        const y =
          side === "top" ? rect.top : side === "bottom" ? rect.bottom : rect.top + rect.height / 2;
        return { x: x - c.left, y: y - c.top };
      };

      const kbLeftPort = rel(kb, "left");
      kbLeftPort.x += 6; // tuck slightly inside the ring border
      const kbRightPort = rel(kb, "right");
      kbRightPort.x -= 6;

      const srcPaths = sourceRefs.current
        .map((el) => {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          const start = { x: r.right - c.left, y: r.top + r.height / 2 - c.top };
          const end = kbLeftPort;
          // Smooth S-curve: control points pushed horizontally
          const c1x = start.x + 70;
          const c2x = end.x - 90;
          return `M ${start.x} ${start.y} C ${c1x} ${start.y}, ${c2x} ${end.y}, ${end.x} ${end.y}`;
        })
        .filter((p): p is string => p !== null);

      const aiLeft = rel(ai, "left");
      aiLeft.x -= 4;
      const kbAi = `M ${kbRightPort.x} ${kbRightPort.y} C ${kbRightPort.x + 80} ${kbRightPort.y}, ${aiLeft.x - 60} ${aiLeft.y}, ${aiLeft.x} ${aiLeft.y}`;

      const aiTop = rel(ai, "top");
      const qBottom = rel(q, "bottom");
      const aiToQ = `M ${aiTop.x} ${aiTop.y} C ${aiTop.x} ${aiTop.y - 40}, ${qBottom.x} ${qBottom.y + 40}, ${qBottom.x} ${qBottom.y}`;

      setPaths({
        srcToKb: srcPaths,
        kbToAssistant: kbAi,
        assistantToQuestion: aiToQ,
        size: { w: c.width, h: c.height },
      });
    };

    recalc();
    const ro = new ResizeObserver(recalc);
    if (containerRef.current) ro.observe(containerRef.current);
    window.addEventListener("resize", recalc);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", recalc);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="border-foreground/15 bg-card/60 relative overflow-hidden rounded-3xl border p-8 backdrop-blur-sm md:p-14"
    >
      <div
        aria-hidden
        className="glow-breathe absolute top-1/2 left-1/2 -z-10 h-72 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full blur-3xl"
        style={{ background: "oklch(from var(--color-brand) l c h / 0.18)" }}
      />

      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        width={paths.size.w || undefined}
        height={paths.size.h || undefined}
        aria-hidden
      >
        <defs>
          <linearGradient
            id="line-gradient"
            gradientUnits="userSpaceOnUse"
            x1="0"
            y1="0"
            x2="100%"
            y2="0"
          >
            <stop offset="0%" stopColor="oklch(from var(--color-foreground) l c h / 0.10)" />
            <stop offset="50%" stopColor="oklch(from var(--color-foreground) l c h / 0.30)" />
            <stop offset="100%" stopColor="oklch(from var(--color-foreground) l c h / 0.10)" />
          </linearGradient>
        </defs>

        {paths.srcToKb.map((d, i) => (
          <g key={`src-${i}`}>
            <path d={d} stroke="url(#line-gradient)" strokeWidth="1.5" fill="none" />
            {/* 2 comets per path, staggered, for a continuous river feel */}
            {[0, 1].map((cometIdx) => (
              <circle key={cometIdx} r="3.5" fill="var(--color-brand)" className="comet">
                <animateMotion
                  dur={`${2.6 + i * 0.2}s`}
                  repeatCount="indefinite"
                  path={d}
                  begin={`${cometIdx * -1.3 + i * -0.2}s`}
                />
              </circle>
            ))}
          </g>
        ))}

        {paths.kbToAssistant !== null && <KbToAssistant d={paths.kbToAssistant} />}

        {paths.assistantToQuestion && (
          <g>
            <path
              d={paths.assistantToQuestion}
              stroke="url(#line-gradient)"
              strokeWidth="1.5"
              fill="none"
              strokeDasharray="3 6"
              opacity="0.7"
            />
          </g>
        )}
      </svg>

      <div className="relative grid grid-cols-3 items-center gap-6 md:gap-12">
        <div className="space-y-2.5">
          <p className="eyebrow text-foreground/55 mb-4">Sources</p>
          {SOURCES.map((source, i) => (
            <div
              key={source.label}
              ref={(el) => {
                sourceRefs.current[i] = el;
              }}
              className="border-foreground/15 bg-background lift flex items-center gap-3 rounded-xl border px-4 py-3 shadow-sm"
            >
              <span className="bg-foreground/8 text-foreground flex h-8 w-8 items-center justify-center rounded-lg">
                <BrandIcon name={source.brand} className="h-4 w-4" />
              </span>
              <span className="text-foreground text-sm font-medium">{source.label}</span>
            </div>
          ))}
        </div>

        <div className="flex justify-center">
          <div
            ref={kbRef}
            className="bg-card relative flex h-44 w-44 items-center justify-center rounded-full md:h-56 md:w-56"
          >
            <div
              aria-hidden
              className="ring-rotate border-brand/55 absolute inset-0 rounded-full border-2 border-dashed"
            />
            <div
              aria-hidden
              className="ring-rotate-rev border-brand/30 absolute inset-3 rounded-full border border-dashed"
            />
            <div className="bg-card border-foreground/10 absolute inset-6 rounded-full border shadow-inner" />

            <div className="relative z-10 text-center">
              <p className="eyebrow text-foreground/55 mb-1.5">Knowledge base</p>
              <AnimatedCount target={1240000} suffix="" />
              <p className="text-foreground/55 mt-0.5 font-mono text-[10px] tracking-wider uppercase">
                vectors indexed
              </p>
              <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-[color-mix(in_oklab,var(--color-brand)_18%,transparent)] px-2 py-0.5">
                <span className="bg-brand h-1.5 w-1.5 animate-pulse rounded-full" />
                <span className="text-foreground font-mono text-[10px] font-medium">syncing</span>
              </div>
            </div>

            {[
              { x: "8%", y: "18%", delay: "0s" },
              { x: "85%", y: "22%", delay: "-0.6s" },
              { x: "12%", y: "78%", delay: "-1.2s" },
              { x: "82%", y: "72%", delay: "-1.8s" },
              { x: "50%", y: "5%", delay: "-2.4s" },
              { x: "50%", y: "92%", delay: "-3.0s" },
            ].map((d, i) => (
              <span
                key={i}
                className="bg-brand pulse-dot absolute h-1.5 w-1.5 rounded-full"
                style={{ left: d.x, top: d.y, animationDelay: d.delay }}
              />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div
            ref={questionRef}
            className="border-foreground/15 bg-background ml-auto max-w-[90%] rounded-2xl rounded-tr-sm border px-4 py-3 shadow-sm"
          >
            <p className="text-foreground text-sm leading-snug">
              What did the team ship last quarter?
            </p>
          </div>

          <p className="eyebrow text-foreground/55">Assistant</p>

          <div
            ref={assistantRef}
            className="border-foreground/15 bg-background relative overflow-hidden rounded-xl border p-4 shadow-md"
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-x-0 bottom-0 h-12"
              style={{
                background:
                  "linear-gradient(to top, oklch(from var(--color-brand) l c h / 0.08), transparent)",
              }}
            />
            <div className="relative">
              <div className="text-foreground/55 mb-2 flex items-center gap-1.5">
                <Sparkles className="text-brand h-3.5 w-3.5" />
                <span className="font-mono text-[10px] tracking-wider uppercase">Answer</span>
              </div>
              <p className="text-foreground text-sm leading-relaxed">
                Three major features: real-time sync, audit logs, SSO. Cited from 4 sources.
              </p>
              <div className="border-foreground/10 mt-3 flex flex-wrap gap-1.5 border-t pt-3">
                <Cite>onboarding-q1.pdf</Cite>
                <Cite>release-notes.md</Cite>
                <Cite>+2 more</Cite>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function KbToAssistant({ d }: { d: string }) {
  return (
    <g>
      <path d={d} stroke="url(#line-gradient)" strokeWidth="2" fill="none" />
      {[0, 1, 2].map((i) => (
        <circle key={i} r="4" fill="var(--color-brand)" className="comet">
          <animateMotion dur="2.4s" repeatCount="indefinite" path={d} begin={`${i * -0.8}s`} />
        </circle>
      ))}
    </g>
  );
}

function Cite({ children }: { children: React.ReactNode }) {
  return (
    <span className="border-brand/40 bg-brand/10 text-foreground/75 inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px]">
      {children}
    </span>
  );
}

/** Counts up to target on first scroll-into-view. Formats compactly (1.2M). */
function AnimatedCount({ target, suffix }: { target: number; suffix?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const [played, setPlayed] = useState(false);
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!ref.current || played) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (e?.isIntersecting && !played) {
          setPlayed(true);
          obs.disconnect();
        }
      },
      { threshold: 0.5 },
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, [played]);

  useEffect(() => {
    if (!played) return;
    const start = performance.now();
    const dur = 1200;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(target * eased));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [played, target]);

  const formatted =
    value >= 1_000_000
      ? `${(value / 1_000_000).toFixed(1)}M`
      : value >= 1_000
        ? `${(value / 1_000).toFixed(0)}k`
        : value.toString();

  return (
    <p ref={ref} className="text-foreground font-mono text-2xl font-bold tabular-nums md:text-3xl">
      {formatted}
      {suffix}
    </p>
  );
}
{% endraw %}
