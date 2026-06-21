{% raw %}"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/states";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-0 flex-1 items-center justify-center py-10">
      <ErrorState
        className="w-full max-w-md"
        title="This section failed to load"
        description={
          error.digest
            ? `An unexpected error occurred. Error ID: ${error.digest}`
            : "An unexpected error occurred while loading this view. Please try again."
        }
        cta={{ label: "Try again", onClick: () => reset() }}
      />
    </div>
  );
}
{% endraw %}
