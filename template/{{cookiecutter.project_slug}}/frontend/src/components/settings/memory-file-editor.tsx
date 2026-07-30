"use client";

import { useState } from "react";
import { Eye } from "lucide-react";

import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Textarea,
} from "@/components/ui";
import { MarkdownContent } from "@/components/chat";
import { MAX_MEMORY_CONTENT_CHARS, MAX_MEMORY_NAME_CHARS } from "./memory-file-name";

interface MemoryFileEditorProps {
  open: boolean;
  isNew: boolean;
  path: string;
  content: string;
  submitting: boolean;
  onPathChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onCancel: () => void;
  onSave: () => void;
}

/** Create/edit dialog for one memory file, with a markdown preview toggle. */
export function MemoryFileEditor({
  open,
  isNew,
  path,
  content,
  submitting,
  onPathChange,
  onContentChange,
  onCancel,
  onSave,
}: MemoryFileEditorProps) {
  const [showPreview, setShowPreview] = useState(false);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !submitting) {
          setShowPreview(false);
          onCancel();
        }
      }}
    >
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isNew ? "New memory file" : path}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {isNew && (
            <div>
              <Label htmlFor="memory-path">File name</Label>
              <Input
                id="memory-path"
                value={path}
                onChange={(e) => onPathChange(e.target.value)}
                placeholder="preferences.md"
                maxLength={MAX_MEMORY_NAME_CHARS}
                className="mt-1.5 font-mono text-sm"
              />
              <p className="text-foreground/45 mt-1 text-[11px]">
                Letters, digits, dots and dashes — no folders. <code>.md</code> is added if you
                leave it off.
              </p>
            </div>
          )}
          <div>
            <div className="flex items-center justify-between">
              <Label htmlFor="memory-content">Content</Label>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowPreview((v) => !v)}
                className="h-6 px-2 text-xs"
              >
                <Eye className="mr-1 h-3 w-3" />
                {showPreview ? "Edit" : "Preview"}
              </Button>
            </div>
            {showPreview ? (
              <div className="border-foreground/10 mt-1.5 max-h-96 overflow-y-auto rounded-md border p-3">
                <div className="prose-sm max-w-none text-sm">
                  <MarkdownContent content={content || "*Empty file.*"} />
                </div>
              </div>
            ) : (
              <Textarea
                id="memory-content"
                value={content}
                onChange={(e) => onContentChange(e.target.value)}
                placeholder="- Prefers concise answers&#10;- Base currency: EUR"
                rows={14}
                maxLength={MAX_MEMORY_CONTENT_CHARS}
                className="mt-1.5 font-mono text-sm"
              />
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={onSave} disabled={submitting}>
            {submitting ? "Saving…" : isNew ? "Create" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
