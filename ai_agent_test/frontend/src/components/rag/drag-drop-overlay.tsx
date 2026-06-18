"use client";

import { useEffect, useRef, useState } from "react";
import { Upload } from "lucide-react";

interface DragDropOverlayProps {
  /** Called when files are dropped. Validate / size-check inside. */
  onDrop: (files: File[]) => void;
  /** Disable activation (e.g., when no collection is selected). */
  disabled?: boolean;
  /** Headline shown in the overlay. */
  title?: string;
  /** Description shown under the headline. */
  description?: string;
  /** Comma-separated extension list shown as badges (e.g., ".pdf, .docx"). */
  acceptedFormats?: string[];
}

/**
 * Document-level drag-drop overlay. Renders a fullscreen branded drop zone when
 * the user drags files over the page. Uses a counter to handle nested
 * dragenter/dragleave correctly.
 */
export function DragDropOverlay({
  onDrop,
  disabled,
  title = "Drop files to upload",
  description = "Files will be added to the active collection",
  acceptedFormats,
}: DragDropOverlayProps) {
  const [active, setActive] = useState(false);
  const counter = useRef(0);

  useEffect(() => {
    if (disabled) return;

    const isFileDrag = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");

    const handleEnter = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      counter.current += 1;
      setActive(true);
    };
    const handleOver = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
    };
    const handleLeave = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      counter.current = Math.max(0, counter.current - 1);
      if (counter.current === 0) setActive(false);
    };
    const handleDrop = (e: DragEvent) => {
      if (!isFileDrag(e)) return;
      e.preventDefault();
      counter.current = 0;
      setActive(false);
      const files = Array.from(e.dataTransfer?.files ?? []);
      if (files.length > 0) onDrop(files);
    };

    document.addEventListener("dragenter", handleEnter);
    document.addEventListener("dragover", handleOver);
    document.addEventListener("dragleave", handleLeave);
    document.addEventListener("drop", handleDrop);

    return () => {
      document.removeEventListener("dragenter", handleEnter);
      document.removeEventListener("dragover", handleOver);
      document.removeEventListener("dragleave", handleLeave);
      document.removeEventListener("drop", handleDrop);
    };
  }, [disabled, onDrop]);

  if (!active) return null;

  return (
    <div
      role="presentation"
      aria-hidden
      className="bg-background/80 fixed inset-0 z-[55] flex items-center justify-center p-8 backdrop-blur-sm"
    >
      <div className="border-brand bg-card w-full max-w-2xl rounded-3xl border-2 border-dashed p-12 text-center shadow-2xl">
        <div className="bg-brand text-brand-foreground mx-auto flex h-14 w-14 items-center justify-center rounded-full">
          <Upload className="h-6 w-6" />
        </div>
        <h2 className="font-display text-foreground mt-6 text-2xl font-bold tracking-tight">
          {title}
        </h2>
        <p className="text-foreground/65 mt-2 text-sm">{description}</p>

        {acceptedFormats && acceptedFormats.length > 0 && (
          <div className="mt-5 flex flex-wrap justify-center gap-1.5">
            {acceptedFormats.map((fmt) => (
              <span
                key={fmt}
                className="border-foreground/15 bg-foreground/[0.03] text-foreground/70 inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wider uppercase"
              >
                {fmt.replace(/^\./, "")}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
