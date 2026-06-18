import { cn } from "@/lib/utils";

type Variant = "skeleton-list" | "skeleton-card" | "skeleton-cards" | "dot-pulse" | "stats";

interface LoadingStateProps {
  variant?: Variant;
  /** Number of rows for skeleton-list, or cards for skeleton-cards. */
  rows?: number;
  className?: string;
  /** Optional label rendered with dot-pulse. */
  label?: string;
}

export function LoadingState({
  variant = "dot-pulse",
  rows = 4,
  className,
  label,
}: LoadingStateProps) {
  if (variant === "dot-pulse") {
    return (
      <div className={cn("flex items-center justify-center gap-3 py-8", className)}>
        <DotPulse />
        {label && <span className="text-foreground/55 text-sm">{label}</span>}
      </div>
    );
  }

  if (variant === "skeleton-list") {
    return (
      <div className={cn("space-y-3", className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="border-border bg-card flex items-center gap-3 rounded-xl border p-4"
          >
            <div className="bg-foreground/10 h-9 w-9 animate-pulse rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="bg-foreground/10 h-3 w-1/3 animate-pulse rounded-full" />
              <div className="bg-foreground/8 h-3 w-2/3 animate-pulse rounded-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "skeleton-card") {
    return (
      <div
        className={cn(
          "border-border bg-card animate-pulse space-y-3 rounded-2xl border p-6",
          className,
        )}
      >
        <div className="bg-foreground/10 h-3 w-1/4 rounded-full" />
        <div className="bg-foreground/15 h-8 w-1/2 rounded-md" />
        <div className="bg-foreground/8 h-2.5 w-full rounded-full" />
        <div className="bg-foreground/8 h-2.5 w-4/5 rounded-full" />
      </div>
    );
  }

  if (variant === "skeleton-cards") {
    return (
      <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <LoadingState key={i} variant="skeleton-card" />
        ))}
      </div>
    );
  }

  if (variant === "stats") {
    return (
      <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="border-border bg-card animate-pulse space-y-3 rounded-2xl border p-5"
          >
            <div className="bg-foreground/10 h-3 w-2/5 rounded-full" />
            <div className="bg-foreground/15 h-8 w-1/2 rounded-md" />
            <div className="bg-foreground/8 h-10 w-full rounded-md" />
          </div>
        ))}
      </div>
    );
  }

  return null;
}

function DotPulse() {
  return (
    <span aria-hidden className="inline-flex items-center gap-1.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="bg-foreground/60 h-1.5 w-1.5 rounded-full"
          style={{
            animation: "dot-pulse 1.2s ease-in-out infinite",
            animationDelay: `${i * 160}ms`,
          }}
        />
      ))}
      <style>{`
        @keyframes dot-pulse {
          0%, 80%, 100% { opacity: 0.25; transform: scale(0.85); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </span>
  );
}
