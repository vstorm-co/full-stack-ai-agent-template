"use client";

import { useEffect, useRef, useState } from "react";

interface AnimatedNumberProps {
  /** The literal text to render (e.g. "5", "<1m", "24/7"). Numbers inside
   *  will be counted up; non-numeric chars rendered as-is. */
  value: string;
  durationMs?: number;
  className?: string;
}

/** Counts up integer parts of a string when scrolled into view.
 *  Non-numeric segments ("<", "/", "m") render unchanged. */
export function AnimatedNumber({ value, durationMs = 900, className }: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const [played, setPlayed] = useState(false);
  const [displayed, setDisplayed] = useState(value);

  useEffect(() => {
    if (!ref.current || played) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting && !played) {
          setPlayed(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [played]);

  useEffect(() => {
    if (!played) return;

    // Find each integer in the string and animate independently
    const segments = value.split(/(\d+)/);
    const targets = segments.map((s) => (/^\d+$/.test(s) ? parseInt(s, 10) : null));

    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      const current = segments
        .map((s, i) => {
          const target = targets[i];
          if (target == null) return s;
          return Math.round(target * eased).toString();
        })
        .join("");
      setDisplayed(current);
      if (t < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [played, value, durationMs]);

  return (
    <span ref={ref} className={className}>
      {displayed}
    </span>
  );
}
