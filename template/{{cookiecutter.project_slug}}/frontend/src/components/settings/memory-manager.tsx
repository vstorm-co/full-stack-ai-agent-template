"use client";

import { useState } from "react";
import { NotebookPen, Pencil, Plus, PowerOff, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui";
import { EmptyState } from "@/components/states";
import { ApiError } from "@/lib/api-client";
import { getErrorMessage } from "@/lib/utils";
import { useMemoryFiles } from "@/hooks";
import { readMemoryFile, type MemoryFileEntry } from "@/lib/memory-api";
import { MemoryDeleteDialog } from "./memory-delete-dialog";
import { MemoryFileEditor } from "./memory-file-editor";
import { canonicalMemoryName, isValidMemoryName, MAIN_NOTEBOOK } from "./memory-file-name";

interface EditorState {
  path: string;
  content: string;
  /** null while creating a new file (CAS create-only). */
  version: string | null;
  isNew: boolean;
}

function formatSize(chars: number): string {
  return chars >= 1024 ? `${(chars / 1024).toFixed(1)} KB` : `${chars} chars`;
}

function sortFiles(files: MemoryFileEntry[]): MemoryFileEntry[] {
  // Main notebook first — it's what gets injected into every chat.
  return [...files].sort((a, b) =>
    a.path === MAIN_NOTEBOOK ? -1 : b.path === MAIN_NOTEBOOK ? 1 : a.path.localeCompare(b.path),
  );
}

/** Turn a failed request into advice the user can act on. */
function errorMessage(e: unknown, fallback: string): string {
  const code = e instanceof ApiError ? (e.data as { code?: string } | null)?.code : undefined;
  if (code === "MEMORY_FILE_EXISTS") {
    return "A file with that name already exists — edit that one instead.";
  }
  if (code === "MEMORY_VERSION_CONFLICT") {
    return "This file changed since it was loaded — the list has been refreshed, try again.";
  }
  return getErrorMessage(e, fallback);
}

export function MemoryManager() {
  const { files, truncated, disabled, isLoading, error, refresh, save, remove } = useMemoryFiles();

  const [editor, setEditor] = useState<EditorState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<MemoryFileEntry | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openEdit = async (entry: MemoryFileEntry) => {
    try {
      const file = await readMemoryFile(entry.path);
      if (file.truncated) {
        // Saving a truncated body back would drop everything past the cut.
        toast.error(`${entry.path} is too large to edit here.`);
        return;
      }
      setEditor({ path: file.path, content: file.content, version: file.version, isNew: false });
    } catch (e) {
      toast.error(errorMessage(e, "Failed to load file"));
    }
  };

  const handleSave = async () => {
    if (!editor) return;
    const path = canonicalMemoryName(editor.path);
    if (!isValidMemoryName(path)) {
      toast.error("Use a flat file name — letters, digits, dots and dashes, no folders.");
      return;
    }
    if (editor.isNew && files.some((f) => f.path === path)) {
      toast.error(`${path} already exists — edit that one instead.`);
      return;
    }
    setSubmitting(true);
    try {
      await save(path, { content: editor.content, version: editor.version });
      toast.success(`${path} saved.`);
      setEditor(null);
    } catch (e) {
      toast.error(errorMessage(e, "Failed to save file"));
      // The version in hand may be stale; drop it so the next attempt reloads.
      setEditor(null);
      void refresh();
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await remove(deleteTarget.path, deleteTarget.version);
      toast.success(`${deleteTarget.path} deleted.`);
    } catch (e) {
      toast.error(errorMessage(e, "Failed to delete file"));
      // Retrying with the same snapshot would fail identically.
      void refresh();
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  const sorted = sortFiles(files);

  if (disabled) {
    return (
      <EmptyState
        icon={PowerOff}
        title="Memory is turned off"
        description="This deployment runs without agent memory, so the assistant doesn't keep notes between conversations."
      />
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="border-destructive/30 bg-destructive/5 text-destructive flex items-center justify-between rounded-xl border px-4 py-3 text-sm">
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={() => refresh()}>
            Retry
          </Button>
        </div>
      )}

      <div className="flex items-baseline justify-between gap-3">
        <p className="text-foreground/55 text-xs">
          The assistant saves notes here with <code>write_memory</code> and reads them back in every
          conversation. Edit anything that&apos;s wrong, or delete what it shouldn&apos;t keep.
        </p>
        <Button
          size="sm"
          onClick={() => setEditor({ path: "", content: "", version: null, isNew: true })}
        >
          <Plus className="mr-1 h-3.5 w-3.5" />
          New file
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <div className="bg-muted h-14 animate-pulse rounded-xl" />
          <div className="bg-muted h-14 animate-pulse rounded-xl" />
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState
          icon={NotebookPen}
          title="No memories yet"
          description="Ask the assistant to remember something — or create a note yourself and it will know it in the next conversation."
        />
      ) : (
        <>
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {sorted.map((entry) => (
              <li key={entry.path} className="flex items-center gap-4 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <code className="text-foreground bg-foreground/8 rounded px-1.5 py-0.5 font-mono text-xs">
                      {entry.path}
                    </code>
                    {entry.path === MAIN_NOTEBOOK && (
                      <span className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
                        main notebook
                      </span>
                    )}
                  </div>
                  <p className="text-foreground/55 mt-1 text-xs">{formatSize(entry.size_chars)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => openEdit(entry)}
                  className="text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                  title="Edit"
                  aria-label={`Edit ${entry.path}`}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteTarget(entry)}
                  className="text-foreground/55 hover:bg-destructive/10 hover:text-destructive inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                  title="Delete"
                  aria-label={`Delete ${entry.path}`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
          {truncated && (
            <p className="text-foreground/45 text-[11px]">
              Showing the first {sorted.length} files. The assistant has more — delete some to see
              the rest.
            </p>
          )}
        </>
      )}

      <MemoryFileEditor
        open={editor !== null}
        isNew={editor?.isNew ?? false}
        path={editor?.path ?? ""}
        content={editor?.content ?? ""}
        submitting={submitting}
        onPathChange={(path) => setEditor((prev) => (prev ? { ...prev, path } : prev))}
        onContentChange={(content) => setEditor((prev) => (prev ? { ...prev, content } : prev))}
        onCancel={() => !submitting && setEditor(null)}
        onSave={handleSave}
      />

      <MemoryDeleteDialog
        path={deleteTarget?.path ?? null}
        deleting={deleting}
        onCancel={() => !deleting && setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
