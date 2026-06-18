"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  Download,
  ExternalLink,
  FileAudio,
  FileCode,
  FileImage,
  FileText,
  FileVideo,
  Loader2,
  X,
} from "lucide-react";

import { useFilePreviewStore } from "@/stores";
import { getFileUrl } from "@/lib/file-api";
import { cn } from "@/lib/utils";
import { MarkdownContent } from "./markdown-content";

const DEFAULT_WIDTH = 480;
const MIN_WIDTH = 320;
const MAX_WIDTH = 1100;
const STORAGE_KEY = "filePreviewPanelWidth";

/**
 * Right-hand sidebar that previews the file currently selected in the chat.
 * Switches viewer based on MIME type / extension; the user can drag the left
 * edge to resize, and the chosen width persists across sessions.
 */
export function FilePreviewPanel() {
  const file = useFilePreviewStore((s) => s.file);
  const close = useFilePreviewStore((s) => s.close);

  const [width, setWidth] = useState<number>(DEFAULT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);

  // Restore persisted width on first mount.
  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (stored) {
      const n = parseInt(stored, 10);
      if (Number.isFinite(n)) setWidth(clamp(n, MIN_WIDTH, MAX_WIDTH));
    }
  }, []);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => {
      // Width = distance from cursor to right edge of viewport.
      const next = clamp(window.innerWidth - e.clientX, MIN_WIDTH, MAX_WIDTH);
      setWidth(next);
    };
    const onUp = () => {
      setIsDragging(false);
      try {
        localStorage.setItem(STORAGE_KEY, String(width));
      } catch {
        /* private mode / quota — drop persistence silently */
      }
    };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [isDragging, width]);

  if (!file) return null;

  const inlineUrl = getFileUrl(file.id);
  const downloadUrl = `${inlineUrl}?disposition=attachment`;
  const ext = extOf(file.filename);
  const kind = previewKind(file.mime_type, ext);
  const KindIcon = iconFor(kind);

  return (
    <aside
      className="border-foreground/10 bg-card relative flex h-full max-w-full shrink-0 flex-col border-l"
      style={{ width: `${width}px` }}
      aria-label="File preview"
    >
      {/* Drag handle — sits on the left edge, takes ~6px of cursor target */}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize file preview"
        onMouseDown={onMouseDown}
        className={cn(
          "group absolute top-0 left-0 z-20 h-full w-1.5 -translate-x-1/2 cursor-col-resize",
          isDragging && "bg-brand/30",
        )}
      >
        <div className="bg-foreground/0 group-hover:bg-foreground/15 absolute top-1/2 left-1/2 h-12 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full transition-colors" />
      </div>

      {/* Header */}
      <header className="border-foreground/10 flex items-center gap-2 border-b px-3 py-2">
        <span className="bg-foreground/8 text-foreground/65 flex h-7 w-7 shrink-0 items-center justify-center rounded-md">
          <KindIcon className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate text-sm font-medium" title={file.filename}>
            {file.filename}
          </p>
          <p className="text-foreground/50 truncate font-mono text-[10px] tracking-wider uppercase">
            {ext ?? file.mime_type ?? "file"}
          </p>
        </div>
        <a
          href={inlineUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
          title="Open in new tab"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
        <a
          href={downloadUrl}
          className="text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
          title="Download"
        >
          <Download className="h-3.5 w-3.5" />
        </a>
        <button
          type="button"
          onClick={close}
          className="text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
          aria-label="Close preview"
          title="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </header>

      {/* Viewer — flex column so iframe/video can use h-full reliably */}
      <div className="flex min-h-0 flex-1 flex-col">
        <Viewer
          kind={kind}
          url={inlineUrl}
          downloadUrl={downloadUrl}
          filename={file.filename}
          ext={ext}
        />
      </div>
    </aside>
  );
}

// ─── Type detection ────────────────────────────────────────────────────────

type PreviewKind =
  | "image"
  | "pdf"
  | "csv"
  | "html"
  | "json"
  | "markdown"
  | "code"
  | "text"
  | "audio"
  | "video"
  | "binary";

function extOf(filename: string): string | null {
  if (!filename.includes(".")) return null;
  const e = filename.split(".").pop();
  return e ? e.toLowerCase() : null;
}

