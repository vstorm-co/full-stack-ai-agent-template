"use client";

import { useCallback, useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Loader2, Clock } from "lucide-react";
import { Spinner } from "@/components/ui";
import type { RAGSyncLog, RAGSyncLogList } from "@/lib/rag-api";
import { apiClient } from "@/lib/api-client";
import { cn, timeAgo } from "@/lib/utils";

interface SyncSourceLogsProps {
  /** API path relative to /api, e.g. /kb/xxx/sync-sources/yyy/logs */
  logsPath: string;
}

const STATUS_ICON = {
  done: <CheckCircle className="h-3.5 w-3.5 text-green-500" />,
  error: <XCircle className="h-3.5 w-3.5 text-destructive" />,
  running: <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />,
  pending: <Clock className="h-3.5 w-3.5 text-muted-foreground" />,
} as const;

function statusIcon(status: string) {
  return STATUS_ICON[status as keyof typeof STATUS_ICON] ?? STATUS_ICON.pending;
}

function duration(log: RAGSyncLog): string {
  if (!log.started_at) return "—";
  const end = log.completed_at ? new Date(log.completed_at) : new Date();
  const ms = end.getTime() - new Date(log.started_at).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${Math.round(ms / 1000)}s`;
  return `${Math.round(ms / 60000)}m`;
}

function LogRow({ log }: { log: RAGSyncLog }) {
  return (
    <div className="border-foreground/8 flex items-start gap-3 border-b py-2.5 last:border-0">
      <div className="mt-0.5 shrink-0">{statusIcon(log.status)}</div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
          <span className="text-foreground text-xs font-medium capitalize">{log.status}</span>
          <span className="text-foreground/45 font-mono text-[10px] tracking-wide uppercase">
            {log.mode}
          </span>
          {log.started_at && (
            <span className="text-foreground/45 text-[10px]">{timeAgo(log.started_at)}</span>
          )}
          <span className="text-foreground/45 text-[10px]">{duration(log)}</span>
        </div>
        {log.status !== "running" && log.status !== "pending" && (
          <p className="text-foreground/55 mt-0.5 text-[10px]">
            {log.ingested > 0 && `${log.ingested} ingested`}
            {log.updated > 0 && ` · ${log.updated} updated`}
            {log.skipped > 0 && ` · ${log.skipped} skipped`}
            {log.failed > 0 && ` · ${log.failed} failed`}
            {log.total_files === 0 && log.ingested === 0 && "no files processed"}
          </p>
        )}
        {log.error_message && (
          <p className="text-destructive mt-0.5 text-[10px] leading-snug">{log.error_message}</p>
        )}
      </div>
    </div>
  );
}

export function SyncSourceLogs({ logsPath }: SyncSourceLogsProps) {
  const [open, setOpen] = useState(false);
  const [logs, setLogs] = useState<RAGSyncLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    if (loaded) return;
    setLoading(true);
    try {
      const data = await apiClient.get<RAGSyncLogList>(logsPath);
      setLogs(data.items);
      setLoaded(true);
    } catch {
      setLogs([]);
      setLoaded(true);
    } finally {
      setLoading(false);
    }
  }, [logsPath, loaded]);

  const toggle = () => {
    if (!open) load();
    setOpen((v) => !v);
  };

  return (
    <div className="border-foreground/8 border-t">
      <button
        type="button"
        onClick={toggle}
        className={cn(
          "text-foreground/55 hover:text-foreground flex w-full items-center gap-1.5 px-4 py-2 text-xs font-medium transition-colors",
        )}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        Sync history
        {loaded && logs.length > 0 && (
          <span className="text-foreground/35 ml-1">({logs.length})</span>
        )}
      </button>

      {open && (
        <div className="px-4 pb-3">
          {loading ? (
            <div className="flex items-center gap-2 py-2">
              <Spinner className="h-3.5 w-3.5" />
              <span className="text-foreground/45 text-xs">Loading…</span>
            </div>
          ) : logs.length === 0 ? (
            <p className="text-foreground/40 py-2 text-xs">No sync runs yet.</p>
          ) : (
            logs.map((log) => <LogRow key={log.id} log={log} />)
          )}
        </div>
      )}
    </div>
  );
}
