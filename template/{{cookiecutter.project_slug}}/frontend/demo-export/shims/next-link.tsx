import type { ReactNode } from "react";

/** Stand-in for `next/link` — a plain anchor. */
export default function Link(props: Record<string, unknown>) {
  const { href, children, ...rest } = props as { href?: string | { pathname?: string }; children?: ReactNode };
  const url = typeof href === "string" ? href : (href?.pathname ?? "#");
  return (
    <a href={url} {...(rest as Record<string, unknown>)}>
      {children as ReactNode}
    </a>
  );
}