const IMAGE_EXTS = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico", "avif"]);
const AUDIO_EXTS = new Set(["mp3", "wav", "ogg", "oga", "m4a", "flac", "opus", "aac", "weba"]);
const VIDEO_EXTS = new Set(["mp4", "webm", "mov", "m4v", "ogv", "mkv"]);
const PLAIN_TEXT_EXTS = new Set(["txt", "log", "conf", "env", "gitignore", "dockerignore"]);
// Maps file extensions to highlight.js language slugs that rehype-highlight
// recognizes. Hitting one renders the file as a fenced code block, which
// gives us free syntax highlighting via the existing markdown pipeline.
const CODE_EXTS: Record<string, string> = {
  ts: "typescript",
  tsx: "tsx",
  js: "javascript",
  jsx: "jsx",
  mjs: "javascript",
  cjs: "javascript",
  py: "python",
  rb: "ruby",
  go: "go",
  rs: "rust",
  java: "java",
  kt: "kotlin",
  swift: "swift",
  c: "c",
  h: "c",
  cpp: "cpp",
  cc: "cpp",
  hpp: "cpp",
  cs: "csharp",
  php: "php",
  sh: "bash",
  bash: "bash",
  zsh: "bash",
  fish: "bash",
  ps1: "powershell",
  sql: "sql",
  yaml: "yaml",
  yml: "yaml",
  toml: "toml",
  ini: "ini",
  xml: "xml",
  graphql: "graphql",
  gql: "graphql",
  proto: "protobuf",
  dockerfile: "dockerfile",
  makefile: "makefile",
  scala: "scala",
  lua: "lua",
  vue: "vue",
  svelte: "svelte",
  r: "r",
  jl: "julia",
  ex: "elixir",
  exs: "elixir",
  erl: "erlang",
  elm: "elm",
  hs: "haskell",
  ml: "ocaml",
  fs: "fsharp",
  pl: "perl",
  scss: "scss",
  sass: "scss",
  less: "less",
  css: "css",
  diff: "diff",
  patch: "diff",
};

function previewKind(mime: string | undefined, ext: string | null): PreviewKind {
  const m = (mime ?? "").toLowerCase();
  if (m.startsWith("image/") || IMAGE_EXTS.has(ext ?? "")) return "image";
  if (m === "application/pdf" || ext === "pdf") return "pdf";
  if (m.startsWith("audio/") || AUDIO_EXTS.has(ext ?? "")) return "audio";
  if (m.startsWith("video/") || VIDEO_EXTS.has(ext ?? "")) return "video";
  if (m === "text/csv" || ext === "csv" || ext === "tsv") return "csv";
  if (m === "text/html" || ext === "html" || ext === "htm") return "html";
  if (m === "application/json" || ext === "json" || ext === "jsonc") return "json";
  if (m === "text/markdown" || ext === "md" || ext === "markdown" || ext === "mdx")
    return "markdown";
  if (CODE_EXTS[ext ?? ""]) return "code";
  if (m.startsWith("text/") || PLAIN_TEXT_EXTS.has(ext ?? "")) return "text";
  return "binary";
}

function iconFor(kind: PreviewKind) {
  switch (kind) {
    case "image":
      return FileImage;
    case "audio":
      return FileAudio;
    case "video":
      return FileVideo;
    case "code":
    case "json":
    case "html":
      return FileCode;
    default:
      return FileText;
  }
}

// ─── Viewer dispatcher ─────────────────────────────────────────────────────

interface ViewerProps {
  kind: PreviewKind;
  url: string;
  downloadUrl: string;
  filename: string;
  ext: string | null;
}

function Viewer({ kind, url, downloadUrl, filename, ext }: ViewerProps) {
  switch (kind) {
    case "image":
      return <ImageViewer url={url} alt={filename} />;
    case "pdf":
      return <PdfViewer url={url} filename={filename} />;
    case "audio":
      return <AudioViewer url={url} filename={filename} />;
    case "video":
      return <VideoViewer url={url} filename={filename} />;
    case "csv":
      return <CsvViewer url={url} />;
    case "html":
      return <HtmlViewer url={url} />;
    case "json":
      return <TextViewer url={url} mode="json" />;
    case "markdown":
      return <TextViewer url={url} mode="markdown" />;
    case "code":
      return <TextViewer url={url} mode="code" lang={CODE_EXTS[ext ?? ""] ?? "text"} />;
    case "text":
      return <TextViewer url={url} mode="text" />;
    case "binary":
      return <BinaryFallback url={downloadUrl} filename={filename} />;
  }
}

// ─── Individual viewers ────────────────────────────────────────────────────

function ImageViewer({ url, alt }: { url: string; alt: string }) {
  return (
    <div className="bg-foreground/[0.02] flex min-h-0 flex-1 items-center justify-center overflow-auto p-4">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={alt} className="max-h-full max-w-full object-contain" />
    </div>
  );
}

function PdfViewer({ url, filename }: { url: string; filename: string }) {
  // Browsers render PDFs natively in <iframe> when Content-Disposition is
  // ``inline`` (the default for our /api/files/{id} endpoint). #toolbar=0
  // collapses the heavy chrome on Chromium.
  return (
    <iframe
      src={`${url}#toolbar=0&navpanes=0`}
      title={filename}
      className="block min-h-0 w-full flex-1 border-0"
    />
  );
}

function AudioViewer({ url, filename }: { url: string; filename: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 p-6">
      <FileAudio className="text-foreground/35 h-12 w-12" />
      <p className="text-foreground/65 line-clamp-2 max-w-full text-center text-xs">{filename}</p>
      <audio controls src={url} className="w-full max-w-md" />
    </div>
  );
}

function VideoViewer({ url, filename }: { url: string; filename: string }) {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center bg-black p-3">
      <video controls src={url} title={filename} className="max-h-full max-w-full" />
    </div>
  );
}

