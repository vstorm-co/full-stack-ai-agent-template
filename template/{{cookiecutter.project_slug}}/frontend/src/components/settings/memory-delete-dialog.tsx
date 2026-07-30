"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui";
import { MAIN_NOTEBOOK } from "./memory-file-name";

interface MemoryDeleteDialogProps {
  path: string | null;
  deleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

/** Confirmation for deleting one memory file. */
export function MemoryDeleteDialog({
  path,
  deleting,
  onCancel,
  onConfirm,
}: MemoryDeleteDialogProps) {
  return (
    <AlertDialog open={path !== null} onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {path}?</AlertDialogTitle>
          <AlertDialogDescription>
            {path === MAIN_NOTEBOOK
              ? "This is the main notebook the assistant reads in every conversation. Deleting it erases everything the assistant remembers about you; it will start a fresh notebook on the next memory it saves."
              : "The assistant will no longer see this note. This cannot be undone."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={deleting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {deleting ? "Deleting…" : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
