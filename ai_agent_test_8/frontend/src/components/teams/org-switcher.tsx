"use client";

import { useEffect } from "react";
import { Building2, ChevronDown, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useOrganizations } from "@/hooks";
import { useRouter } from "next/navigation";

export function OrgSwitcher() {
  const { orgs, activeOrg, fetchOrgs, switchOrg } = useOrganizations();
  const router = useRouter();

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  const displayOrg = activeOrg ?? orgs[0];

  if (!displayOrg) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="h-9 rounded-lg"
        onClick={() => router.push("/orgs")}
      >
        <Building2 className="mr-2 h-4 w-4" />
        Select org
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="hover:bg-accent h-9 gap-2 rounded-lg px-2">
          <Avatar className="h-5 w-5">
            {displayOrg.avatar_url && <AvatarImage src={`/api/orgs/${displayOrg.id}/avatar`} />}
            <AvatarFallback className="text-[10px]">
              {displayOrg.name.substring(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <span className="max-w-28 truncate text-sm font-medium">{displayOrg.name}</span>
          <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        {orgs.map((org) => (
          <DropdownMenuItem key={org.id} onSelect={() => switchOrg(org.id)} className="gap-2">
            <Avatar className="h-5 w-5">
              {org.avatar_url && <AvatarImage src={`/api/orgs/${org.id}/avatar`} />}
              <AvatarFallback className="text-[10px]">
                {org.name.substring(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <span className="truncate">{org.name}</span>
            {org.is_personal && (
              <span className="text-muted-foreground ml-auto text-[10px]">Personal</span>
            )}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => router.push("/orgs")} className="gap-2">
          <Building2 className="h-4 w-4" />
          Manage organizations
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => router.push("/orgs?create=1")} className="gap-2">
          <Plus className="h-4 w-4" />
          New organization
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
