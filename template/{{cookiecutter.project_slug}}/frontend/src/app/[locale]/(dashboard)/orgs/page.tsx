{% raw %}"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRightLeft, Building2, Camera, Check, Plug, Plus, Settings } from "lucide-react";
import { toast } from "sonner";

import { CreateOrgDialog } from "@/components/teams";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState, LoadingState } from "@/components/states";
import { Button } from "@/components/ui";
import { useOrganizations } from "@/hooks";
import { getErrorMessage, MAX_AVATAR_SIZE_BYTES } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";

export default function OrgsPage() {
  const { orgs, activeOrgId, fetchOrgs, switchOrg } = useOrganizations();
  const [createOpen, setCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingOrgIdRef = useRef<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleAvatarUpload = async (orgId: string, file: File) => {
    if (file.size > MAX_AVATAR_SIZE_BYTES) {
      toast.error("Avatar too large. Maximum 2MB.");
      return;
    }
    setUploadingFor(orgId);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`/api/orgs/${orgId}/avatar`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      toast.success("Organization avatar updated");
      await fetchOrgs(true);
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to upload avatar"));
    } finally {
      setUploadingFor(null);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await fetchOrgs();
      if (!cancelled) setIsLoading(false);
    })();
    if (searchParams.get("create") === "1") setCreateOpen(true);
    return () => {
      cancelled = true;
    };
  }, [fetchOrgs, searchParams]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Team"
        title="Organizations"
        description="Switch between workspaces, manage members, and spin up new organizations to collaborate with your team."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
            New organization
          </Button>
        }
      />

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={3} />
      ) : orgs.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No organizations yet"
          description="Create your first workspace to invite teammates and share access to conversations and knowledge bases."
          cta={{ label: "Create organization", onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {orgs.map((org) => {
            const isActive = org.id === activeOrgId;
            return (
              <li
                key={org.id}
                className="border-border bg-card hover:border-foreground/30 flex flex-col gap-4 rounded-xl border p-5 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <button
                    type="button"
                    className="group bg-muted text-foreground relative flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl"
                    onClick={() => {
                      pendingOrgIdRef.current = org.id;
                      fileInputRef.current?.click();
                    }}
                    disabled={uploadingFor !== null}
                    title="Change organization avatar"
                  >
                    {org.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={`/api/orgs/${org.id}/avatar?v=${org.updated_at ?? ""}`}
                        alt={org.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <Building2 className="h-5 w-5" />
                    )}
                    <span className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                      <Camera className="h-4 w-4 text-white" />
                    </span>
                  </button>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-foreground truncate text-sm font-semibold">{org.name}</h2>
                      {org.is_personal && (
                        <span className="border-border text-muted-foreground rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase">
                          Personal
                        </span>
                      )}
                      {isActive && (
                        <span className="border-border bg-muted text-foreground inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase">
                          <Check className="h-2.5 w-2.5" />
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-muted-foreground mt-0.5 truncate text-xs">
                      <span className="capitalize">{org.subscription_tier}</span>
                      {org.slug && <> · {org.slug}</>}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    disabled={isActive}
                    onClick={() => {
                      switchOrg(org.id);
                      router.push(ROUTES.DASHBOARD);
                    }}
                  >
                    <ArrowRightLeft className="h-3.5 w-3.5" />
                    {isActive ? "Current" : "Switch"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => router.push(ROUTES.ORG_INTEGRATIONS(org.id))}
                  >
                    <Plug className="h-3.5 w-3.5" />
                    Integrations
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => router.push(ROUTES.ORG_MEMBERS(org.id))}
                  >
                    <Settings className="h-3.5 w-3.5" />
                    Manage
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          const orgId = pendingOrgIdRef.current;
          e.target.value = "";
          if (file && orgId) handleAvatarUpload(orgId, file);
          pendingOrgIdRef.current = null;
        }}
      />
      <CreateOrgDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => fetchOrgs(true)}
      />
    </div>
  );
}
{% endraw %}
