"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, MailPlus, Plus, UserPlus, Users } from "lucide-react";

import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";
import { useOrganizations } from "@/hooks";
import type { InvitationList, OrganizationMemberList } from "@/types";

export function TeamSummary() {
  const { activeOrg } = useOrganizations();
  const [members, setMembers] = useState<OrganizationMemberList | null>(null);
  const [invitations, setInvitations] = useState<InvitationList | null>(null);
  const [loading, setLoading] = useState(true);

  const orgId = activeOrg?.id ?? null;

  useEffect(() => {
    if (!orgId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all([
      apiClient.get<OrganizationMemberList>(`/orgs/${orgId}/members`).catch(() => null),
      apiClient.get<InvitationList>(`/orgs/${orgId}/invitations`).catch(() => null),
    ]).then(([m, i]) => {
      if (cancelled) return;
      setMembers(m);
      setInvitations(i);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  if (!activeOrg) {
    return null;
  }

  if (activeOrg.is_personal) {
    return (
      <section className="border-border bg-card flex flex-col rounded-xl border p-5 lg:p-6">
        <header>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">Team</p>
          <h2 className="font-display text-foreground mt-1 text-xl font-semibold tracking-tight">
            Personal workspace
          </h2>
        </header>
        <p className="text-foreground/65 mt-3 text-sm">
          You&apos;re working solo. Create an organization to invite teammates and share
          conversations + knowledge bases.
        </p>
        <div className="mt-auto pt-5">
          <Link
            href={ROUTES.ORGS_CREATE}
            className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create organization
          </Link>
        </div>
      </section>
    );
  }

  const memberCount = members?.total ?? 0;
  const pendingCount = (invitations?.items ?? []).filter((i) => i.status === "pending").length;

  return (
    <section className="border-border bg-card flex flex-col rounded-xl border p-5 lg:p-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Team · {activeOrg.name}
          </p>
          <h2 className="font-display text-foreground mt-1 text-xl font-semibold tracking-tight">
            Members &amp; invitations
          </h2>
        </div>
        <Link
          href={ROUTES.ORG_MEMBERS(activeOrg.id)}
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1 text-xs font-medium transition-colors"
        >
          Manage
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </header>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Stat
          icon={<Users className="h-4 w-4" />}
          label={memberCount === 1 ? "member" : "members"}
          value={loading ? null : memberCount}
        />
        <Stat
          icon={<MailPlus className="h-4 w-4" />}
          label={pendingCount === 1 ? "pending invite" : "pending invites"}
          value={loading ? null : pendingCount}
          tone={pendingCount > 0 ? "accent" : "neutral"}
        />
      </div>

      <div className="mt-auto pt-5">
        <Link
          href={ROUTES.ORG_MEMBERS(activeOrg.id)}
          className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors"
        >
          <UserPlus className="h-4 w-4" />
          Invite teammate
        </Link>
      </div>
    </section>
  );
}

function Stat({
  icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: React.ReactNode;
  label: string;
  value: number | null;
  tone?: "neutral" | "accent";
}) {
  const accent = tone === "accent" && value !== null && value > 0;
  return (
    <div
      className={`rounded-xl border p-3 ${
        accent ? "border-brand/40 bg-brand/[0.06]" : "border-border bg-background/60"
      }`}
    >
      <div className="text-foreground/55 inline-flex items-center gap-1.5 font-mono text-[11px] tracking-wider uppercase">
        {icon}
        {label}
      </div>
      <p className="font-display text-foreground mt-1 text-2xl font-bold tabular-nums">
        {value === null ? "—" : value.toLocaleString()}
      </p>
    </div>
  );
}
