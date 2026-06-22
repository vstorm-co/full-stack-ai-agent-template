{% raw %}"use client";

import { use, useState } from "react";
import { AlertCircle, Database, Plug, PlayCircle, RefreshCw, Trash2, Unplug } from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState, LoadingState } from "@/components/states";
import { SyncSourceWizard } from "@/components/rag/sync-source-wizard";
import { SyncSourceLogs } from "@/components/rag/sync-source-logs";
import { BrandIcon } from "@/components/marketing/brand-icon";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
  Badge,
  Button,
} from "@/components/ui";
import { useOrgIntegrations } from "@/hooks/use-org-integrations";
import { useOrganizations } from "@/hooks";
import type { SyncSourceCreate, SyncSourceRead } from "@/lib/rag-api";
import { timeAgo } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

const CONNECTOR_BRAND: Record<string, "gdrive" | "github" | "notion" | "slack" | "dropbox" | "s3"> = {
  google_drive: "gdrive",
  gdrive: "gdrive",
  drive: "gdrive",
  github: "github",
  notion: "notion",
  slack: "slack",
  dropbox: "dropbox",
  s3: "s3",
  aws: "s3",
};

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  done: "default",
  error: "destructive",
  running: "secondary",
  pending: "outline",
};

function IntegrationCard({
  source,
  orgId,
  onDelete,
  onTrigger,
}: {
  source: SyncSourceRead;
  orgId: string;
  onDelete: (id: string) => void;
  onTrigger: (id: string) => void;
}) {
  const brand = CONNECTOR_BRAND[source.connector_type];
  const isUnassigned = !source.collection_name;

  return (
    <div className="border-foreground/10 bg-card overflow-hidden rounded-2xl border">
      <div className="flex items-start gap-4 p-4">
        <span className="bg-foreground/8 flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
          {brand ? (
            <BrandIcon name={brand} className="h-5 w-5" aria-hidden />
          ) : (
            <Database className="text-foreground h-5 w-5" />
          )}
        </span>

        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-foreground text-sm font-semibold">{source.name}</p>
            {isUnassigned ? (
              <Badge variant="outline" className="text-[10px]">
                <Unplug className="mr-1 h-2.5 w-2.5" />
                Unassigned
              </Badge>
            ) : (
              <Badge variant="secondary" className="font-mono text-[10px]">
                {source.collection_name}
              </Badge>
            )}
            {source.last_sync_status && (
              <Badge
                variant={STATUS_VARIANT[source.last_sync_status] ?? "outline"}
                className="text-[10px]"
              >
                {source.last_sync_status}
              </Badge>
            )}
          </div>
          <p className="text-foreground/55 font-mono text-xs tracking-wide uppercase">
            {source.connector_type}
            {source.schedule_minutes ? ` · every ${source.schedule_minutes}m` : " · manual"}
          </p>
          {source.last_sync_at && (
            <p className="text-foreground/45 text-xs">Last sync {timeAgo(source.last_sync_at)}</p>
          )}
          {source.last_error && (
            <p className="text-destructive flex items-start gap-1 text-xs">
              <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
              {source.last_error}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            title="Trigger sync"
            onClick={() => onTrigger(source.id)}
            disabled={isUnassigned}
          >
            <PlayCircle className="h-4 w-4" />
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive h-8 w-8">
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Remove integration?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently delete &ldquo;{source.name}&rdquo; and stop all scheduled syncs.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  onClick={() => onDelete(source.id)}
                >
                  Remove
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
      <SyncSourceLogs logsPath={`/orgs/${orgId}/integrations/${source.id}/logs`} />
    </div>
  );
}

export default function OrgIntegrationsPage({ params }: PageProps) {
  const { id } = use(params);
  const { orgs } = useOrganizations();
  const org = orgs.find((o) => o.id === id);

  const { sources, connectors, kbs, isLoading, submitting, createIntegration, deleteIntegration, triggerIntegration } =
    useOrgIntegrations(id);

  const [wizardOpen, setWizardOpen] = useState(false);

  const handleCreate = async (data: SyncSourceCreate) => {
    await createIntegration(data);
    setWizardOpen(false);
  };

  const unassigned = sources.filter((s) => !s.collection_name);
  const assigned = sources.filter((s) => s.collection_name);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={org?.name ?? "Organization"}
        title="Integrations"
        description="Manage data source integrations for this organization. Unassigned integrations can be reused across multiple knowledge bases."
        actions={
          <Button onClick={() => setWizardOpen(true)}>
            <Plug className="h-4 w-4" />
            Add integration
          </Button>
        }
      />

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={3} />
      ) : sources.length === 0 ? (
        <EmptyState
          icon={Plug}
          title="No integrations yet"
          description="Add a Google Drive or S3 integration to start syncing documents into knowledge bases."
          cta={{ label: "Add integration", onClick: () => setWizardOpen(true) }}
        />
      ) : (
        <div className="space-y-6">
          {unassigned.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-foreground/70 text-xs font-semibold tracking-wider uppercase">
                Org-level (unassigned)
              </h2>
              <div className="space-y-3">
                {unassigned.map((s) => (
                  <IntegrationCard
                    key={s.id}
                    source={s}
                    orgId={id}
                    onDelete={deleteIntegration}
                    onTrigger={triggerIntegration}
                  />
                ))}
              </div>
            </section>
          )}

          {assigned.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-foreground/70 text-xs font-semibold tracking-wider uppercase">
                Assigned to knowledge bases
              </h2>
              <div className="space-y-3">
                {assigned.map((s) => (
                  <IntegrationCard
                    key={s.id}
                    source={s}
                    orgId={id}
                    onDelete={deleteIntegration}
                    onTrigger={triggerIntegration}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <SyncSourceWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        connectors={connectors}
        collections={kbs.map((kb) => ({ name: kb.collection_name, label: kb.name }))}
        onSubmit={handleCreate}
        submitting={submitting}
      />
    </div>
  );
}
{% endraw %}
