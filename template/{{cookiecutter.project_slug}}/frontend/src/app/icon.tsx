{% raw %}import { ImageResponse } from "next/og";

/** Dynamic favicon — black square with a lime brand dot. Renders at 32×32. */
export const size = { width: 32, height: 32 };
export const contentType = "image/png";
export const dynamic = "force-static";

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0E0E0C",
        borderRadius: "6px",
      }}
    >
      <div
        style={{
          width: 14,
          height: 14,
          borderRadius: "9999px",
          background: "#C5F94A",
        }}
      />
    </div>,
    { ...size },
  );
}
{% endraw %}
