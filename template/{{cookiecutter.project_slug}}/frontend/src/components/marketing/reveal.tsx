{% raw %}"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface RevealProps {
  children: React.ReactNode;
  className?: string;
  /** Delay in ms before reveal animation starts. Useful for staggering siblings. */
  delay?: number;
}

/** Fades in + translates up when element enters viewport.
 *  Critical: SSR-renders as visible. Only after JS hydrates AND the element is
 *  still below the fold do we set it invisible and animate on scroll-into-view.
 *  Anything already on-screen / no-JS / SEO bots / screenshot tools see content. */
export function Reveal({ children, className, delay = 0 }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  // Default true: SSR + above-the-fold render visible.
  const [shown, setShown] = useState(true);

  useEffect(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const inViewportNow = rect.top < window.innerHeight * 0.95;
    if (inViewportNow) return; // already visible — keep it visible

    setShown(false);
    const obs = new IntersectionObserver(
      (entries) => {
        const e = entries[0];
        if (e?.isIntersecting) {
          setShown(true);
          obs.disconnect();
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -8% 0px" },
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ transitionDelay: shown ? `${delay}ms` : "0ms" }}
      className={cn(
        "transition-[opacity,transform] duration-[900ms] ease-[cubic-bezier(0.22,1,0.36,1)] will-change-[opacity,transform]",
        shown ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0",
        className,
      )}
    >
      {children}
    </div>
  );
}
{% endraw %}
