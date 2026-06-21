{% raw %}"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { ExternalLink } from "lucide-react";

import { CopyButton } from "./copy-button";
import type { MarkdownContentProps } from "./markdown-content";

/** Parse `language-xyz` from a `<code>` className that rehype-highlight emits. */
function languageLabel(className: string | undefined): string | null {
  if (!className) return null;
  const match = /(?:^|\s)language-([a-z0-9+\-]+)/i.exec(className);
  return match && match[1] ? match[1].toLowerCase() : null;
}

/**
 * Pre-process markdown to turn bare citation markers [N] into markdown links
 * with a special `#cite-N` href. The `a` component override below detects this
 * and renders an interactive CitationBadge instead of a regular link.
 *
 * Only replaces [N] that is NOT followed by `(` (already a link) or `:` (link
 * reference definition). Code spans/blocks are left as-is because the regex
 * doesn't enter them — in practice agent responses never cite inside code.
 */
function preprocessCitations(content: string): string {
  return content.replace(/\[(\d{1,3})\](?![\(:])/g, (_, n) => `[[${n}]](#cite-${n})`);
}

export function MarkdownContent({ content, onCiteClick }: MarkdownContentProps) {
  const processed = onCiteClick ? preprocessCitations(content) : content;
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        pre({ children, ...props }) {
          const codeElement = children as React.ReactElement<{
            children?: string;
            className?: string;
          }>;
          const codeContent =
            typeof codeElement?.props?.children === "string" ? codeElement.props.children : "";
          const lang = languageLabel(codeElement?.props?.className);

          return (
            <div className="group border-border bg-muted my-3 overflow-hidden rounded-xl border">
              {(lang || codeContent) && (
                <div className="border-foreground/8 text-foreground/55 flex items-center justify-between border-b px-3 py-1.5 font-mono text-[10px] tracking-wider uppercase">
                  <span>{lang ?? "text"}</span>
                  {codeContent && (
                    <CopyButton text={codeContent} className="opacity-100 transition-opacity" />
                  )}
                </div>
              )}
              <pre className="overflow-x-auto p-3.5 text-[12.5px] leading-relaxed" {...props}>
                {children}
              </pre>
            </div>
          );
        },
        code({ className, children, ...props }) {
          const isInline = !className;
          if (isInline) {
            return (
              <code
                className="bg-foreground/8 text-foreground rounded px-1.5 py-0.5 font-mono text-[0.85em]"
                {...props}
              >
                {children}
              </code>
            );
          }
          return (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        a({ href, children, ...props }) {
          if (href?.startsWith("#cite-") && onCiteClick) {
            const n = parseInt(href.slice(6), 10);
            if (!Number.isNaN(n)) {
              return (
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    onCiteClick(n);
                  }}
                  className="bg-foreground/10 text-foreground/70 hover:bg-foreground/20 mx-0.5 inline-flex h-[1.1em] cursor-pointer items-center rounded px-1 align-middle font-mono text-[0.72em] font-semibold tabular-nums transition-colors"
                  title={`Source [${n}]`}
                >
                  {n}
                </button>
              );
            }
          }
          const isExternal = !!href && /^https?:\/\//i.test(href);
          return (
            <a
              href={href}
              target={isExternal ? "_blank" : undefined}
              rel={isExternal ? "noopener noreferrer" : undefined}
              className="text-foreground hover:text-brand-hover decoration-brand hover:decoration-brand inline-flex items-baseline gap-0.5 font-medium underline decoration-2 underline-offset-[3px] transition-colors"
              {...props}
            >
              {children}
              {isExternal && (
                <ExternalLink className="text-foreground/60 inline h-[0.8em] w-[0.8em] shrink-0 -translate-y-[1px]" />
              )}
            </a>
          );
        },
        p({ children, ...props }) {
          return (
            <p className="mb-3 leading-relaxed last:mb-0" {...props}>
              {children}
            </p>
          );
        },
        ul({ children, ...props }) {
          return (
            <ul
              className="marker:text-foreground/40 mb-3 ml-5 list-disc space-y-1 last:mb-0"
              {...props}
            >
              {children}
            </ul>
          );
        },
        ol({ children, ...props }) {
          return (
            <ol
              className="marker:text-foreground/40 mb-3 ml-5 list-decimal space-y-1 last:mb-0"
              {...props}
            >
              {children}
            </ol>
          );
        },
        li({ children, ...props }) {
          return (
            <li className="leading-relaxed" {...props}>
              {children}
            </li>
          );
        },
        h1({ children, ...props }) {
          return (
            <h1
              className="font-display mt-4 mb-2 text-xl font-bold tracking-tight first:mt-0"
              {...props}
            >
              {children}
            </h1>
          );
        },
        h2({ children, ...props }) {
          return (
            <h2
              className="font-display mt-4 mb-2 text-lg font-semibold tracking-tight first:mt-0"
              {...props}
            >
              {children}
            </h2>
          );
        },
        h3({ children, ...props }) {
          return (
            <h3 className="font-display mt-3 mb-2 text-base font-semibold first:mt-0" {...props}>
              {children}
            </h3>
          );
        },
        blockquote({ children, ...props }) {
          return (
            <blockquote
              className="border-brand/40 text-foreground/75 my-3 border-l-2 pl-4 italic"
              {...props}
            >
              {children}
            </blockquote>
          );
        },
        table({ children, ...props }) {
          return (
            <div className="border-foreground/10 my-3 overflow-x-auto rounded-lg border">
              <table className="min-w-full text-sm" {...props}>
                {children}
              </table>
            </div>
          );
        },
        thead({ children, ...props }) {
          return (
            <thead className="bg-foreground/[0.04]" {...props}>
              {children}
            </thead>
          );
        },
        th({ children, ...props }) {
          return (
            <th
              className="border-foreground/10 border-b px-3 py-2 text-left font-mono text-[11px] font-semibold tracking-wider uppercase"
              {...props}
            >
              {children}
            </th>
          );
        },
        td({ children, ...props }) {
          return (
            <td className="border-foreground/8 border-b px-3 py-2 last:border-0" {...props}>
              {children}
            </td>
          );
        },
        hr({ ...props }) {
          return <hr className="border-foreground/10 my-4" {...props} />;
        },
      }}
    >
      {processed}
    </ReactMarkdown>
  );
}
{% endraw %}
