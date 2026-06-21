/** Inline JSON-LD `<script>` for schema.org structured data.
 *  Use under server components only — Next.js will inline this into the SSR HTML. */

interface JsonLdProps {
  data: Record<string, unknown> | Record<string, unknown>[];
}

/**
 * Escape `<` and `>` so a malicious string in `data` can't terminate the
 * surrounding `<script>` tag (e.g. `"</script><script>alert(1)</script>"`).
 * `<` and `>` are interpreted as `<`/`>` by JSON parsers but are
 * inert in HTML.
 */
function safeStringify(data: unknown): string {
  return JSON.stringify(data).replace(/</g, "\\u003c").replace(/>/g, "\\u003e");
}

export function JsonLd({ data }: JsonLdProps) {
  return (
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: safeStringify(data) }} />
  );
}
