{% raw %}"use client";

import dynamic from "next/dynamic";

import type { MapSpec } from "@/types";

// Leaflet is browser-only — load the renderer with ssr:false so it never
// executes during server rendering.
const MapLeaflet = dynamic(() => import("./map-leaflet"), {
  ssr: false,
  loading: () => <div className="bg-muted h-[320px] w-full animate-pulse rounded-xl" />,
});

/** Parse a `create_map` tool result into a MapSpec, or null if it isn't one. */
export function parseMapResult(result: unknown): MapSpec | null {
  let payload: unknown = result;
  if (typeof result === "string") {
    try {
      payload = JSON.parse(result);
    } catch {
      return null;
    }
  }
  if (payload && typeof payload === "object" && (payload as { kind?: unknown }).kind === "map") {
    return payload as MapSpec;
  }
  return null;
}

/** Render a titled card containing the interactive Leaflet map. */
export function MapMessage({ spec }: { spec: MapSpec }) {
  return (
    <div className="bg-card overflow-hidden rounded-xl border p-3 sm:p-4">
      <p className="text-foreground mb-3 text-sm font-semibold">{spec.title}</p>
      <MapLeaflet spec={spec} />
    </div>
  );
}
{% endraw %}