{% raw %}"use client";

import { useEffect, useRef, useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Download, ExternalLink, FileText, Loader2, X } from "lucide-react";

import { MarkdownContent } from "@/components/chat/markdown-content";
import { Button } from "@/components/ui/button";
import { DialogOverlay, DialogPortal } from "@/components/ui/dialog";

// ─────────────────────────────────────────────────────────────────────────────
// Viewer type detection
// ─────────────────────────────────────────────────────────────────────────────

type ViewerKind = "pdf" | "image" | "markdown" | "text" | "video" | "audio" | "html" | "unknown";

const TEXT_EXTENSIONS = new Set([
  "txt", "log", "csv", "tsv",
  "py", "js", "ts", "jsx", "tsx", "mjs", "cjs",
  "json", "jsonl", "yaml", "yml", "toml", "ini", "env", "cfg",
  "sh", "bash", "zsh", "fish",
  "sql", "xml", "html", "htm", "css", "scss", "sass", "less",
  "rs", "go", "java", "cpp", "cc", "c", "h", "cs", "rb", "php",
  "swift", "kt", "scala", "r", "m", "lua", "ex", "exs",
]);

function resolveViewerKind(mimeType: string, filename: string): ViewerKind {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";

  if (mimeType === "application/pdf") return "pdf";
  if (mimeType.startsWith("image/")) return "image";
  if (mimeType.startsWith("video/")) return "video";
  if (mimeType.startsWith("audio/")) return "audio";
  if (mimeType === "text/html" || ext === "html" || ext === "htm") return "html";
  if (ext === "md" || ext === "markdown" || mimeType === "text/markdown") return "markdown";
  if (
    mimeType.startsWith("text/") ||
    mimeType === "application/json" ||
    mimeType === "application/javascript" ||
    mimeType === "application/xml" ||
    mimeType === "application/x-yaml" ||
    TEXT_EXTENSIONS.has(ext)
  )
    return "text";

  return "unknown";
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

interface FileViewerDoc {
  id: string;
  filename: string;
  filetype: string | null;
}

interface FileViewerProps {
  kbId: string;
  doc: FileViewerDoc | null;
  open: boolean;
  onClose: () => void;
}

export function FileViewer({ kbId, doc, open, onClose }: FileViewerProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [viewerKind, setViewerKind] = useState<ViewerKind>("unknown");
  const [mimeType, setMimeType] = useState("application/octet-stream");
  const blobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  useEffect(() => {
    if (!open || !doc) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setBlobUrl(null);
      setTextContent(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const currentDoc = doc;

    (async () => {
      setLoading(true);
      setError(null);
      setBlobUrl(null);
      setTextContent(null);

      try {
        const res = await fetch(`/api/kb/${kbId}/documents/${currentDoc.id}/download`);
        if (!res.ok) throw new Error(`Failed to load file (${res.status})`);
        if (cancelled) return;

        const ct = res.headers.get("content-type") || "application/octet-stream";
        const mime = (ct.split(";")[0] ?? ct).trim();
        const kind = resolveViewerKind(mime, currentDoc.filename);

        if (!cancelled) {
          setMimeType(mime);
          setViewerKind(kind);
        }

        if (kind === "text" || kind === "markdown") {
          const text = await res.text();
          if (!cancelled) setTextContent(text);
        } else {
          const blob = await res.blob();
          if (!cancelled) {
            if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
            const url = URL.createObjectURL(blob);
            blobUrlRef.current = url;
            setBlobUrl(url);
          }
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load file");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, doc?.id, kbId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Action helpers ──────────────────────────────────────────────────────────

  const makeTempUrl = (): string | null => {
    if (blobUrl) return null;
    if (textContent !== null) return URL.createObjectURL(new Blob([textContent], { type: mimeType }));
    return null;
  };

  const handleDownload = () => {
    if (!doc) return;
    const tempUrl = makeTempUrl();
    const url = blobUrl || tempUrl;
    if (!url) return;
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    if (tempUrl) setTimeout(() => URL.revokeObjectURL(tempUrl), 0);
  };

  const handleOpenExternal = () => {
    const tempUrl = makeTempUrl();
    const url = blobUrl || tempUrl;
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");
    if (tempUrl) setTimeout(() => URL.revokeObjectURL(tempUrl), 60_000);
  };

  // ── Rendering ───────────────────────────────────────────────────────────────

  const hasContent = blobUrl !== null || textContent !== null;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogPortal>
        <DialogOverlay />
        <DialogPrimitive.Content
          className="
            bg-background fixed top-[50%] left-[50%] z-50
            flex h-[90vh] w-[95vw] max-w-5xl
            -translate-x-1/2 -translate-y-1/2
            flex-col overflow-hidden border shadow-lg
            sm:rounded-lg
            data-[state=open]:animate-in data-[state=closed]:animate-out
            data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0
            data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95
            duration-200
          "
        >
          {/* Header */}
          <div className="border-b flex shrink-0 items-center gap-3 px-4 py-2.5">
            <FileText className="text-muted-foreground h-4 w-4 shrink-0" />
            <DialogPrimitive.Title className="text-foreground flex-1 truncate text-sm font-medium">
              {doc?.filename ?? ""}
            </DialogPrimitive.Title>
            <div className="flex shrink-0 items-center gap-0.5">
              {hasContent && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-foreground h-7 w-7 p-0"
                    onClick={handleOpenExternal}
                    title="Open in new browser tab"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-foreground h-7 w-7 p-0"
                    onClick={handleDownload}
                    title="Download file"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </>
              )}
              <DialogPrimitive.Close asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground hover:text-foreground h-7 w-7 p-0"
                  title="Close"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </DialogPrimitive.Close>
            </div>
          </div>

          {/* Body */}
          <div className="relative min-h-0 flex-1 overflow-hidden">
            {loading && (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
              </div>
            )}

            {!loading && error && (
              <div className="flex h-full flex-col items-center justify-center gap-4 px-8 text-center">
                <p className="text-destructive text-sm">{error}</p>
              </div>
            )}

            {!loading && !error && viewerKind === "pdf" && blobUrl && (
              <iframe
                src={blobUrl}
                className="h-full w-full border-0"
                title={doc?.filename}
              />
            )}

            {!loading && !error && viewerKind === "image" && blobUrl && (
              <div className="flex h-full items-center justify-center overflow-auto p-4">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={blobUrl}
                  alt={doc?.filename}
                  className="max-h-full max-w-full rounded object-contain"
                />
              </div>
            )}

            {!loading && !error && viewerKind === "html" && blobUrl && (
              <iframe
                src={blobUrl}
                className="h-full w-full border-0"
                sandbox="allow-scripts allow-same-origin"
                title={doc?.filename}
              />
            )}

            {!loading && !error && viewerKind === "video" && blobUrl && (
              <div className="flex h-full items-center justify-center p-4">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <video src={blobUrl} controls className="max-h-full max-w-full rounded" />
              </div>
            )}

            {!loading && !error && viewerKind === "audio" && blobUrl && (
              <div className="flex h-full items-center justify-center p-4">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <audio src={blobUrl} controls className="w-full max-w-md" />
              </div>
            )}

            {!loading && !error && viewerKind === "markdown" && textContent !== null && (
              <div className="h-full overflow-auto p-6">
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <MarkdownContent content={textContent} />
                </div>
              </div>
            )}

            {!loading && !error && viewerKind === "text" && textContent !== null && (
              <div className="h-full overflow-auto">
                <pre className="text-foreground break-words whitespace-pre-wrap p-4 font-mono text-xs leading-relaxed">
                  {textContent}
                </pre>
              </div>
            )}

            {!loading && !error && viewerKind === "unknown" && blobUrl && (
              <div className="flex h-full flex-col items-center justify-center gap-4 px-8 text-center">
                <p className="text-muted-foreground text-sm">
                  This file type cannot be previewed inline.
                </p>
                <p className="text-muted-foreground text-xs">{doc?.filetype || mimeType}</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleOpenExternal}>
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    Open in browser
                  </Button>
                  <Button size="sm" onClick={handleDownload}>
                    <Download className="mr-1.5 h-3.5 w-3.5" />
                    Download
                  </Button>
                </div>
              </div>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </DialogPrimitive.Root>
  );
}
{% endraw %}
