"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Search,
  Shield,
} from "lucide-react";

import { UserDetailDrawer } from "@/components/admin/user-detail-drawer";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
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
import { useAdminUsers } from "@/hooks";
import type { AdminUserRead } from "@/hooks/use-admin-users";
import { cn, formatDate } from "@/lib/utils";

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
type SortDir = "asc" | "desc";
// Keys the backend can sort on (route → service → repo).
type SortKey = "email" | "full_name" | "created_at";

function getInitials(nameOrEmail: string): string {
  return nameOrEmail
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");
}

export default function AdminUsersPage() {
  const { users, total, isLoading, fetchUsers, updateUser, deleteUser, impersonateUser } =
    useAdminUsers();
  const [search, setSearch] = useState("");
  const [pageSize, setPageSize] = useState(50);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ by: SortKey; dir: SortDir }>({
    by: "created_at",
    dir: "desc",
  });
  const [drawerUser, setDrawerUser] = useState<AdminUserRead | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    setPage(0);
  }, [search, pageSize, sort.by, sort.dir]);

  const load = useCallback(
    (pg: number, q: string, ps: number, sortBy: SortKey, sortDir: SortDir) => {
      fetchUsers({
        skip: pg * ps,
        limit: ps,
        search: q || undefined,
        sortBy,
        sortDir,
      });
    },
    [fetchUsers],
  );

  // Debounced fetch — the server does filtering, sorting, and pagination.
  useEffect(() => {
    const timer = setTimeout(() => {
      load(page, search, pageSize, sort.by, sort.dir);
    }, 300);
    return () => clearTimeout(timer);
  }, [load, page, search, pageSize, sort.by, sort.dir]);

  // Keep the drawer's user object in sync with updates from the hook.
  useEffect(() => {
    if (drawerUser) {
      const fresh = users.find((u) => u.id === drawerUser.id);
      if (fresh && fresh !== drawerUser) setDrawerUser(fresh);
    }
  }, [users, drawerUser]);

  const handleOpenUser = useCallback((user: AdminUserRead) => {
    setDrawerUser(user);
    setDrawerOpen(true);
  }, []);

  const toggleSort = (key: SortKey) =>
    setSort((s) =>
      s.by === key ? { by: key, dir: s.dir === "asc" ? "desc" : "asc" } : { by: key, dir: "desc" },
    );

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const columns = useMemo<Column<AdminUserRead>[]>(
    () => [
      {
        key: "email",
        header: (
          <SortHeader active={sort.by === "email"} dir={sort.dir} onClick={() => toggleSort("email")}>
            User
          </SortHeader>
        ),
        cell: (u) => (
          <div className="flex min-w-0 items-center gap-3">
            <Avatar className="h-8 w-8 shrink-0">
              <AvatarImage src={`/api/users/avatar/${u.id}`} alt={u.email} />
              <AvatarFallback className="text-[10px]">
                {getInitials(u.full_name || u.email)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="text-foreground truncate text-sm font-medium">
                {u.full_name || u.email.split("@")[0]}
              </p>
              <p className="text-muted-foreground truncate text-xs">{u.email}</p>
            </div>
          </div>
        ),
      },
      {
        key: "role",
        hideBelow: "md",
        header: "Role",
        cell: (u) => (
          <div className="flex items-center gap-1.5">
            <span className="text-sm capitalize">{u.role}</span>
            {u.is_app_admin && (
              <Badge variant="outline" className="gap-0.5 font-normal">
                <Shield className="h-2.5 w-2.5" />
                App
              </Badge>
            )}
          </div>
        ),
      },
      {
        key: "is_active",
        hideBelow: "sm",
        header: "Status",
        cell: (u) =>
          u.is_active ? (
            <Badge
              variant="outline"
              className="border-border bg-foreground/5 text-foreground font-normal"
            >
              Active
            </Badge>
          ) : (
            <Badge
              variant="outline"
              className="border-border text-muted-foreground font-normal"
            >
              Suspended
            </Badge>
          ),
      },
      {
        key: "created_at",
        hideBelow: "md",
        header: (
          <SortHeader
            active={sort.by === "created_at"}
            dir={sort.dir}
            onClick={() => toggleSort("created_at")}
          >
            Joined
          </SortHeader>
        ),
        cell: (u) => (
          <span className="text-muted-foreground text-sm">
            {formatDate(u.created_at)}
          </span>
        ),
      },
      {
        key: "actions",
        header: "",
        align: "right",
        className: "w-0",
        cell: (u) => (
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleOpenUser(u);
            }}
          >
            Inspect
          </Button>
        ),
      },
    ],
    [sort.by, sort.dir, handleOpenUser],
  );

  const start = total === 0 ? 0 : page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search by email or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={String(pageSize)} onValueChange={(v) => setPageSize(Number(v))}>
          <SelectTrigger className="w-[120px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((n) => (
              <SelectItem key={n} value={String(n)}>
                {n} / page
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <span className="text-muted-foreground ml-auto text-xs">
          {total.toLocaleString()} total
        </span>
      </div>

      <DataTable<AdminUserRead>
        columns={columns}
        rows={users}
        getRowKey={(u) => u.id}
        loading={isLoading && users.length === 0}
        onRowClick={handleOpenUser}
        empty={search ? `No users match "${search}".` : "No users yet."}
      />

      {total > 0 && (
        <div className="border-border bg-card flex items-center justify-between rounded-xl border px-4 py-3">
          <span className="text-muted-foreground text-sm">
            {start}–{end} of {total.toLocaleString()}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || isLoading}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-muted-foreground px-2 text-sm">
              {page + 1} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || isLoading}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      <UserDetailDrawer
        user={drawerUser}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onUpdate={updateUser}
        onDelete={deleteUser}
        onImpersonate={impersonateUser}
      />
    </div>
  );
}

function SortHeader({
  active,
  dir,
  onClick,
  children,
}: {
  active: boolean;
  dir: SortDir;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const Icon = !active ? ArrowUpDown : dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "hover:text-foreground inline-flex items-center gap-1 text-left font-mono text-[11px] font-medium tracking-wider uppercase transition-colors",
        active ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {children}
      <Icon className={cn("h-3 w-3", !active && "opacity-40")} aria-hidden />
    </button>
  );
}
