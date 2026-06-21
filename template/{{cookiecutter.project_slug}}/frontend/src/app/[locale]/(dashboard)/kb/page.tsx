{% raw %}"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Database, Lock, Plus, Sparkles, Trash2, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { CreateKBDialog } from "@/components/kb";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState, LoadingState } from "@/components/states";
import { Badge, Button } from "@/components/ui";
import { useKnowledgeBases } from "@/hooks";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import type { KBScope, KnowledgeBase } from "@/types";

const SCOPE_META: Record<KBScope, { label: string; icon: LucideIcon }> = {
  personal: { label: "Personal", icon: Lock },
  org: { label: "Organization", icon: Users },
  app: { label: "App-wide", icon: Sparkles },
};

export default function KBPage() {
  const { kbs, isLoading, fetchKBs, deleteKB } = useKnowledgeBases();
  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    fetchKBs();
  }, [fetchKBs]);

  // Default KB first, then newest first.
  const sorted = [...kbs].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Knowledge"
        title="Knowledge bases"
        description="Group related documents into a base. Open one to upload files, then choose in chat which bases the agent should search."
        actions={
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
            New knowledge base
          </Button>
        }
      />

      {isLoading && kbs.length === 0 ? (
        <LoadingState variant="skeleton-list" rows={4} />
      ) : kbs.length === 0 ? (
        <EmptyState
          icon={Database}
          title="No knowledge bases yet"
          description="Create one to give your assistant access to documents from your collections."
          cta={{ label: "Create knowledge base", onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <div className="grid auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sorted.map((kb) => (
            <KBCard key={kb.id} kb={kb} onDelete={() => deleteKB(kb.id)} />
          ))}
        </div>
      )}

      <CreateKBDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={() => fetchKBs()} />
    </div>
  );
}

function KBCard({ kb, onDelete }: { kb: KnowledgeBase; onDelete: () => void }) {
  const meta = SCOPE_META[kb.scope];

  return (
    <div
      className={cn(
        "group border-border bg-card hover:border-foreground/30 hover:bg-accent relative flex flex-col rounded-xl border transition-colors",
      )}
    >
      {/* Whole-card link; inner interactive controls re-enable pointer events. */}
      <Link
        href={ROUTES.KB_DETAIL(kb.id)}
        className="focus-visible:ring-ring absolute inset-0 z-10 rounded-[inherit] focus-visible:ring-2 focus-visible:outline-none"
        aria-label={`Open ${kb.name}`}
      />

      <div className="pointer-events-none relative z-20 flex h-full flex-col p-5">
        <div className="flex items-start justify-between gap-2">
          <span className="bg-muted text-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
            <meta.icon className="h-4 w-4" />
          </span>

          <div className="flex items-center gap-1.5">
            {kb.is_default && (
              <Badge variant="outline" className="border-border text-muted-foreground font-normal">
                Default
              </Badge>
            )}
            {!kb.is_default && (
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
                className="text-muted-foreground hover:bg-accent hover:text-destructive pointer-events-auto inline-flex h-8 w-8 items-center justify-center rounded-lg opacity-0 transition-colors group-hover:opacity-100 focus-visible:opacity-100"
                aria-label="Delete knowledge base"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-4 flex-1">
          <p className="text-foreground text-base leading-tight font-semibold">{kb.name}</p>
          {kb.description ? (
            <p className="text-muted-foreground mt-1.5 line-clamp-2 text-sm leading-relaxed">
              {kb.description}
            </p>
          ) : (
            <p className="text-muted-foreground mt-1.5 truncate font-mono text-xs">
              {kb.collection_name}
            </p>
          )}
        </div>

        <div className="text-muted-foreground mt-5 flex items-center justify-between gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 truncate">
            <meta.icon className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{meta.label}</span>
          </span>
          <ArrowUpRight className="h-4 w-4 shrink-0" />
        </div>
      </div>
    </div>
  );
}
{% endraw %}