function HtmlViewer({ url }: { url: string }) {
  // Sandboxed: no script execution, no same-origin access. The user can still
  // see the rendered HTML (incl. styles) but untrusted content can't escape.
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(url, { credentials: "include" })
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((text) => {
        if (!cancelled) setHtml(text);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (error) return <ErrorState message={error} />;
  if (html === null) return <LoadingState />;

  return (
    <iframe
      sandbox=""
      srcDoc={html}
      title="HTML preview"
      className="block min-h-0 w-full flex-1 border-0 bg-white"
    />
  );
}

function CsvViewer({ url }: { url: string }) {
  const [rows, setRows] = useState<string[][] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(url, { credentials: "include" })
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((text) => {
        if (!cancelled) setRows(parseCsv(text));
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState />;
  if (rows.length === 0) return <EmptyState message="Empty file" />;

  const [header, ...body] = rows;
  const MAX_ROWS = 500;
  const truncated = body.length > MAX_ROWS;
  const visible = truncated ? body.slice(0, MAX_ROWS) : body;

  return (
    <div className="min-h-0 flex-1 overflow-auto p-3">
      <div className="border-foreground/10 overflow-x-auto rounded-md border">
        <table className="min-w-full text-xs">
          <thead className="bg-foreground/[0.04] sticky top-0">
            <tr>
              {(header ?? []).map((cell, i) => (
                <th
                  key={i}
                  className="border-foreground/10 border-b px-2.5 py-1.5 text-left font-mono text-[10px] font-semibold tracking-wider uppercase"
                >
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row, ri) => (
              <tr key={ri} className="hover:bg-foreground/[0.03]">
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className="border-foreground/8 border-b px-2.5 py-1.5 align-top whitespace-nowrap"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {truncated && (
        <p className="text-foreground/55 mt-2 text-center font-mono text-[10px] tracking-wider uppercase">
          Showing {MAX_ROWS.toLocaleString()} of {body.length.toLocaleString()} rows · download to
          see all
        </p>
      )}
    </div>
  );
}

/** Minimal RFC 4180-ish parser: handles quoted fields and escaped quotes. */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  let i = 0;

  while (i < text.length) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        inQuotes = false;
        i++;
        continue;
      }
      field += c;
      i++;
      continue;
    }
    if (c === '"') {
      inQuotes = true;
      i++;
      continue;
    }
    if (c === "," || c === "\t") {
      row.push(field);
      field = "";
      i++;
      continue;
    }
    if (c === "\n" || c === "\r") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      if (c === "\r" && text[i + 1] === "\n") i += 2;
      else i++;
      continue;
    }
    field += c;
    i++;
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

interface TextViewerProps {
  url: string;
  mode: "text" | "json" | "markdown" | "code";
  /** highlight.js language slug — only used for ``mode === "code"``. */
  lang?: string;
}

function TextViewer({ url, mode, lang }: TextViewerProps) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(url, { credentials: "include" })
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((t) => {
        if (cancelled) return;
        if (mode === "json") {
          try {
            setText(JSON.stringify(JSON.parse(t), null, 2));
          } catch {
            setText(t);
          }
        } else {
          setText(t);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, [url, mode]);

  if (error) return <ErrorState message={error} />;
  if (text === null) return <LoadingState />;

  if (mode === "markdown") {
    return (
      <div className="prose-sm min-h-0 max-w-none flex-1 overflow-auto p-4 text-sm">
        <MarkdownContent content={text} />
      </div>
    );
  }

  if (mode === "code") {
    // Wrap in a fenced block and let MarkdownContent (rehype-highlight) do
    // syntax coloring — saves us from importing highlight.js separately.
    const fenced = "```" + (lang ?? "text") + "\n" + text + "\n```";
    return (
      <div className="min-h-0 flex-1 overflow-auto">
        <MarkdownContent content={fenced} />
      </div>
    );
  }

  return (
    <pre
      className={cn(
        "bg-foreground/[0.02] m-0 min-h-0 flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed",
        "whitespace-pre",
      )}
    >
      {text}
    </pre>
  );
}

function BinaryFallback({ url, filename }: { url: string; filename: string }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="bg-foreground/8 text-foreground/65 flex h-14 w-14 items-center justify-center rounded-2xl">
        <FileText className="h-6 w-6" />
      </div>
      <div>
        <p className="text-foreground text-sm font-medium">{filename}</p>
        <p className="text-foreground/55 mt-1 text-xs">No inline preview for this file type.</p>
      </div>
      <a
        href={url}
        className="border-foreground/15 hover:border-foreground/40 hover:bg-foreground/5 mt-2 inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors"
      >
        <Download className="h-3.5 w-3.5" />
        Download
      </a>
    </div>
  );
}

// ─── State helpers ─────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="text-foreground/55 flex min-h-0 flex-1 items-center justify-center gap-2 text-xs">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      Loading…
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="text-destructive/80 flex min-h-0 flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-xs">
      <AlertCircle className="h-5 w-5" />
      <p>Couldn&apos;t load preview</p>
      <p className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">{message}</p>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-foreground/55 flex min-h-0 flex-1 items-center justify-center text-xs">
      {message}
    </div>
  );
}

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}
