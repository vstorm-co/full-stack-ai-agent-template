{% raw %}"use client";

import "leaflet/dist/leaflet.css";

import type { LatLngBoundsExpression, LatLngExpression } from "leaflet";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import type { MapSpec } from "@/types";

const DEFAULT_COLOR = "#6366f1";

// Default export so it can be loaded via next/dynamic with ssr:false — Leaflet
// touches `window` at import time and must never run during SSR.
export default function MapLeaflet({ spec }: { spec: MapSpec }) {
  const markers = spec.markers;
  const hasCenter = Array.isArray(spec.center) && spec.center.length === 2;

  let center: LatLngExpression | undefined;
  let zoom: number | undefined;
  let bounds: LatLngBoundsExpression | undefined;

  if (hasCenter) {
    center = spec.center as [number, number];
    zoom = spec.zoom ?? 10;
  } else if (markers.length === 1) {
    const m = markers[0]!;
    center = [m.lat, m.lng];
    zoom = spec.zoom ?? 12;
  } else {
    const lats = markers.map((m) => m.lat);
    const lngs = markers.map((m) => m.lng);
    bounds = [
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)],
    ];
  }

  return (
    <MapContainer
      center={center}
      zoom={zoom}
      bounds={bounds}
      boundsOptions={{ padding: [30, 30] }}
      scrollWheelZoom={false}
      className="border-foreground/10 h-[320px] w-full rounded-xl border"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map((m, i) => (
        <CircleMarker
          key={i}
          center={[m.lat, m.lng]}
          radius={8}
          pathOptions={{
            color: m.color ?? DEFAULT_COLOR,
            fillColor: m.color ?? DEFAULT_COLOR,
            fillOpacity: 0.7,
            weight: 2,
          }}
        >
          <Popup>
            <strong>{m.label}</strong>
            {m.description ? <div className="mt-1">{m.description}</div> : null}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
{% endraw %}