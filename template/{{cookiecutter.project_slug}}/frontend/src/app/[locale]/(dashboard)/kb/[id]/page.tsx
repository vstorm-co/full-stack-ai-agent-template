{% raw %}"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileText,
  Loader2,
  Lock,
  Plug,
  Plus,
  RefreshCw,
  RotateCw,
  Sparkles,
  Trash2,
  Upload,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { ROUTES } from "@/lib/constants";
import { PageHeader } from "@/components/dashboard/page-header";
import { Badge, Button, DataTable, Progress, Skeleton, type Column } from "@/components/ui";
import { EmptyState } from "@/components/states";
import { SyncSourceWizard } from "@/components/rag/sync-source-wizard";
import { SyncSourceLogs } from "@/components/rag/sync-source-logs";
import { BrandIcon } from "@/components/marketing/brand-icon";
import { FileViewer } from "@/components/kb/file-viewer";
import { useKBDetail } from "@/hooks";
import { cn, formatBytes, formatDateTime } from "@/lib/utils";
import { downloadKBDocument } from "@/lib/rag-api";
import type { SyncSourceRead } from "@/lib/rag-api";
import type { KBDocument, KBScope } from "@/types";

const SCOPE_META: Record<KBScope, { label: string; icon: LucideIcon }> = {
  personal: { label: "Personal", icon: Lock },
  org: { label: "Organization", icon: Users },
  app: { label: "App-wide", icon: Sparkles },
};

const CONNECTOR_BRAND: Record<string, "gdrive" | "github" | "notion" | "slack" | "dropbox" | "s3"> = {
  google_drive: "gdrive",
  gdrive: "gdrive",
  drive: "gdrive",
  github: "github",
  notion: "notion",
  slack: "slack",
  dropbox: "dropbox",
  s3: "s3",
  aws: "s3",
};

// Sync sources have no server-side pagination (the backend returns every source
// for the KB's collection). They're typically few, so collapse past this count
// behind a client-side "show all" toggle.
const SYNC_SOURCES_VISIBLE = 10;

// Ingestion polling backoff: fast at first, then ease off to spare the API on
// long ingests. Resets to POLL_MIN_MS whenever a document changes state.
const POLL_MIN_MS = 2000;
const POLL_MAX_MS = 30000;
const POLL_FACTOR = 1.5;

interface KBDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function KBDetailPage({ params }: KBDetailPageProps) {
  const { id } = use(params);
  const {
    kb,
    documents,
    documentsTotal,
    hasMoreDocuments,
    syncSources,
    orgIntegrations,
    connectors,
    isLoading,
    isLoadingMoreDocs,
    isUploading,
    uploadProgress,
    error,
    refresh,
    loadMoreDocuments,
    uploadDocument,
    deleteDocument,
    createSyncSource,
    cloneSyncSource,
    triggerSyncSource,
    deleteSyncSource,
  } = useKBDetail(id);

  const [isDragging, setIsDragging] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [creatingSource, setCreatingSource] = useState(false);
  const [syncSourcesExpanded, setSyncSourcesExpanded] = useState(false);
  const [viewerDoc, setViewerDoc] = useState<KBDocument | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownload = async (doc: KBDocument) => {
    if (downloadingId) return;
    setDownloadingId(doc.id);
    try {
      await downloadKBDocument(id, doc, "download");
    } catch {
      /* silently ignore */
    } finally {
      setDownloadingId(null);
    }
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll document status while any document is still ingesting, using
  // exponential backoff to ease API load during long ingests: start at 2s,
  // grow ×1.5 each tick, cap at 30s. Reset to the fast interval whenever a
  // document changes state (a new doc appears, or a status flips), and stop
  // entirely once nothing is pending/processing.
  const pollDelayRef = useRef(POLL_MIN_MS);
  const docSignatureRef = useRef("");
  useEffect(() => {
    const pending = documents.some((d) => d.status === "pending" || d.status === "processing");

    // Signature of the current docs' ids+statuses; a change means new docs or a
    // status flip — reset backoff so the next poll is fast.
    const signature = documents
      .map((d) => `${d.id}:${d.status}`)
      .sort()
      .join("|");
    if (signature !== docSignatureRef.current) {
      docSignatureRef.current = signature;
      pollDelayRef.current = POLL_MIN_MS;
    }

    if (!pending) return;

    const timeout = setTimeout(() => {
      pollDelayRef.current = Math.min(Math.round(pollDelayRef.current * POLL_FACTOR), POLL_MAX_MS);
      refresh();
    }, pollDelayRef.current);
    return () => clearTimeout(timeout);
  }, [documents, refresh]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      try {
        await uploadDocument(file);
      } catch {
        /* toast handled in hook */
      }
    }
  };

