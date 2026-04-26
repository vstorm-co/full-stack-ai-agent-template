"use client";

import { useState } from "react";
import { Button } from "@/components/ui";
import type { ActionRequest, ReviewConfig, Decision } from "@/types";
import { Wrench, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ToolApprovalDialogProps {
  actionRequests: ActionRequest[];
  reviewConfigs: ReviewConfig[];
  onDecisions: (decisions: Decision[]) => void;
  disabled?: boolean;
}

export function ToolApprovalDialog({
  actionRequests,
  reviewConfigs,
  onDecisions,
  disabled = false,
}: ToolApprovalDialogProps) {
  // Store edited args for each action
  const [editedArgs, setEditedArgs] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      actionRequests.map((a) => [a.id, JSON.stringify(a.args, null, 2)])
    )
  );
  const [hasChanges, setHasChanges] = useState(false);

  const handleArgsChange = (id: string, text: string) => {
    setEditedArgs((prev) => ({ ...prev, [id]: text }));
    setHasChanges(true);
  };

  const handleCancel = () => {
    // Reset to original args
    setEditedArgs(
      Object.fromEntries(
        actionRequests.map((a) => [a.id, JSON.stringify(a.args, null, 2)])
      )
    );
    setHasChanges(false);
  };

  const handleSave = () => {
    // Validate all JSON
    for (const id of Object.keys(editedArgs)) {
      try {
        JSON.parse(editedArgs[id] ?? "");
      } catch {
        return; // Invalid JSON, don't save
      }
    }
    setHasChanges(false);
  };

  const handleSubmit = () => {
    const decisions: Decision[] = actionRequests.map((a) => {
      try {
        const parsed = JSON.parse(editedArgs[a.id] ?? "");
        const original = JSON.stringify(a.args);
        const edited = JSON.stringify(parsed);

        if (original !== edited) {
          return {
            type: "edit" as const,
            editedAction: { id: a.id, tool_name: a.tool_name, args: parsed },
          };
        }
        return { type: "approve" as const };
      } catch {
        return { type: "reject" as const };
      }
    });
    onDecisions(decisions);
  };

  return (
    <div className="rounded-lg border border-yellow-500/50 bg-yellow-50/5 p-3 space-y-3">
      <div className="flex items-center gap-2 text-sm text-yellow-600">
        <AlertTriangle className="h-4 w-4" />
        <span className="font-medium">Tool approval required</span>
      </div>

      {actionRequests.map((action) => (
        <div key={action.id} className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
            <code className="text-xs font-semibold">{action.tool_name}</code>
          </div>
          <textarea
            className={cn(
              "w-full p-2 text-xs font-mono bg-background border rounded resize-none",
              "min-h-[80px] max-h-[200px]"
            )}
            value={editedArgs[action.id]}
            onChange={(e) => handleArgsChange(action.id, e.target.value)}
            disabled={disabled}
            rows={Math.min(10, (editedArgs[action.id]?.split("\n").length || 3) + 1)}
          />
        </div>
      ))}

      <div className="flex justify-end gap-2 pt-1 border-t">
        {hasChanges && (
          <>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs"
              onClick={handleCancel}
              disabled={disabled}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={handleSave}
              disabled={disabled}
            >
              Save
            </Button>
          </>
        )}
        <Button
          size="sm"
          className="h-7 text-xs"
          onClick={handleSubmit}
          disabled={disabled}
        >
          Submit ({actionRequests.length})
        </Button>
      </div>
    </div>
  );
}
