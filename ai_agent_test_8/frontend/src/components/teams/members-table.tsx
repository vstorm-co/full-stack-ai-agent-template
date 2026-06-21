"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Trash2 } from "lucide-react";
import type { OrganizationMember, OrgRole } from "@/types";

interface MembersTableProps {
  members: OrganizationMember[];
  currentUserId: string;
  canManage: boolean;
  onRoleChange: (userId: string, role: OrgRole) => void;
  onRemove: (userId: string) => void;
}

const roleBadgeVariant: Record<OrgRole, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

export function MembersTable({
  members,
  currentUserId,
  canManage,
  onRoleChange,
  onRemove,
}: MembersTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Member</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Joined</TableHead>
          {canManage && <TableHead className="w-12" />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {members.map((m) => {
          const isSelf = m.user_id === currentUserId;
          const isOwner = m.role === "owner";
          return (
            <TableRow key={m.id}>
              <TableCell>
                <div className="flex items-center gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="text-xs">
                      {(m.full_name ?? m.email).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="text-sm font-medium">{m.full_name ?? m.email}</p>
                    {m.full_name && <p className="text-muted-foreground text-xs">{m.email}</p>}
                    {isSelf && <span className="text-muted-foreground text-xs">(you)</span>}
                  </div>
                </div>
              </TableCell>
              <TableCell>
                {canManage && !isOwner && !isSelf ? (
                  <Select
                    value={m.role}
                    onValueChange={(v) => onRoleChange(m.user_id, v as OrgRole)}
                  >
                    <SelectTrigger className="h-7 w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="member">Member</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Badge variant={roleBadgeVariant[m.role]}>{m.role}</Badge>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground text-sm">
                {new Date(m.joined_at).toLocaleDateString()}
              </TableCell>
              {canManage && (
                <TableCell>
                  {!isOwner && !isSelf && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive h-7 w-7 p-0"
                      onClick={() => onRemove(m.user_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </TableCell>
              )}
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
