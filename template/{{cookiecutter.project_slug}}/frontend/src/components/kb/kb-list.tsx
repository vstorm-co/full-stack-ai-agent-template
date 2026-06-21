{% raw %}"use client";

import Link from "next/link";
import { ArrowUpRight, Lock, Sparkles, Trash2, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import type { KBScope, KnowledgeBase } from "@/types";

interface KBListProps {
  kbs: KnowledgeBase[];
  onDelete: (id: string) => void;
  canDelete?: boolean;
}

const SCOPE_META: Record<KBScope, { label: string; icon: LucideIcon }> = {
  personal: { label: "Personal", icon: Lock },
  org: { label: "Organization", icon: Users },
  app: { label: "App-wide", icon: Sparkles },
};

/**
 * Bento-style grid of knowledge bases. The default KB (if present and listed
 * first by ordering below) gets a `col-span-2` featured treatment with a
 * brand-tinted border + glow; the rest are equal-size cards. Scope is shown as
 * an icon chip on each card instead of being grouped into sections.
 */
export function KBList({ kbs, onDelete, canDelete = true }: KBListProps) {
  if (!kbs.length) return null;

  const sorted = [...kbs].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {sorted.map((kb, idx) => (
        <KBCard
          key={kb.id}
          kb={kb}
          canDelete={canDelete}
          onDelete={() => onDelete(kb.id)}
          featured={idx === 0 && kb.is_default}
        />
      ))}
    </div>
  );
}

interface KBCardProps {
  kb: KnowledgeBase;
  canDelete: boolean;
  onDelete: () => void;
  featured: boolean;
}

function KBCard({ kb, canDelete, onDelete, featured }: KBCardProps) {
  const meta = SCOPE_META[kb.scope];

  return (
    <div
      className={cn(
        "group relative isolate overflow-hidden rounded-2xl border transition-all hover:-translate-y-0.5",
        featured
          ? "border-brand/40 bg-foreground/[0.02] lg:col-span-2"
          : "border-foreground/10 bg-card hover:border-foreground/25",
      )}
    >
      {featured && (
        <>
          <div
            aria-hidden
            className="pointer-events-none absolute -top-16 -right-16 -z-10 h-48 w-48 rounded-full blur-3xl"
            style={{
              background:
                "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.3), transparent 65%)",
            }}
          />
          <div
            aria-hidden
            className="bg-dots pointer-events-none absolute inset-0 -z-10 opacity-50"
          />
        </>
      )}

      {/* Whole-card link (absolute, full coverage). Inner content uses
        pointer-events: none so clicks fall through; only the delete button
        re-enables them. */}
      <Link
        href={ROUTES.KB_DETAIL(kb.id)}
        className="focus-visible:ring-foreground/20 absolute inset-0 z-10 rounded-[inherit] focus-visible:ring-2 focus-visible:outline-none"
        aria-label={`Open ${kb.name}`}
      />

      <div className="pointer-events-none relative z-20 flex h-full flex-col p-5 sm:p-6">
        <div className="flex items-start justify-between gap-2">
          <span
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
              featured
                ? "bg-brand text-brand-foreground"
                : "bg-foreground/8 text-foreground/65 group-hover:bg-foreground/12",
            )}
            style={
              featured
                ? { boxShadow: "0 0 18px oklch(from var(--color-brand) l c h / 0.45)" }
                : undefined
            }
          >
            <meta.icon className="h-4 w-4" />
          </span>

          <div className="pointer-events-none relative flex items-center gap-1">
            {kb.is_default && (
              <span className="bg-brand/15 text-foreground inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase">
                <Sparkles className="h-2.5 w-2.5" />
                Default
              </span>
            )}
            {canDelete && !kb.is_default && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (
                    confirm(
                      `Delete "${kb.name}"? This will remove the knowledge base and all its documents.`,
                    )
                  ) {
                    onDelete();
                  }
                }}
                className="text-foreground/45 hover:bg-destructive/10 hover:text-destructive pointer-events-auto inline-flex h-8 w-8 items-center justify-center rounded-lg opacity-0 transition-all group-hover:opacity-100 focus-visible:opacity-100"
                aria-label="Delete knowledge base"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-6 flex-1">
          <p
            className={cn(
              "text-foreground leading-tight font-semibold",
              featured ? "text-xl sm:text-2xl" : "text-base",
            )}
          >
            {kb.name}
          </p>
          {kb.description ? (
            <p
              className={cn(
                "text-foreground/65 mt-2 leading-relaxed",
                featured ? "max-w-md text-sm" : "line-clamp-2 text-xs",
              )}
            >
              {kb.description}
            </p>
          ) : (
            <p className="text-foreground/35 mt-2 truncate font-mono text-[10px] tracking-wider uppercase">
              {kb.collection_name}
            </p>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between gap-2 font-mono text-[10px] tracking-wider uppercase">
          <span className="text-foreground/45 inline-flex items-center gap-1.5 truncate">
            <meta.icon className="h-3 w-3 shrink-0" />
            <span className="truncate">{meta.label}</span>
            {kb.description && (
              <>
                <span className="text-foreground/20">·</span>
                <span className="truncate">{kb.collection_name}</span>
              </>
            )}
          </span>
          <ArrowUpRight className="text-foreground/30 group-hover:text-foreground/80 h-4 w-4 shrink-0 transition-colors group-hover:rotate-45" />
        </div>
      </div>
    </div>
  );
}
{% endraw %}
