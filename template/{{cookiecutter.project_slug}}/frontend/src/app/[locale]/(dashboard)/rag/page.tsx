{% raw %}"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuth } from "@/hooks";
import { ROUTES } from "@/lib/constants";
import {
  Button,
  Input,
  Badge,
  Skeleton,
  Spinner,
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from "@/components/ui";
import {
  Database,
  Search,
  Trash2,
  FileText,
  Plus,
  Upload,
  CheckCircle,
  XCircle,
  Eye,
  RefreshCw,
} from "lucide-react";
import {
  listCollections,
  getCollectionInfo,
  createCollection,
  deleteCollection,
  listTrackedDocuments,
  deleteTrackedDocument,
  ingestFile,
  searchDocuments,
  getDocumentDownloadUrl,
  listSyncLogs,
  cancelSync,
  listSyncSources,
  createSyncSource,
  deleteSyncSource,
  triggerSyncSource,
  listConnectors,
  type RAGCollectionInfo,
  type RAGTrackedDocument,
  type RAGSearchResult,
  type RAGSyncLog,
  type SyncSourceRead,
  type SyncSourceCreate,
  type ConnectorInfo,
} from "@/lib/rag-api";
import { DragDropOverlay } from "@/components/rag/drag-drop-overlay";
import { SyncSourceWizard } from "@/components/rag/sync-source-wizard";
import { apiClient } from "@/lib/api-client";
import { PageHeader } from "@/components/dashboard/page-header";

import { BACKEND_URL } from "@/lib/constants";
import { getErrorMessage, isAppAdmin, MAX_UPLOAD_SIZE_MB, timeAgo } from "@/lib/utils";

interface CollectionWithInfo {
  name: string;
  info: RAGCollectionInfo | null;
}

function StatusIcon({ status }: { status: string }) {
  const label = status === "done" ? "Completed" : status === "error" ? "Failed" : "Processing";
  return (
    <span role="status" aria-label={label}>
      {status === "done" && <CheckCircle className="text-foreground h-4 w-4" />}
      {status === "error" && <XCircle className="text-destructive h-4 w-4" />}
      {status !== "done" && status !== "error" && (
        <Spinner className="text-muted-foreground h-4 w-4" />
      )}
    </span>
  );
}

export default function RAGPage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && !isAppAdmin(user)) {
      router.replace(ROUTES.CHAT);
    }
  }, [user, router]);

  const [collections, setCollections] = useState<CollectionWithInfo[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [docs, setDocs] = useState<RAGTrackedDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<RAGSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoading, setDocsLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchDone, setSearchDone] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{
    current: number;
    total: number;
    filename: string;
  } | null>(null);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTabState] = useState<"documents" | "search" | "sync">(() => {
    if (typeof window !== "undefined") {
      const t = new URLSearchParams(window.location.search).get("tab");
      if (t === "search" || t === "sync") return t;
    }
    return "documents";
  });
  const setTab = (t: "documents" | "search" | "sync") => {
    setTabState(t);
    const url = new URL(window.location.href);
    if (t === "documents") url.searchParams.delete("tab");
    else url.searchParams.set("tab", t);
    window.history.replaceState({}, "", url.toString());
  };
  const [syncLogs, setSyncLogs] = useState<RAGSyncLog[]>([]);
  const [syncLogsLoading, setSyncLogsLoading] = useState(false);
  const [syncSources, setSyncSources] = useState<SyncSourceRead[]>([]);
  const [syncSourcesLoading, setSyncSourcesLoading] = useState(false);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [addSourceOpen, setAddSourceOpen] = useState(false);
  const [addSourceSubmitting, setAddSourceSubmitting] = useState(false);
  const [supportedFormats, setSupportedFormats] = useState<string[]>([
    ".pdf",
    ".docx",
    ".txt",
    ".md",
  ]);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCollections();
      const items: CollectionWithInfo[] = [];
      for (const name of data.items) {
        try {
          items.push({ name, info: await getCollectionInfo(name) });
        } catch {
          items.push({ name, info: null });
        }
      }
      setCollections(items);
      setSelected((prev) => (items.length > 0 && !prev ? (items[0]?.name ?? "") : prev));
    } catch {
      toast.error("Failed to load collections");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDocs = async (col: string) => {
    if (!col) {
      setDocs([]);
      return;
    }
    setDocsLoading(true);
    try {
      const data = await listTrackedDocuments(col);
      setDocs(data.items || []);
    } catch {
      setDocs([]);
    } finally {
      setDocsLoading(false);
    }
  };

  const fetchSyncLogs = async () => {
    setSyncLogsLoading(true);
    try {
      const data = await listSyncLogs(selected || undefined);
      setSyncLogs(data.items || []);
    } catch {
      setSyncLogs([]);
    } finally {
      setSyncLogsLoading(false);
    }
  };

  const fetchSyncSources = async () => {
    setSyncSourcesLoading(true);
    try {
      const data = await listSyncSources();
      setSyncSources(data.items || []);
    } catch {
      setSyncSources([]);
    } finally {
      setSyncSourcesLoading(false);
    }
  };

  const fetchConnectors = async () => {
    try {
      const data = await listConnectors();
      setConnectors(data.items || []);
    } catch {
      setConnectors([]);
    }
  };

  const handleAddSource = async (data: SyncSourceCreate) => {
    if (!data.name || !data.connector_type || !data.collection_name) {
      toast.error("Name, connector type, and collection are required");
      return;
    }
    setAddSourceSubmitting(true);
    try {
      await createSyncSource(data);
      toast.success(`Source "${data.name}" created`);
      setAddSourceOpen(false);
      fetchSyncSources();
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to create source"));
    } finally {
      setAddSourceSubmitting(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    try {
      await deleteSyncSource(sourceId);
      toast.success("Source deleted");
      setSyncSources((prev) => prev.filter((s) => s.id !== sourceId));
    } catch {
      toast.error("Failed to delete source");
    }
  };

  const handleTriggerSync = async (sourceId: string) => {
    try {
      await triggerSyncSource(sourceId);
      toast.success("Sync triggered");
      fetchSyncLogs();
      fetchSyncSources();
    } catch {
      toast.error("Failed to trigger sync");
    }
  };

  useEffect(() => {
    fetchCollections();
    apiClient
      .get<{ formats: string[] }>("/rag/supported-formats")
      .then((data) => {
        if (data?.formats) setSupportedFormats(data.formats);
      })
      .catch(() => {});
  }, [fetchCollections]);
  useEffect(() => {
    if (selected) fetchDocs(selected);
  }, [selected]);

  // SSE for real-time ingestion status updates (auto-reconnect built-in)
  useEffect(() => {
    const es = new EventSource(`${BACKEND_URL}/api/v1/rag/status/stream`);

    es.addEventListener("status", (event) => {
      try {
        const data = JSON.parse(event.data);
        setDocs((prev) =>
          prev.map((d) => (d.id === data.document_id ? { ...d, status: data.status } : d)),
        );
        if (data.status === "done") {
          toast.success(`${data.filename}: Ingested successfully`);
          fetchCollections();
        } else if (data.status === "error") {
          toast.error(`${data.filename}: Ingestion failed`);
        }
      } catch {}
    });

    return () => es.close();
  }, [fetchCollections]);

  const handleCreate = async () => {
    const name = newName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!name) return;
    try {
      await createCollection(name);
      toast.success(`"${name}" created`);
      setNewName("");
      setShowCreate(false);
      await fetchCollections();
      setSelected(name);
    } catch {
      toast.error("Failed to create collection");
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await deleteCollection(name);
      toast.success(`"${name}" deleted`);
      setCollections((prev) => prev.filter((c) => c.name !== name));
      if (selected === name) {
        setSelected("");
        setDocs([]);
        setSearchResults([]);
      }
    } catch {
      toast.error("Failed to delete");
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    try {
      await deleteTrackedDocument(docId);
      toast.success("Document deleted");
      setDocs((prev) => prev.filter((d) => d.id !== docId));
      fetchCollections();
    } catch {
      toast.error("Failed to delete");
    }
  };

  const processFiles = useCallback(
    async (fileList: File[]) => {
      if (!selected || fileList.length === 0) return;
      const allowedExts = supportedFormats.map((f) => f.toLowerCase());
      let successCount = 0;
      let errorCount = 0;

      setUploading(true);
      for (let i = 0; i < fileList.length; i++) {
        const file: File | undefined = fileList[i];
        if (!file) continue;
        setUploadProgress({ current: i + 1, total: fileList.length, filename: file.name });

        const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
        if (allowedExts.length > 0 && !allowedExts.includes(ext)) {
          toast.error(`${file.name}: Unsupported format (${ext})`);
          errorCount++;
          continue;
        }
        if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
          toast.error(`${file.name}: Too large (max ${MAX_UPLOAD_SIZE_MB}MB)`);
          errorCount++;
          continue;
        }

        try {
          await ingestFile(selected, file);
          successCount++;
        } catch (err) {
          toast.error(`${file.name}: ${getErrorMessage(err, "Failed")}`);
          errorCount++;
        }
      }

      setUploading(false);
      setUploadProgress(null);

      if (successCount > 0) {
        toast.success(
          `${successCount} file${successCount > 1 ? "s" : ""} ingested${errorCount > 0 ? `, ${errorCount} failed` : ""}`,
        );
      }

      await fetchDocs(selected);
      await fetchCollections();
    },
    [selected, supportedFormats, fetchCollections],
  );

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    e.target.value = "";
    await processFiles(Array.from(files));
  };

  const handleDrop = useCallback(
    (files: File[]) => {
      if (!selected) {
        toast.error("Select a collection before dropping files");
        return;
      }
      processFiles(files);
    },
    [selected, processFiles],
  );

  const handleSearch = async () => {
    if (!searchQuery.trim() || !selected) return;
    setSearching(true);
    try {
      const data = await searchDocuments({
        query: searchQuery,
        collection_name: selected,
        limit: 10,
      });
      setSearchResults(data.results);
      setSearchDone(true);
    } catch {
      toast.error("Search failed");
    } finally {
      setSearching(false);
    }
  };

  const info = collections.find((c) => c.name === selected)?.info;

  const tabs: { key: "documents" | "search" | "sync"; label: string }[] = [
    { key: "documents", label: docs.length > 0 ? `Documents (${docs.length})` : "Documents" },
    { key: "search", label: "Search" },
    { key: "sync", label: "Sync" },
  ];

  return (
    <div className="space-y-6">
      <DragDropOverlay
        onDrop={handleDrop}
        disabled={!selected || uploading}
        title={selected ? `Drop files into "${selected}"` : "Drop files to upload"}
        description={
          selected
            ? "Files will be ingested into the active collection"
            : "Select a collection first"
        }
        acceptedFormats={supportedFormats}
      />
      <SyncSourceWizard
        open={addSourceOpen}
        onOpenChange={setAddSourceOpen}
        connectors={connectors}
        collections={collections.map((c) => ({ name: c.name }))}
        defaultCollection={selected}
        onSubmit={handleAddSource}
        submitting={addSourceSubmitting}
      />

      <PageHeader
        eyebrow="Knowledge"
        title="RAG"
        description="Manage knowledge-base collections, ingest documents, run semantic search, and configure automated sync sources."
      />

      <div className="border-border bg-card rounded-xl border p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-1 flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Database className="text-muted-foreground h-4 w-4 shrink-0" />
              <span className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                Collection
              </span>
            </div>
            {loading ? (
              <Skeleton className="h-9 w-56 rounded-xl" />
            ) : collections.length === 0 ? (
              <span className="text-muted-foreground text-sm">No collections yet</span>
            ) : (
              <Select
                value={selected}
                onValueChange={(v) => {
                  setSelected(v);
                  setSearchResults([]);
                  setSearchDone(false);
                  setTab("documents");
                }}
              >
                <SelectTrigger className="h-9 w-full rounded-xl sm:w-72">
                  <SelectValue placeholder="Select a collection" />
                </SelectTrigger>
                <SelectContent>
                  {collections.map((col) => (
                    <SelectItem key={col.name} value={col.name}>
                      {col.name}
                      {col.info ? ` · ${col.info.total_vectors.toLocaleString()} vectors` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {info && (
              <span className="text-muted-foreground font-mono text-xs">
                {info.total_vectors.toLocaleString()} vectors · {info.dim}d
              </span>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="rounded-xl"
              onClick={() => setShowCreate((v) => !v)}
            >
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              New collection
            </Button>
            {uploadProgress ? (
              <div
                className="text-muted-foreground flex items-center gap-2 text-xs"
                role="status"
                aria-live="polite"
              >
                <Spinner className="text-muted-foreground h-3.5 w-3.5" aria-hidden="true" />
                <span className="font-mono">
                  {uploadProgress.current}/{uploadProgress.total}
                </span>
                <span className="max-w-[120px] truncate">{uploadProgress.filename}</span>
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="rounded-xl"
                onClick={() => fileRef.current?.click()}
                disabled={uploading || !selected}
              >
                <Upload className="mr-1.5 h-3.5 w-3.5" />
                Upload files
              </Button>
            )}
            {selected && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive hover:text-destructive rounded-xl"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete collection &ldquo;{selected}&rdquo;?</AlertDialogTitle>
                    <AlertDialogDescription>
                      All documents and vectors will be permanently removed.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      onClick={() => handleDelete(selected)}
                    >
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
            <input
              ref={fileRef}
              type="file"
              onChange={handleUpload}
              accept={supportedFormats.join(",")}
              multiple
              className="hidden"
            />
          </div>
        </div>

        {showCreate && (
          <div className="border-border mt-3 flex gap-2 border-t pt-3">
            <Input
              placeholder="collection_name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              className="h-9 max-w-xs rounded-xl"
            />
            <Button size="sm" className="h-9 rounded-xl" onClick={handleCreate}>
              Create
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-9 rounded-xl"
              onClick={() => {
                setShowCreate(false);
                setNewName("");
              }}
            >
              Cancel
            </Button>
          </div>
        )}

        {uploadProgress && (
          <div className="mt-3">
            <div className="bg-muted h-1 w-full overflow-hidden rounded-full">
              <div
                className="bg-foreground h-full rounded-full transition-all"
                style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {!selected ? (
        <div className="border-border bg-card text-muted-foreground flex flex-col items-center justify-center rounded-xl border py-16 text-center">
          <Database className="mb-3 h-8 w-8" />
          <p className="text-sm">Select or create a collection to get started.</p>
        </div>
      ) : (
        <>
          <div className="border-border flex gap-1 border-b">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => {
                  if (t.key === "sync") {
                    fetchSyncSources();
                    fetchConnectors();
                    if (syncLogs.length === 0 && !syncLogsLoading) fetchSyncLogs();
                  }
                  setTab(t.key);
                }}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                  tab === t.key
                    ? "border-foreground text-foreground"
                    : "text-muted-foreground hover:text-foreground border-transparent"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "documents" &&
            (docsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-xl" />
                ))}
              </div>
            ) : docs.length === 0 ? (
              <div className="border-border bg-card flex flex-col items-center justify-center rounded-xl border py-16 text-center">
                <FileText className="text-muted-foreground mb-3 h-8 w-8" />
                <p className="text-foreground text-sm font-medium">No documents</p>
                <p className="text-muted-foreground mt-1 text-xs">Upload PDF, DOCX, TXT, or MD</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4 rounded-xl"
                  onClick={() => fileRef.current?.click()}
                >
                  <Upload className="mr-2 h-4 w-4" /> Upload files
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {docs.map((doc) => (
                  <div
                    key={doc.id}
                    className="border-border bg-card hover:bg-accent flex items-center justify-between rounded-xl border p-3 transition-colors"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <StatusIcon status={doc.status} />
                      <div className="min-w-0">
                        <p className="text-foreground truncate text-sm font-medium">
                          {doc.filename}
                        </p>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="font-mono text-[10px]">
                            {doc.filetype.toUpperCase()}
                          </Badge>
                          {doc.status === "done" && (
                            <span className="text-muted-foreground font-mono text-xs">
                              {(doc.filesize / 1024).toFixed(0)} KB
                            </span>
                          )}
                          {doc.status === "processing" && (
                            <span className="text-muted-foreground text-xs">Processing...</span>
                          )}
                          {doc.status === "error" && (
                            <span className="text-destructive max-w-[200px] truncate text-xs">
                              {doc.error_message}
                            </span>
                          )}
                          {doc.created_at && (
                            <span className="text-muted-foreground text-[10px]">
                              {new Date(doc.created_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-0.5">
                      {doc.has_file && (
                        <a
                          href={getDocumentDownloadUrl(doc.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg p-1.5 transition-colors"
                          title="View original"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </a>
                      )}
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <button className="text-destructive hover:bg-accent rounded-lg p-1.5 transition-colors">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete &ldquo;{doc.filename}&rdquo;?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will remove the document from vector store and storage.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={() => handleDeleteDoc(doc.id)}
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                ))}
              </div>
            ))}

          {tab === "search" && (
            <div className="space-y-4">
              <div className="border-border bg-card rounded-xl border p-4">
                <div className="flex gap-2">
                  <Input
                    placeholder={`Search in "${selected}"...`}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    className="rounded-xl"
                  />
                  <Button
                    onClick={handleSearch}
                    disabled={searching || !searchQuery.trim()}
                    className="rounded-xl"
                  >
                    <Search className="mr-2 h-4 w-4" />
                    {searching ? "..." : "Search"}
                  </Button>
                </div>
              </div>

              {searchDone && searchResults.length === 0 && !searching && (
                <div className="border-border bg-card flex flex-col items-center justify-center rounded-xl border py-12 text-center">
                  <Search className="text-muted-foreground mb-3 h-8 w-8" />
                  <p className="text-foreground text-sm font-medium">No results found</p>
                  <p className="text-muted-foreground mt-1 text-xs">
                    Try a different query or check another collection
                  </p>
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="space-y-2">
                  {searchResults.map((r, i) => {
                    // Try to find the source document for "View source" link
                    const sourceDoc = docs.find(
                      (d) => d.filename === r.metadata?.filename && d.has_file,
                    );
                    return (
                      <div
                        key={i}
                        className="border-border bg-card rounded-xl border p-4 transition-colors"
                      >
                        <div className="mb-2 flex flex-wrap items-center gap-2">
                          <FileText className="text-muted-foreground h-3.5 w-3.5" />
                          <span className="text-foreground text-xs font-medium">
                            {String(r.metadata?.filename ?? "?")}
                          </span>
                          {r.metadata?.page_num != null && (
                            <Badge variant="outline" className="font-mono text-[10px]">
                              p.{String(r.metadata.page_num)}
                            </Badge>
                          )}
                          <Badge variant="secondary" className="ml-auto font-mono text-[10px]">
                            {r.score.toFixed(3)}
                          </Badge>
                          {sourceDoc && (
                            <a
                              href={getDocumentDownloadUrl(sourceDoc.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-[10px] font-medium"
                            >
                              <Eye className="h-3 w-3" /> View source
                            </a>
                          )}
                        </div>
                        <p className="text-muted-foreground text-sm leading-relaxed">{r.content}</p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {tab === "sync" && (
            <div className="space-y-6">
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-foreground text-sm font-semibold">Sync sources</h3>
                  <Button
                    size="sm"
                    variant="outline"
                    className="rounded-xl"
                    onClick={() => {
                      setAddSourceOpen(true);
                      if (connectors.length === 0) fetchConnectors();
                    }}
                  >
                    <Plus className="mr-1 h-3.5 w-3.5" /> Add source
                  </Button>
                </div>

                {syncSourcesLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-28 w-full rounded-xl" />
                    ))}
                  </div>
                ) : syncSources.length === 0 ? (
                  <div className="border-border bg-card flex flex-col items-center justify-center rounded-xl border py-8 text-center">
                    <Database className="text-muted-foreground mb-2 h-6 w-6" />
                    <p className="text-foreground text-sm font-medium">No sync sources configured</p>
                    <p className="text-muted-foreground mt-1 text-xs">
                      Add a source to start syncing documents automatically
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {syncSources.map((source) => (
                      <div
                        key={source.id}
                        className="border-border bg-card rounded-xl border p-4"
                      >
                        <div className="mb-2 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Database className="text-muted-foreground h-4 w-4" />
                            <span className="text-foreground text-sm font-medium">
                              {source.name}
                            </span>
                          </div>
                          <Badge variant={source.is_active ? "default" : "secondary"}>
                            {source.is_active ? "Active" : "Disabled"}
                          </Badge>
                        </div>
                        <div className="text-muted-foreground space-y-1 text-sm">
                          <p>
                            {source.connector_type} &rarr; {source.collection_name}
                          </p>
                          <p>
                            {source.schedule_minutes
                              ? `Every ${source.schedule_minutes}min`
                              : "Manual"}{" "}
                            &bull; {source.sync_mode}
                          </p>
                          {source.last_sync_at && (
                            <p className="text-xs">
                              Last sync: {timeAgo(source.last_sync_at)} &mdash;{" "}
                              {source.last_sync_status}
                            </p>
                          )}
                          {source.last_error && (
                            <p className="text-destructive truncate text-xs">{source.last_error}</p>
                          )}
                        </div>
                        <div className="mt-3 flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="rounded-xl"
                            onClick={() => handleTriggerSync(source.id)}
                          >
                            <RefreshCw className="mr-1 h-3 w-3" /> Sync now
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-destructive hover:text-destructive rounded-xl"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>
                                  Delete source &ldquo;{source.name}&rdquo;?
                                </AlertDialogTitle>
                                <AlertDialogDescription>
                                  This will remove the sync source configuration. Existing documents
                                  will not be affected.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                  onClick={() => handleDeleteSource(source.id)}
                                >
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <h3 className="text-foreground mb-3 text-sm font-semibold">History</h3>
                {syncLogsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-16 w-full rounded-xl" />
                    ))}
                  </div>
                ) : syncLogs.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No sync history yet</p>
                ) : (
                  <div className="space-y-2">
                    {syncLogs.map((log) => (
                      <div key={log.id} className="border-border bg-card rounded-xl border p-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <StatusIcon
                              status={log.status === "running" ? "processing" : log.status}
                            />
                            <span className="text-foreground text-sm font-medium">
                              {log.collection_name}
                            </span>
                            <Badge variant="outline" className="font-mono text-[10px]">
                              {log.source}
                            </Badge>
                            <Badge variant="secondary" className="font-mono text-[10px]">
                              {log.mode}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            {log.started_at && (
                              <span className="text-muted-foreground font-mono text-[10px]">
                                {new Date(log.started_at).toLocaleString()}
                              </span>
                            )}
                            {log.status === "running" && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-destructive h-6 rounded-lg px-2 text-[10px]"
                                onClick={async () => {
                                  try {
                                    await cancelSync(log.id);
                                    toast.success("Sync cancelled");
                                    fetchSyncLogs();
                                  } catch {
                                    toast.error("Failed to cancel");
                                  }
                                }}
                              >
                                Cancel
                              </Button>
                            )}
                          </div>
                        </div>
                        <div className="text-muted-foreground mt-2 flex flex-wrap gap-3 font-mono text-xs">
                          <span>{log.total_files} total</span>
                          {log.ingested > 0 && <span className="text-foreground">{log.ingested} new</span>}
                          {log.updated > 0 && (
                            <span className="text-foreground">{log.updated} updated</span>
                          )}
                          {log.skipped > 0 && <span>{log.skipped} skipped</span>}
                          {log.failed > 0 && (
                            <span className="text-destructive">{log.failed} failed</span>
                          )}
                        </div>
                        {log.error_message && (
                          <p className="text-destructive mt-1 truncate text-xs">
                            {log.error_message}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
{% endraw %}
