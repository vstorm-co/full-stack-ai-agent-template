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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAdminUsers } from "@/hooks";
import type { AdminUserRead } from "@/hooks/use-admin-users";
import { cn } from "@/lib/utils";

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
type SortDir = "asc" | "desc";
type SortKey = "email" | "full_name" | "role" | "is_active" | "created_at";

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

  // Reset to first page when filters change
  useEffect(() => {
    setPage(0);
  }, [search, pageSize, sort.by, sort.dir]);

  const load = useCallback(
    (pg: number, q: string, ps: number) => {
      fetchUsers({ skip: pg * ps, limit: ps, search: q || undefined });
    },
    [fetchUsers],
  );

  // Debounced fetch
  useEffect(() => {
    const timer = setTimeout(() => {
      load(page, search, pageSize);
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

  const handleOpenUser = (user: AdminUserRead) => {
    setDrawerUser(user);
    setDrawerOpen(true);
  };

  const toggleSort = (key: SortKey) =>
    setSort((s) =>
      s.by === key ? { by: key, dir: s.dir === "asc" ? "desc" : "asc" } : { by: key, dir: "desc" },
    );

  // Backend doesn't support sort yet on this endpoint, so apply client-side over current page.
  const sortedUsers = useMemo(() => {
    const arr = [...users];
    arr.sort((a, b) => {
      const av = (a[sort.by] ?? "") as string | number | boolean;
      const bv = (b[sort.by] ?? "") as string | number | boolean;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [users, sort.by, sort.dir]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6">
        <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">Users</p>
        <h2 className="font-display text-foreground [&_em]:font-accent mt-1 text-xl font-semibold tracking-tight [&_em]:font-normal [&_em]:italic">
          Everyone in <em>your workspace.</em>
        </h2>
        <p className="text-muted-foreground">
          Inspect, suspend, or impersonate any user in the workspace.
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
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
          <SelectTrigger className="w-[110px]">
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
      </div>

      <div className="text-muted-foreground mb-2 text-xs">{total} total</div>

      <Table>
        <TableHeader>
          <TableRow>
            <SortableHead
              active={sort.by === "email"}
              dir={sort.dir}
              onClick={() => toggleSort("email")}
            >
              User
            </SortableHead>
            <SortableHead
              active={sort.by === "role"}
              dir={sort.dir}
              onClick={() => toggleSort("role")}
            >
              Role
            </SortableHead>
            <SortableHead
              active={sort.by === "is_active"}
              dir={sort.dir}
              onClick={() => toggleSort("is_active")}
            >
              Status
            </SortableHead>
            <SortableHead
              active={sort.by === "created_at"}
              dir={sort.dir}
              onClick={() => toggleSort("created_at")}
            >
              Joined
            </SortableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && users.length === 0
            ? Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 5 }).map((__, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            : sortedUsers.map((u) => (
                <TableRow key={u.id} className="cursor-pointer" onClick={() => handleOpenUser(u)}>
                  <TableCell>
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
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm capitalize">{u.role}</span>
                      {u.is_app_admin && (
                        <Badge variant="default" className="gap-0.5">
                          <Shield className="h-2.5 w-2.5" />
                          App
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {u.is_active ? (
                      <Badge variant="default">Active</Badge>
                    ) : (
                      <Badge variant="destructive">Suspended</Badge>
                    )}
                  </TableCell>
                  <TableCell>{new Date(u.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenUser(u);
                      }}
                    >
                      Inspect
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
          {!isLoading && users.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-muted-foreground py-8 text-center">
                {search ? `No users match "${search}".` : "No users yet."}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <PaginationBar
        page={page}
        pageSize={pageSize}
        total={total}
        totalPages={totalPages}
        isLoading={isLoading}
        onPrev={() => setPage((p) => Math.max(0, p - 1))}
        onNext={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
      />

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

function SortableHead({
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
    <TableHead>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "hover:text-foreground inline-flex items-center gap-1 text-left transition-colors",
          active && "text-foreground",
        )}
      >
        {children}
        <Icon className={cn("h-3 w-3", !active && "opacity-40")} aria-hidden />
      </button>
    </TableHead>
  );
}

function PaginationBar({
  page,
  pageSize,
  total,
  totalPages,
  isLoading,
  onPrev,
  onNext,
}: {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  isLoading: boolean;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (total === 0) return null;
  const start = page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);
  return (
    <div className="flex items-center justify-between border-t px-4 py-3">
      <span className="text-muted-foreground text-sm">
        {start}–{end} of {total}
      </span>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
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
          onClick={onNext}
          disabled={page >= totalPages - 1 || isLoading}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
