{%- if cookiecutter.enable_rag and cookiecutter.use_frontend %}
{% raw %}"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useAuth } from "@/hooks";
import { ROUTES } from "@/lib/constants";
import { Button, Card, CardContent, Input, Badge, Skeleton, Spinner, Label, Switch,
  AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogAction, AlertDialogCancel,
  Dialog, DialogTrigger, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription,
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui";
import {
  Database, Search, Trash2, FileText, Plus, Upload, FolderOpen,
  CheckCircle, XCircle, ChevronLeft, Download, Eye, RefreshCw,
} from "lucide-react";
import {
  listCollections, getCollectionInfo, createCollection, deleteCollection,
  listTrackedDocuments, deleteTrackedDocument, ingestFile, searchDocuments,
  getDocumentDownloadUrl, listSyncLogs, cancelSync,
  listSyncSources, createSyncSource, deleteSyncSource, triggerSyncSource, listConnectors,
  type RAGCollectionInfo, type RAGTrackedDocument, type RAGSearchResult, type RAGSyncLog,
  type SyncSourceRead, type SyncSourceCreate, type ConnectorInfo,
} from "@/lib/rag-api";
{% endraw %}
{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}
import { BACKEND_URL } from "@/lib/constants";
{%- endif %}
{% raw %}
interface CollectionWithInfo {
  name: string;
  info: RAGCollectionInfo | null;
}

function StatusIcon({ status }: { status: string }) {
  const label = status === "done" ? "Completed" : status === "error" ? "Failed" : "Processing";
  return (
    <span role="status" aria-label={label}>
      {status === "done" && <CheckCircle className="h-4 w-4 text-green-500" />}
      {status === "error" && <XCircle className="h-4 w-4 text-red-500" />}
      {status !== "done" && status !== "error" && <Spinner className="h-4 w-4 text-brand" />}
    </span>
  );
}

export default function RAGPage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && user.role !== "admin") {
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
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number; filename: string } | null>(null);
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
  const [addSourceForm, setAddSourceForm] = useState<SyncSourceCreate>({
    name: "", connector_type: "", collection_name: "", config: {}, sync_mode: "full", schedule_minutes: null,
  });
  const [addSourceSubmitting, setAddSourceSubmitting] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [supportedFormats, setSupportedFormats] = useState<string[]>([".pdf", ".docx", ".txt", ".md"]);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCollections();
      const items: CollectionWithInfo[] = [];
      for (const name of data.items) {
        try { items.push({ name, info: await getCollectionInfo(name) }); }
        catch { items.push({ name, info: null }); }
      }
      setCollections(items);
      setSelected(prev => (items.length > 0 && !prev) ? (items[0]?.name ?? "") : prev);
    } catch { toast.error("Failed to load collections"); }
    finally { setLoading(false); }
  }, []);

  const fetchDocs = async (col: string) => {
    if (!col) { setDocs([]); return; }
    setDocsLoading(true);
    try {
      const data = await listTrackedDocuments(col);
      setDocs(data.items || []);
    } catch { setDocs([]); }
    finally { setDocsLoading(false); }
  };

  const fetchSyncLogs = async () => {
    setSyncLogsLoading(true);
    try {
      const data = await listSyncLogs(selected || undefined);
      setSyncLogs(data.items || []);
    } catch { setSyncLogs([]); }
    finally { setSyncLogsLoading(false); }
  };

  const fetchSyncSources = async () => {
    setSyncSourcesLoading(true);
    try {
      const data = await listSyncSources();
      setSyncSources(data.items || []);
    } catch { setSyncSources([]); }
    finally { setSyncSourcesLoading(false); }
  };

  const fetchConnectors = async () => {
    try {
      const data = await listConnectors();
      setConnectors(data.items || []);
    } catch { setConnectors([]); }
  };

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays}d ago`;
  };

  const handleAddSource = async () => {
    if (!addSourceForm.name || !addSourceForm.connector_type || !addSourceForm.collection_name) {
      toast.error("Name, connector type, and collection are required");
      return;
    }
    setAddSourceSubmitting(true);
    try {
      await createSyncSource(addSourceForm);
      toast.success(`Source "${addSourceForm.name}" created`);
      setAddSourceOpen(false);
      setAddSourceForm({ name: "", connector_type: "", collection_name: "", config: {}, sync_mode: "full", schedule_minutes: null });
      fetchSyncSources();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create source");
    } finally { setAddSourceSubmitting(false); }
  };

  const handleDeleteSource = async (sourceId: string) => {
    try {
      await deleteSyncSource(sourceId);
      toast.success("Source deleted");
      setSyncSources(prev => prev.filter(s => s.id !== sourceId));
    } catch { toast.error("Failed to delete source"); }
  };

  const handleTriggerSync = async (sourceId: string) => {
    try {
      await triggerSyncSource(sourceId);
      toast.success("Sync triggered");
      fetchSyncLogs();
      fetchSyncSources();
    } catch { toast.error("Failed to trigger sync"); }
  };

  const selectedConnector = connectors.find(c => c.type === addSourceForm.connector_type);

  useEffect(() => {
    fetchCollections();
    fetch("/api/v1/rag/supported-formats", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.formats) setSupportedFormats(data.formats); })
      .catch(() => {});
  }, [fetchCollections]);
  useEffect(() => { if (selected) fetchDocs(selected); }, [selected]);
{% endraw %}
{%- if (cookiecutter.use_celery or cookiecutter.use_taskiq or cookiecutter.use_arq) and cookiecutter.enable_redis %}

  // SSE for real-time ingestion status updates (auto-reconnect built-in)
  useEffect(() => {
    const es = new EventSource(`${BACKEND_URL}/api/v1/rag/status/stream`);

    es.addEventListener("status", (event) => {
      try {
        const data = JSON.parse(event.data);
        setDocs(prev => prev.map(d =>
          d.id === data.document_id ? { ...d, status: data.status } : d
        ));
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
{%- endif %}
{% raw %}
  const handleCreate = async () => {
    const name = newName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!name) return;
    try {
      await createCollection(name);
      toast.success(`"${name}" created`);
      setNewName(""); setShowCreate(false);
      await fetchCollections();
      setSelected(name);
    } catch { toast.error("Failed to create collection"); }
  };

  const handleDelete = async (name: string) => {
    try {
      await deleteCollection(name);
      toast.success(`"${name}" deleted`);
      setCollections(prev => prev.filter(c => c.name !== name));
      if (selected === name) { setSelected(""); setDocs([]); setSearchResults([]); }
    } catch { toast.error("Failed to delete"); }
  };

  const handleDeleteDoc = async (docId: string) => {
    try {
      await deleteTrackedDocument(docId);
      toast.success("Document deleted");
      setDocs(prev => prev.filter(d => d.id !== docId));
      fetchCollections();
    } catch { toast.error("Failed to delete"); }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !selected) return;
    e.target.value = "";

    const fileList = Array.from(files);
    const maxMb = parseInt(process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB || "50", 10);
    let successCount = 0;
    let errorCount = 0;

    setUploading(true);
    for (let i = 0; i < fileList.length; i++) {
      const file: File | undefined = fileList[i];
      if (!file) continue;
      setUploadProgress({ current: i + 1, total: fileList.length, filename: file.name });

      if (file.size > maxMb * 1024 * 1024) {
        toast.error(`${file.name}: Too large (max ${maxMb}MB)`);
        errorCount++;
        continue;
      }

      try {
        await ingestFile(selected, file);
        successCount++;
      } catch (err) {
        toast.error(`${file.name}: ${err instanceof Error ? err.message : "Failed"}`);
        errorCount++;
      }
    }

    setUploading(false);
    setUploadProgress(null);

    if (successCount > 0) {
      toast.success(`${successCount} file${successCount > 1 ? "s" : ""} ingested${errorCount > 0 ? `, ${errorCount} failed` : ""}`);
    }

    await fetchDocs(selected);
    await fetchCollections();
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || !selected) return;
    setSearching(true);
    try {
      const data = await searchDocuments({ query: searchQuery, collection_name: selected, limit: 10 });
      setSearchResults(data.results);
      setSearchDone(true);
    } catch { toast.error("Search failed"); }
    finally { setSearching(false); }
  };

  const info = collections.find(c => c.name === selected)?.info;

  return (
    <div className="-m-3 flex min-h-0 flex-1 sm:-m-6">
      {/* Sidebar — collections */}
      {sidebarOpen && (
        <div className="flex w-52 shrink-0 flex-col border-r lg:w-64">
          <div className="flex h-12 items-center justify-between border-b px-3">
            <h2 className="text-sm font-semibold">Collections</h2>
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setShowCreate(!showCreate)}>
                <Plus className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSidebarOpen(false)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {showCreate && (
            <div className="border-b p-3">
              <div className="flex gap-1.5">
                <Input placeholder="name" value={newName} onChange={e => setNewName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleCreate()} className="h-7 text-xs" />
                <Button size="sm" onClick={handleCreate} className="h-7 px-2 text-xs">OK</Button>
              </div>
            </div>
          )}

          <div className="scrollbar-thin flex-1 overflow-y-auto p-2">
            {loading ? (
              <div className="space-y-2 p-2">{[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full rounded-md" />)}</div>
            ) : collections.length === 0 ? (
              <div className="py-8 text-center">
                <Database className="text-muted-foreground mx-auto mb-2 h-6 w-6" />
                <p className="text-muted-foreground text-xs">No collections</p>
                <Button variant="link" size="sm" className="mt-1 text-xs" onClick={() => setShowCreate(true)}>Create one</Button>
              </div>
            ) : (
              <div className="space-y-1">
                {collections.map(col => (
                  <button
                    key={col.name}
                    onClick={() => { setSelected(col.name); setSearchResults([]); setTab("documents"); }}
                    className={`group flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm transition-colors ${selected === col.name ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-muted/50"}`}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{col.name}</p>
                      <p className="text-[10px] opacity-60">
                        {col.info ? `${col.info.total_vectors} vectors` : ""}
                      </p>
                    </div>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <button
                          className="text-destructive shrink-0 rounded p-0.5 opacity-0 group-hover:opacity-100"
                          onClick={e => e.stopPropagation()}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete collection &ldquo;{col.name}&rdquo;?</AlertDialogTitle>
                          <AlertDialogDescription>All documents and vectors will be permanently removed.</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDelete(col.name)}>Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex min-w-0 flex-1 flex-col">
        {!selected ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3">
            {!sidebarOpen && (
              <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(true)} className="mb-4">
                <Database className="mr-2 h-4 w-4" /> Show Collections
              </Button>
            )}
            <FolderOpen className="text-muted-foreground h-10 w-10" />
            <p className="text-muted-foreground text-sm">Select or create a collection</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-3">
                {!sidebarOpen && (
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSidebarOpen(true)}>
                    <Database className="h-4 w-4" />
                  </Button>
                )}
                <div>
                  <h2 className="font-semibold">{selected}</h2>
                  <p className="text-muted-foreground text-xs">
                    {info ? `${info.total_vectors.toLocaleString()} vectors · ${info.dim}d` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {uploadProgress ? (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground" role="status" aria-live="polite">
                    <Spinner className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
                    <span>{uploadProgress.current}/{uploadProgress.total}</span>
                    <span className="max-w-[120px] truncate">{uploadProgress.filename}</span>
                  </div>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading}>
                    <Upload className="mr-2 h-3.5 w-3.5" />
                    Upload Files
                  </Button>
                )}
                <input ref={fileRef} type="file" onChange={handleUpload} accept={supportedFormats.join(",")} multiple className="hidden" />
              </div>
            </div>

            {/* Upload progress bar */}
            {uploadProgress && (
              <div className="px-4">
                <div className="bg-muted h-1 w-full overflow-hidden rounded-full">
                  <div
                    className="bg-brand h-full rounded-full transition-all"
                    style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Tabs */}
            <div className="flex border-b px-4">
              <button className={`px-3 py-2 text-sm font-medium ${tab === "documents" ? "border-b-2 border-brand text-foreground" : "text-muted-foreground"}`} onClick={() => setTab("documents")}>
                Documents {docs.length > 0 && `(${docs.length})`}
              </button>
              <button className={`px-3 py-2 text-sm font-medium ${tab === "search" ? "border-b-2 border-brand text-foreground" : "text-muted-foreground"}`} onClick={() => setTab("search")}>
                Search
              </button>
              <button className={`px-3 py-2 text-sm font-medium ${tab === "sync" ? "border-b-2 border-brand text-foreground" : "text-muted-foreground"}`} onClick={() => { setTab("sync"); fetchSyncSources(); fetchConnectors(); if (syncLogs.length === 0 && !syncLogsLoading) fetchSyncLogs(); }}>
                Sync
              </button>
            </div>

            {/* Content */}
            <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
              {tab === "documents" && (
                docsLoading ? (
                  <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}</div>
                ) : docs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16">
                    <FileText className="text-muted-foreground mb-3 h-8 w-8" />
                    <p className="text-muted-foreground text-sm">No documents</p>
                    <p className="text-muted-foreground mt-1 text-xs">Upload PDF, DOCX, TXT, or MD</p>
                    <Button variant="outline" size="sm" className="mt-4" onClick={() => fileRef.current?.click()}>
                      <Upload className="mr-2 h-4 w-4" /> Upload Files
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {docs.map(doc => (
                      <div key={doc.id} className="flex items-center justify-between rounded-lg border p-3">
                        <div className="flex items-center gap-3 overflow-hidden">
                          <StatusIcon status={doc.status} />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium">{doc.filename}</p>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-[10px]">{doc.filetype.toUpperCase()}</Badge>
                              {doc.status === "done" && (
                                <span className="text-muted-foreground text-xs">
                                  {(doc.filesize / 1024).toFixed(0)} KB
                                </span>
                              )}
                              {doc.status === "processing" && <span className="text-brand text-xs">Processing...</span>}
                              {doc.status === "error" && (
                                <span className="text-xs text-red-500 truncate max-w-[200px]">{doc.error_message}</span>
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
                              className="text-muted-foreground hover:text-foreground rounded p-1.5 transition-colors"
                              title="View original"
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </a>
                          )}
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <button className="text-destructive hover:text-destructive rounded p-1.5 transition-colors">
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete &ldquo;{doc.filename}&rdquo;?</AlertDialogTitle>
                                <AlertDialogDescription>This will remove the document from vector store and storage.</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDeleteDoc(doc.id)}>Delete</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              )}

              {tab === "search" && (
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder={`Search in "${selected}"...`}
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && handleSearch()}
                    />
                    <Button onClick={handleSearch} disabled={searching || !searchQuery.trim()}>
                      <Search className="mr-2 h-4 w-4" />
                      {searching ? "..." : "Search"}
                    </Button>
                  </div>

                  {searchDone && searchResults.length === 0 && !searching && (
                    <div className="flex flex-col items-center justify-center py-12">
                      <Search className="text-muted-foreground mb-3 h-8 w-8" />
                      <p className="text-muted-foreground text-sm">No results found</p>
                      <p className="text-muted-foreground mt-1 text-xs">Try a different query or check another collection</p>
                    </div>
                  )}

                  {searchResults.length > 0 && (
                    <div className="space-y-2">
                      {searchResults.map((r, i) => {
                        // Try to find the source document for "View original" link
                        const sourceDoc = docs.find(d => d.filename === r.metadata?.filename && d.has_file);
                        return (
                          <Card key={i} className="p-3">
                            <div className="mb-1.5 flex flex-wrap items-center gap-2">
                              <FileText className="text-muted-foreground h-3.5 w-3.5" />
                              <span className="text-xs font-medium">{String(r.metadata?.filename ?? "?")}</span>
                              {r.metadata?.page_num != null && <Badge variant="outline" className="text-[10px]">p.{String(r.metadata.page_num)}</Badge>}
                              <Badge variant="secondary" className="ml-auto text-[10px]">{r.score.toFixed(3)}</Badge>
                              {sourceDoc && (
                                <a
                                  href={getDocumentDownloadUrl(sourceDoc.id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-brand hover:text-brand-hover inline-flex items-center gap-1 text-[10px] font-medium"
                                >
                                  <Eye className="h-3 w-3" /> View source
                                </a>
                              )}
                            </div>
                            <p className="text-muted-foreground text-sm leading-relaxed">{r.content}</p>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {tab === "sync" && (
                <div className="space-y-6">
                  {/* Sync Sources */}
                  <div>
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-semibold">Sync Sources</h3>
                      <Dialog open={addSourceOpen} onOpenChange={(open) => {
                        setAddSourceOpen(open);
                        if (open) {
                          setAddSourceForm({ name: "", connector_type: "", collection_name: selected || "", config: {}, sync_mode: "full", schedule_minutes: null });
                          if (connectors.length === 0) fetchConnectors();
                        }
                      }}>
                        <DialogTrigger asChild>
                          <Button size="sm" variant="outline">
                            <Plus className="mr-1 h-3.5 w-3.5" /> Add Source
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
                          <DialogHeader>
                            <DialogTitle>Add Sync Source</DialogTitle>
                            <DialogDescription>Configure a new data source for automatic synchronization.</DialogDescription>
                          </DialogHeader>
                          <div className="space-y-4 py-2">
                            <div className="space-y-1.5">
                              <Label htmlFor="source-name">Source Name</Label>
                              <Input id="source-name" placeholder="e.g. My S3 Bucket" value={addSourceForm.name} onChange={e => setAddSourceForm(f => ({ ...f, name: e.target.value }))} />
                            </div>
                            <div className="space-y-1.5">
                              <Label>Connector Type</Label>
                              <Select value={addSourceForm.connector_type} onValueChange={val => setAddSourceForm(f => ({ ...f, connector_type: val, config: {} }))}>
                                <SelectTrigger><SelectValue placeholder="Select connector..." /></SelectTrigger>
                                <SelectContent>
                                  {connectors.filter(c => c.enabled).map(c => (
                                    <SelectItem key={c.type} value={c.type}>{c.name}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>

                            {/* Dynamic config fields */}
                            {selectedConnector && Object.keys(selectedConnector.config_schema).length > 0 && (
                              <div className="space-y-3 rounded-lg border p-3">
                                <p className="text-xs font-medium text-muted-foreground">Connector Configuration</p>
                                {Object.entries(selectedConnector.config_schema).map(([key, field]) => (
                                  <div key={key} className="space-y-1">
                                    <Label htmlFor={`cfg-${key}`} className="text-xs">
                                      {field.label}{field.required && <span className="text-destructive ml-0.5">*</span>}
                                    </Label>
                                    {field.type === "boolean" ? (
                                      <div className="flex items-center gap-2">
                                        <Switch
                                          id={`cfg-${key}`}
                                          checked={!!addSourceForm.config[key]}
                                          onCheckedChange={val => setAddSourceForm(f => ({ ...f, config: { ...f.config, [key]: val } }))}
                                        />
                                        {field.help && <span className="text-[10px] text-muted-foreground">{field.help}</span>}
                                      </div>
                                    ) : (
                                      <>
                                        <Input
                                          id={`cfg-${key}`}
                                          type={field.secret ? "password" : field.type === "integer" ? "number" : "text"}
                                          placeholder={field.default !== undefined ? String(field.default) : ""}
                                          value={addSourceForm.config[key] !== undefined ? String(addSourceForm.config[key]) : ""}
                                          onChange={e => {
                                            const val = field.type === "integer" ? (e.target.value ? Number(e.target.value) : "") : e.target.value;
                                            setAddSourceForm(f => ({ ...f, config: { ...f.config, [key]: val } }));
                                          }}
                                          className="h-8 text-xs"
                                        />
                                        {field.help && <p className="text-[10px] text-muted-foreground">{field.help}</p>}
                                      </>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            <div className="space-y-1.5">
                              <Label>Target Collection</Label>
                              <Select value={addSourceForm.collection_name} onValueChange={val => setAddSourceForm(f => ({ ...f, collection_name: val }))}>
                                <SelectTrigger><SelectValue placeholder="Select collection..." /></SelectTrigger>
                                <SelectContent>
                                  {collections.map(c => (
                                    <SelectItem key={c.name} value={c.name}>{c.name}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              <div className="space-y-1.5">
                                <Label>Sync Mode</Label>
                                <Select value={addSourceForm.sync_mode || "full"} onValueChange={val => setAddSourceForm(f => ({ ...f, sync_mode: val }))}>
                                  <SelectTrigger><SelectValue /></SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="full">Full</SelectItem>
                                    <SelectItem value="new_only">New Only</SelectItem>
                                    <SelectItem value="update_only">Update Only</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-1.5">
                                <Label htmlFor="schedule-min">Schedule (minutes)</Label>
                                <Input
                                  id="schedule-min" type="number" min={0} placeholder="0 = manual"
                                  value={addSourceForm.schedule_minutes ?? ""}
                                  onChange={e => setAddSourceForm(f => ({ ...f, schedule_minutes: e.target.value ? Number(e.target.value) : null }))}
                                  className="h-8"
                                />
                              </div>
                            </div>
                          </div>
                          <DialogFooter>
                            <Button variant="outline" onClick={() => setAddSourceOpen(false)}>Cancel</Button>
                            <Button onClick={handleAddSource} disabled={addSourceSubmitting}>
                              {addSourceSubmitting ? <Spinner className="mr-2 h-3.5 w-3.5" /> : null}
                              Create Source
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                    </div>

                    {syncSourcesLoading ? (
                      <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}</div>
                    ) : syncSources.length === 0 ? (
                      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-8">
                        <Database className="text-muted-foreground mb-2 h-6 w-6" />
                        <p className="text-muted-foreground text-sm">No sync sources configured</p>
                        <p className="text-muted-foreground mt-1 text-xs">Add a source to start syncing documents automatically</p>
                      </div>
                    ) : (
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {syncSources.map(source => (
                          <Card key={source.id}>
                            <CardContent className="p-4">
                              <div className="mb-2 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <Database className="h-4 w-4" />
                                  <span className="font-medium text-sm">{source.name}</span>
                                </div>
                                <Badge variant={source.is_active ? "default" : "secondary"}>
                                  {source.is_active ? "Active" : "Disabled"}
                                </Badge>
                              </div>
                              <div className="text-sm text-muted-foreground space-y-1">
                                <p>{source.connector_type} &rarr; {source.collection_name}</p>
                                <p>{source.schedule_minutes ? `Every ${source.schedule_minutes}min` : "Manual"} &bull; {source.sync_mode}</p>
                                {source.last_sync_at && (
                                  <p className="text-xs">Last sync: {formatRelativeTime(source.last_sync_at)} &mdash; {source.last_sync_status}</p>
                                )}
                                {source.last_error && (
                                  <p className="text-xs text-red-500 truncate">{source.last_error}</p>
                                )}
                              </div>
                              <div className="flex gap-2 mt-3">
                                <Button size="sm" variant="outline" onClick={() => handleTriggerSync(source.id)}>
                                  <RefreshCw className="mr-1 h-3 w-3" /> Sync Now
                                </Button>
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button size="sm" variant="ghost">
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>Delete source &ldquo;{source.name}&rdquo;?</AlertDialogTitle>
                                      <AlertDialogDescription>This will remove the sync source configuration. Existing documents will not be affected.</AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                                      <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDeleteSource(source.id)}>Delete</AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Sync History */}
                  <div>
                    <h3 className="mb-3 text-sm font-semibold">History</h3>
                    {syncLogsLoading ? (
                      <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}</div>
                    ) : syncLogs.length === 0 ? (
                      <p className="text-muted-foreground text-sm">No sync history yet</p>
                    ) : (
                      <div className="space-y-2">
                        {syncLogs.map(log => (
                          <div key={log.id} className="rounded-lg border p-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <StatusIcon status={log.status === "running" ? "processing" : log.status} />
                                <span className="text-sm font-medium">{log.collection_name}</span>
                                <Badge variant="outline" className="text-[10px]">{log.source}</Badge>
                                <Badge variant="secondary" className="text-[10px]">{log.mode}</Badge>
                              </div>
                              <div className="flex items-center gap-2">
                                {log.started_at && (
                                  <span className="text-muted-foreground text-[10px]">{new Date(log.started_at).toLocaleString()}</span>
                                )}
                                {log.status === "running" && (
                                  <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px] text-destructive" onClick={async () => {
                                    try { await cancelSync(log.id); toast.success("Sync cancelled"); fetchSyncLogs(); } catch { toast.error("Failed to cancel"); }
                                  }}>Cancel</Button>
                                )}
                              </div>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
                              <span>{log.total_files} total</span>
                              {log.ingested > 0 && <span className="text-green-500">{log.ingested} new</span>}
                              {log.updated > 0 && <span className="text-blue-500">{log.updated} updated</span>}
                              {log.skipped > 0 && <span>{log.skipped} skipped</span>}
                              {log.failed > 0 && <span className="text-red-500">{log.failed} failed</span>}
                            </div>
                            {log.error_message && <p className="mt-1 text-xs text-red-500 truncate">{log.error_message}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

{% endraw %}
{%- else %}
export default function RAGPage() { return null; }
{%- endif %}
