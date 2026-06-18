"use client";

import { cn } from "@/lib/utils";

interface SegmentedControlProps {
  value: string;
  onChange: (value: string) => void;
  options: { label: string; value: string }[];
  className?: string;
}

export function SegmentedControl({ value, onChange, options, className }: SegmentedControlProps) {
  return (
    <div
      className={cn(
        "border-foreground/15 bg-background inline-flex rounded-full border p-0.5",
        className,
      )}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-full px-3 py-1 font-mono text-[11px] tracking-wider uppercase transition-colors",
            value === opt.value
              ? "bg-foreground text-background"
              : "text-foreground/55 hover:text-foreground",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
