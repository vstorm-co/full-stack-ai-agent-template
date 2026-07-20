import type { CSSProperties } from "react";

/** Minimal stand-in for `next/image` — renders a plain <img>, dropping Next-only props. */
export default function Image(props: Record<string, unknown>) {
  const { src, alt = "", width, height, fill, className, style } = props as {
    src: string | { src: string };
    alt?: string;
    width?: number;
    height?: number;
    fill?: boolean;
    className?: string;
    style?: CSSProperties;
  };
  const resolved = typeof src === "string" ? src : (src?.src ?? "");
  const s: CSSProperties = fill
    ? { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", ...style }
    : (style ?? {});
  return (
    <img
      src={resolved}
      alt={alt}
      width={fill ? undefined : width}
      height={fill ? undefined : height}
      className={className}
      style={s}
    />
  );
}