  const documentColumns = useMemo<Column<KBDocument>[]>(
    () => [
      {
        key: "filename",
        header: "Name",
        cell: (doc) => (
          <div className="flex min-w-0 items-center gap-3">
            <span className="bg-muted text-muted-foreground inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
              <FileText className="h-3.5 w-3.5" />
            </span>
            <span className="text-foreground truncate font-medium" title={doc.filename}>
              {doc.filename}
            </span>
          </div>
        ),
      },
      {
        key: "filetype",
        header: "Type / size",
        className: "hidden sm:table-cell",
        cell: (doc) => (
          <span className="text-muted-foreground text-xs">
            {doc.filetype || "—"}
            {doc.filesize !== null && ` · ${formatBytes(doc.filesize)}`}
            {doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
          </span>
        ),
      },
      {
        key: "status",
        header: "Status",
        cell: (doc) => <StatusBadge status={doc.status} message={doc.error_message} />,
      },
      {
        key: "actions",
        header: "",
        align: "right",
        className: "w-0",
        cell: (doc) => {
          const dlBusy = downloadingId === doc.id;
          return (
            <div className="flex items-center gap-0.5">
              {doc.has_file && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-foreground h-8 w-8 p-0"
                    onClick={() => setViewerDoc(doc)}
                    title="Preview file"
                    aria-label="Preview file"
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-foreground h-8 w-8 p-0"
                    onClick={() => handleDownload(doc)}
                    disabled={!!downloadingId}
                    title="Download file"
                    aria-label="Download file"
                  >
                    {dlBusy ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-destructive h-8 w-8 p-0"
                onClick={() => {
                  if (confirm(`Remove "${doc.filename}" from this knowledge base?`))
                    deleteDocument(doc.id);
                }}
                title="Remove document"
                aria-label="Remove document"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          );
        },
      },
    ],
    [deleteDocument, downloadingId, handleDownload, setViewerDoc],
  );

  if (isLoading && !kb) return <KBDetailSkeleton />;
  if (error && !kb) {
    return (
      <div className="text-destructive flex h-64 items-center justify-center text-sm">{error}</div>
    );
  }
  if (!kb) return null;

  const scopeMeta = SCOPE_META[kb.scope];

  return (
    <div
      className="relative pb-8"
      onDragEnter={(e) => {
        if (e.dataTransfer.types.includes("Files")) {
          dragCounterRef.current += 1;
          setIsDragging(true);
        }
      }}
      onDragLeave={() => {
        dragCounterRef.current = Math.max(0, dragCounterRef.current - 1);
        if (dragCounterRef.current === 0) setIsDragging(false);
      }}
      onDragOver={(e) => {
        if (e.dataTransfer.types.includes("Files")) e.preventDefault();
      }}
      onDrop={(e) => {
        e.preventDefault();
        dragCounterRef.current = 0;
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      {isDragging && (
        <div className="bg-background/80 fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="border-foreground/30 bg-card flex flex-col items-center gap-4 rounded-xl border-2 border-dashed px-12 py-16">
            <span className="bg-muted text-foreground inline-flex h-14 w-14 items-center justify-center rounded-xl">
              <Upload className="h-6 w-6" />
            </span>
            <div className="text-center">
              <p className="text-foreground text-lg font-semibold">Drop to upload</p>
              <p className="text-muted-foreground mt-1 text-sm">
                Files will be added to{" "}
                <span className="text-foreground font-medium">{kb.name}</span>
              </p>
            </div>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={isUploading}
      />

      <PageHeader
        breadcrumbs={[{ label: "Knowledge bases", href: ROUTES.KB }, { label: kb.name }]}
        title={kb.name}
        description={
          kb.description || (
            <span className="font-mono text-xs">{kb.collection_name}</span>
          )
        }
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => refresh()} disabled={isLoading}>
              <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {isUploading ? "Uploading…" : "Upload"}
            </Button>
          </>
        }
      />

      <div className="text-muted-foreground mb-6 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="inline-flex items-center gap-1.5">
          <scopeMeta.icon className="h-3.5 w-3.5" />
          {scopeMeta.label}
          {kb.is_default && " · Default"}
        </span>
        <span>·</span>
        <span>{documents.length} documents</span>
        <span>·</span>
        <span>{documents.reduce((sum, d) => sum + d.chunk_count, 0).toLocaleString()} vectors</span>
      </div>

      {uploadProgress.length > 0 && (
        <section className="border-border bg-card mb-6 space-y-3 rounded-xl border p-4">
          {uploadProgress.map((up) => (
            <div key={up.uploadId}>
              <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
                <span className="text-foreground flex min-w-0 items-center gap-2 font-medium">
                  <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                  <span className="truncate" title={up.filename}>
                    {up.filename}
                  </span>
                </span>
                <span className="text-muted-foreground shrink-0 tabular-nums">
                  {up.percent === null
                    ? "Uploading…"
                    : up.percent >= 100
                      ? "Processing…"
                      : `${up.percent}%`}
                </span>
              </div>
              <Progress
                value={up.percent ?? undefined}
                className={cn(up.percent === null && "animate-pulse")}
              />
            </div>
          ))}
        </section>
      )}

      <section className="mb-8">
        <h2 className="text-foreground mb-3 text-sm font-semibold">Documents</h2>
        <DataTable<KBDocument>
          columns={documentColumns}
          rows={documents}
          getRowKey={(doc) => doc.id}
          loading={isLoading && documents.length === 0}
          empty={
            <EmptyState
              icon={Upload}
              title="No documents yet"
              description="Drag files anywhere on this page, or pick from your computer."
              cta={{ label: "Choose files", onClick: () => fileInputRef.current?.click() }}
            />
          }
        />
        {documents.length > 0 && (
          <div className="mt-3 flex flex-col items-center gap-2">
            {hasMoreDocuments && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => loadMoreDocuments()}
                disabled={isLoadingMoreDocs}
              >
                {isLoadingMoreDocs && <Loader2 className="h-4 w-4 animate-spin" />}
                {isLoadingMoreDocs ? "Loading…" : "Load more"}
              </Button>
            )}
            <p className="text-muted-foreground text-center text-xs">
              Showing {documents.length} of {documentsTotal} · drag files anywhere to add
            </p>
          </div>
        )}
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-foreground text-sm font-semibold">Sync sources</h2>
          {connectors.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => setWizardOpen(true)}>
              <Plus className="h-4 w-4" />
              Connect
            </Button>
          )}
        </div>

        {syncSources.length === 0 ? (
          <EmptyState
            icon={Plug}
            title={connectors.length > 0 ? "No sources connected" : "No connectors configured"}
            description={
              connectors.length > 0
                ? "Add one to keep this knowledge base in sync automatically."
                : "Configure connectors at the workspace level to start syncing from external sources."
            }
            cta={
              connectors.length > 0
                ? { label: "Connect source", onClick: () => setWizardOpen(true) }
                : undefined
            }
          />
        ) : (
          <>
            <ul className="border-border bg-card divide-border divide-y overflow-hidden rounded-xl border">
              {(syncSourcesExpanded ? syncSources : syncSources.slice(0, SYNC_SOURCES_VISIBLE)).map(
                (source) => (
                  <SyncSourceRow
                    key={source.id}
                    source={source}
                    kbId={id}
                    onTrigger={() => triggerSyncSource(source.id)}
                    onDelete={() => deleteSyncSource(source.id)}
                  />
                ),
              )}
            </ul>
            {syncSources.length > SYNC_SOURCES_VISIBLE && (
              <div className="mt-3 flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSyncSourcesExpanded((v) => !v)}
                >
                  {syncSourcesExpanded ? "Show less" : `Show all ${syncSources.length} sources`}
                </Button>
              </div>
            )}
          </>
        )}
      </section>

      <FileViewer
        kbId={id}
        doc={viewerDoc}
        open={viewerDoc !== null}
        onClose={() => setViewerDoc(null)}
      />

      <SyncSourceWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        connectors={connectors}
        collections={[{ name: kb.collection_name }]}
        defaultCollection={kb.collection_name}
        orgIntegrations={orgIntegrations}
        submitting={creatingSource}
        onSubmit={async (data) => {
          setCreatingSource(true);
          try {
            await createSyncSource(data);
            setWizardOpen(false);
          } catch {
            /* toast handled in hook */
          } finally {
            setCreatingSource(false);
          }
        }}
        onClone={async (sourceId, collectionName, name) => {
          setCreatingSource(true);
          try {
            await cloneSyncSource(sourceId, collectionName, name);
            setWizardOpen(false);
          } catch {
            /* toast handled in hook */
          } finally {
            setCreatingSource(false);
          }
        }}
      />
    </div>
  );
}

/** Skeleton mirroring the page layout: header, meta strip, and a few doc rows. */
function KBDetailSkeleton() {
  return (
    <div className="pb-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24 rounded-lg" />
          <Skeleton className="h-9 w-24 rounded-lg" />
        </div>
      </div>

      <Skeleton className="mb-6 h-4 w-64" />

      <Skeleton className="mb-3 h-4 w-24" />
      <div className="border-border bg-card divide-border divide-y overflow-hidden rounded-xl border">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-3">
            <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

function SyncSourceRow({
  source,
  kbId,
  onTrigger,
  onDelete,
}: {
  source: SyncSourceRead;
  kbId: string;
  onTrigger: () => void;
  onDelete: () => void;
}) {
  const lastSync = source.last_sync_at ? formatDateTime(source.last_sync_at) : "Never";
  const brand = CONNECTOR_BRAND[source.connector_type];
  return (
    <li className="overflow-hidden">
      <div className="hover:bg-accent flex items-center gap-3 px-4 py-3 transition-colors">
        <span className="bg-muted text-muted-foreground inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
          {brand ? (
            <BrandIcon name={brand} className="h-4 w-4" />
          ) : (
            <Plug className="h-3.5 w-3.5" />
          )}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-foreground truncate text-sm font-medium">{source.name}</p>
          </div>
          <div className="text-muted-foreground mt-0.5 flex flex-wrap items-center gap-x-2 text-xs">
            <span>Last sync · {lastSync}</span>
            {source.schedule_minutes && source.schedule_minutes > 0 && (
              <>
                <span>·</span>
                <span>every {source.schedule_minutes}m</span>
              </>
            )}
          </div>
        </div>
        {source.last_sync_status && (
          <SyncStatusBadge status={source.last_sync_status} message={source.last_error} />
        )}
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-foreground h-8 w-8 p-0"
          onClick={onTrigger}
          title="Trigger sync now"
          aria-label="Trigger sync now"
        >
          <RotateCw className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-destructive h-8 w-8 p-0"
          onClick={() => {
            if (confirm(`Disconnect "${source.name}"?`)) onDelete();
          }}
          title="Remove source"
          aria-label="Remove source"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      <SyncSourceLogs logsPath={`/kb/${kbId}/sync-sources/${source.id}/logs`} />
    </li>
  );
}

function StatusBadge({ status, message }: { status: string; message: string | null }) {
  const config = {
    completed: { Icon: CheckCircle2, label: "Ready", spin: false },
    processing: { Icon: Loader2, label: "Processing", spin: true },
    pending: { Icon: Clock, label: "Pending", spin: false },
    failed: { Icon: AlertCircle, label: "Failed", spin: false },
  } as const;
  const c = (config as Record<string, (typeof config)[keyof typeof config]>)[status] ?? {
    Icon: Clock,
    label: status,
    spin: false,
  };
  return (
    <Badge
      variant="outline"
      title={message ?? undefined}
      className={cn(
        "border-border gap-1 font-normal",
        status === "failed" ? "text-destructive" : "text-muted-foreground",
      )}
    >
      <c.Icon className={cn("h-3 w-3", c.spin && "animate-spin")} />
      {c.label}
    </Badge>
  );
}

function SyncStatusBadge({ status, message }: { status: string; message: string | null }) {
  return (
    <Badge
      variant="outline"
      title={message ?? undefined}
      className={cn(
        "border-border shrink-0 font-normal",
        status === "failed" ? "text-destructive" : "text-muted-foreground",
      )}
    >
      {status}
    </Badge>
  );
}

{% endraw %}
