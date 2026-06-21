"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import { Camera, Loader2, MailPlus, Trash2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";

import { InviteMemberDialog } from "@/components/teams";
import { PageHeader } from "@/components/dashboard/page-header";
import { EmptyState, LoadingState } from "@/components/states";
import {
  Avatar,
  AvatarFallback,
  Badge,
  Button,
  DataTable,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  type Column,
} from "@/components/ui";
import { useAuth, useInvitations, useMembers, useOrganizations } from "@/hooks";
import type { OrganizationMember, OrgRole } from "@/types";
import { formatDate, getErrorMessage, MAX_AVATAR_SIZE_BYTES } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";

interface PageProps {
  params: Promise<{ id: string }>;
}

const ROLE_VARIANT: Record<OrgRole, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

function getInitials(nameOrEmail: string): string {
  return nameOrEmail
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");
}


export default function OrgMembersPage({ params }: PageProps) {
  const { id } = use(params);
  const { user } = useAuth();
  const { members, total, isLoading, fetchMembers, changeRole, removeMember } = useMembers(id);
  const { invitations, fetchInvitations, revokeInvitation } = useInvitations(id);
  const { orgs, fetchOrgs, patchOrg } = useOrganizations();
  const [inviteOpen, setInviteOpen] = useState(false);

  useEffect(() => {
    fetchMembers();
    fetchInvitations();
    fetchOrgs();
  }, [fetchMembers, fetchInvitations, fetchOrgs]);

  const org = orgs.find((o) => o.id === id);
  const currentMember = members.find((m) => m.user_id === user?.id);
  const canManage = currentMember?.role === "owner" || currentMember?.role === "admin";
  const pendingInvitations = invitations.filter((i) => i.status === "pending");

  // Workspace profile state — name edits stay local until "Save" lands the
  // PATCH; avatar uploads are immediate (a separate POST endpoint).
  const [name, setName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (org) setName(org.name);
  }, [org?.id, org?.name]);

  const handleSaveName = async () => {
    if (!org) return;
    const trimmed = name.trim();
    if (!trimmed || trimmed === org.name) return;
    setSavingName(true);
    try {
      await patchOrg(org.id, { name: trimmed });
    } finally {
      setSavingName(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    if (file.size > MAX_AVATAR_SIZE_BYTES) {
      toast.error("Avatar too large. Maximum 2MB.");
      return;
    }
    setAvatarUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`/api/orgs/${id}/avatar`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      toast.success("Workspace avatar updated");
      await fetchOrgs(true);
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to upload avatar"));
    } finally {
      setAvatarUploading(false);
    }
  };

  const columns = useMemo<Column<OrganizationMember>[]>(() => {
    const cols: Column<OrganizationMember>[] = [
      {
        key: "member",
        header: "Member",
        cell: (m) => {
          const isSelf = m.user_id === user?.id;
          return (
            <div className="flex min-w-0 items-center gap-3">
              <Avatar className="h-8 w-8 shrink-0">
                <AvatarFallback className="text-[10px]">
                  {getInitials(m.full_name || m.email)}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="text-foreground truncate text-sm font-medium">
                  {m.full_name || m.email.split("@")[0]}
                  {isSelf && <span className="text-muted-foreground font-normal"> (you)</span>}
                </p>
                <p className="text-muted-foreground truncate text-xs">{m.email}</p>
              </div>
            </div>
          );
        },
      },
      {
        key: "role",
        header: "Role",
        cell: (m) => {
          const isSelf = m.user_id === user?.id;
          const isOwner = m.role === "owner";
          if (canManage && !isOwner && !isSelf) {
            return (
              <Select value={m.role} onValueChange={(v) => changeRole(m.user_id, v as OrgRole)}>
                <SelectTrigger className="h-8 w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="member">Member</SelectItem>
                </SelectContent>
              </Select>
            );
          }
          return (
            <Badge variant={ROLE_VARIANT[m.role]} className="capitalize">
              {m.role}
            </Badge>
          );
        },
      },
      {
        key: "joined",
        header: "Joined",
        cell: (m) => <span className="text-muted-foreground text-sm">{formatDate(m.joined_at)}</span>,
      },
    ];

    if (canManage) {
      cols.push({
        key: "actions",
        header: "",
        align: "right",
        className: "w-0",
        cell: (m) => {
          const isSelf = m.user_id === user?.id;
          const isOwner = m.role === "owner";
          if (isOwner || isSelf) return null;
          return (
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive"
              onClick={() => removeMember(m.user_id)}
              aria-label={`Remove ${m.full_name || m.email}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          );
        },
      });
    }

    return cols;
  }, [canManage, user?.id, changeRole, removeMember]);

  return (
    <div className="space-y-6">
      <PageHeader
        title={org?.name ?? "Members"}
        description={`${total} ${total === 1 ? "person has" : "people have"} access to this workspace. Owners and admins can invite teammates and adjust roles.`}
        breadcrumbs={[
          { label: "Organizations", href: ROUTES.ORGS },
          { label: org?.name ?? "Members" },
        ]}
        actions={
          canManage ? (
            <Button onClick={() => setInviteOpen(true)}>
              <UserPlus className="h-4 w-4" />
              Invite teammate
            </Button>
          ) : undefined
        }
      />

      {org && (
        <section className="border-border bg-card flex flex-wrap items-start gap-5 rounded-xl border p-5 sm:p-6">
          <button
            type="button"
            onClick={() => avatarInputRef.current?.click()}
            disabled={!canManage || avatarUploading}
            className="bg-muted text-foreground group relative flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl disabled:cursor-default"
            title={canManage ? "Change workspace avatar" : "Only owners and admins can edit"}
          >
            {org.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`/api/orgs/${org.id}/avatar?v=${org.updated_at ?? ""}`}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-foreground font-mono text-base font-semibold">
                {org.name.slice(0, 2).toUpperCase()}
              </span>
            )}
            {canManage && (
              <span className="absolute inset-0 flex items-center justify-center bg-black/45 opacity-0 transition-opacity group-hover:opacity-100">
                {avatarUploading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-white" />
                ) : (
                  <Camera className="h-5 w-5 text-white" />
                )}
              </span>
            )}
          </button>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={handleAvatarUpload}
          />

          <div className="min-w-0 flex-1 space-y-3">
            <div>
              <p className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
                Workspace profile
              </p>
              <p className="text-muted-foreground mt-0.5 text-xs">
                Name and avatar shown across the app to everyone in this workspace.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={!canManage || savingName}
                className="min-w-0 flex-1"
                placeholder="Workspace name"
                maxLength={255}
              />
              {canManage && name.trim() !== org.name && name.trim() !== "" && (
                <Button onClick={handleSaveName} disabled={savingName}>
                  {savingName ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                </Button>
              )}
            </div>
            {!canManage && (
              <p className="text-muted-foreground text-[11px]">
                Only owners and admins can edit workspace profile.
              </p>
            )}
          </div>
        </section>
      )}

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={3} />
      ) : members.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No members yet"
          description="Invite teammates by email to give them access to this workspace."
          cta={
            canManage ? { label: "Invite teammate", onClick: () => setInviteOpen(true) } : undefined
          }
        />
      ) : (
        <DataTable<OrganizationMember>
          columns={columns}
          rows={members}
          getRowKey={(m) => m.id}
          empty="No members yet."
        />
      )}

      {pendingInvitations.length > 0 && (
        <section className="space-y-3">
          <div>
            <p className="text-muted-foreground font-mono text-[11px] tracking-wider uppercase">
              Pending invitations
            </p>
            <h2 className="text-foreground text-sm font-semibold">
              {pendingInvitations.length} waiting on a response
            </h2>
          </div>
          <ul className="border-border bg-card divide-border divide-y overflow-hidden rounded-xl border">
            {pendingInvitations.map((inv) => (
              <li key={inv.id} className="flex flex-wrap items-center gap-3 px-4 py-3.5">
                <span className="bg-muted text-muted-foreground inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                  <MailPlus className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">{inv.email}</p>
                  <p className="text-muted-foreground mt-0.5 truncate text-xs">
                    Invited {formatDate(inv.created_at)}
                    {inv.expires_at && <> · expires {formatDate(inv.expires_at)}</>}
                  </p>
                </div>
                <Badge variant={ROLE_VARIANT[inv.role]} className="capitalize">
                  {inv.role}
                </Badge>
                {canManage && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-destructive"
                    onClick={() => revokeInvitation(inv.token)}
                  >
                    Revoke
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <InviteMemberDialog open={inviteOpen} onOpenChange={setInviteOpen} orgId={id} />
    </div>
  );
}
