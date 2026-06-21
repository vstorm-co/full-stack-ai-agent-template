"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Search,
} from "lucide-react";

import {
  Avatar,
  AvatarFallback,
  AvatarImage,
  Badge,
  Button,
  type Column,
  DataTable,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui";
import { useAdminConversations } from "@/hooks";
import { ROUTES } from "@/lib/constants";
import { cn, formatDate } from "@/lib/utils";

const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
type SortDir = "asc" | "desc";
type ConvSortKey = "title" | "owner" | "messages" | "created_at" | "updated_at";
type Status = "active" | "archived" | "all";

type Conversation = ReturnType<typeof useAdminConversations>["conversations"][number];

function getInitials(nameOrEmail: string): string {
  return nameOrEmail
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? "")
    .join("");
}

function UserAvatar({
  userId,
  label,
  size = "md",
}: {
  userId: string | null | undefined;
  label: string;
  size?: "sm" | "md";
}) {
  const cls = size === "sm" ? "h-6 w-6 text-[10px]" : "h-7 w-7 text-[11px]";
  return (
    <Avatar className={cls}>
      {userId && <AvatarImage src={`/api/users/avatar/${userId}`} alt={label} />}
      <AvatarFallback>{getInitials(label)}</AvatarFallback>
    </Avatar>
  );
}

function SortButton({
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
        "hover:text-foreground inline-flex items-center gap-1 text-left uppercase transition-colors",
        active && "text-foreground",
      )}
    >
      {children}
      <Icon className={cn("h-3 w-3", !active && "opacity-40")} aria-hidden />
    </button>
  );
}

export default function AdminConversationsPage() {
  const t = useTranslations("admin");
  const { conversations, conversationsTotal, users, isLoading, fetchConversations, fetchUsers } =
    useAdminConversations();

  const [search, setSearch] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("active");
  const [pageSize, setPageSize] = useState<number>(50);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ by: ConvSortKey; dir: SortDir }>({
    by: "updated_at",
    dir: "desc",
  });

  useEffect(() => {
    setPage(0);
  }, [search, selectedUserId, status, pageSize, sort.by, sort.dir]);

  // Load owners list for the dropdown — once on mount, independent of any tab.
  useEffect(() => {
    fetchUsers({ limit: 200, sort_by: "email", sort_dir: "asc" });
  }, [fetchUsers]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchConversations({
        search: search || undefined,
        user_id: selectedUserId || undefined,
        status,
        sort_by: sort.by,
        sort_dir: sort.dir,
        skip: page * pageSize,
        limit: pageSize,
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [search, selectedUserId, status, sort.by, sort.dir, page, pageSize, fetchConversations]);

  const totalPages = Math.max(1, Math.ceil(conversationsTotal / pageSize));

  const toggleSort = (key: ConvSortKey) =>
    setSort((s) =>
      s.by === key ? { by: key, dir: s.dir === "asc" ? "desc" : "asc" } : { by: key, dir: "desc" },
    );

  const userOptions = useMemo(
    () => users.map((u) => ({ id: u.id, email: u.email, fullName: u.full_name })),
    [users],
  );

  const columns: Column<Conversation>[] = useMemo(
    () => [
      {
        key: "title",
        header: (
          <SortButton active={sort.by === "title"} dir={sort.dir} onClick={() => toggleSort("title")}>
            {t("title")}
          </SortButton>
        ),
        cell: (conv) => (
          <span className="text-foreground font-medium">{conv.title || t("untitled")}</span>
        ),
      },
      {
        key: "owner",
        hideBelow: "md",
        header: (
          <SortButton active={sort.by === "owner"} dir={sort.dir} onClick={() => toggleSort("owner")}>
            {t("owner")}
          </SortButton>
        ),
        cell: (conv) =>
          conv.user_email ? (
            <span className="flex items-center gap-2">
              <UserAvatar userId={conv.user_id ?? null} label={conv.user_email} size="sm" />
              <span className="text-muted-foreground truncate">{conv.user_email}</span>
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: "messages",
        align: "right",
        hideBelow: "sm",
        header: (
          <SortButton
            active={sort.by === "messages"}
            dir={sort.dir}
            onClick={() => toggleSort("messages")}
          >
            {t("messages")}
          </SortButton>
        ),
        cell: (conv) => <span className="tabular-nums">{conv.message_count}</span>,
      },
      {
        key: "created_at",
        hideBelow: "md",
        header: (
          <SortButton
            active={sort.by === "created_at"}
            dir={sort.dir}
            onClick={() => toggleSort("created_at")}
          >
            {t("created")}
          </SortButton>
        ),
        cell: (conv) => (
          <span className="text-muted-foreground">
            {formatDate(conv.created_at)}
          </span>
        ),
      },
      {
        key: "status",
        header: t("status"),
        cell: (conv) =>
          conv.is_archived ? (
            <Badge variant="secondary">Archived</Badge>
          ) : (
            <Badge variant="default">Active</Badge>
          ),
      },
      {
        key: "actions",
        align: "right",
        header: "",
        cell: (conv) => (
          <Link
            href={`${ROUTES.CHAT}?id=${conv.id}`}
            className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 font-mono text-[11px] tracking-wider uppercase transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
            {t("view")}
          </Link>
        ),
      },
    ],
    [sort.by, sort.dir, t],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder={t("search")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={status} onValueChange={(v) => setStatus(v as Status)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
            <SelectItem value="all">All</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={selectedUserId ?? "all"}
          onValueChange={(v) => setSelectedUserId(v === "all" ? null : v)}
        >
          <SelectTrigger className="w-[260px]">
            <SelectValue placeholder="All owners" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All owners</SelectItem>
            {userOptions.map((u) => (
              <SelectItem key={u.id} value={u.id}>
                <span className="flex items-center gap-2">
                  <UserAvatar userId={u.id} label={u.fullName || u.email} size="sm" />
                  <span className="truncate">{u.email}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

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

      <div className="text-muted-foreground text-xs">{conversationsTotal} total</div>

      <DataTable<Conversation>
        columns={columns}
        rows={conversations}
        getRowKey={(conv) => conv.id}
        loading={isLoading && conversations.length === 0}
        empty={t("noConversations")}
        skeletonRows={5}
      />

      <PaginationBar
        page={page}
        pageSize={pageSize}
        total={conversationsTotal}
        totalPages={totalPages}
        isLoading={isLoading}
        onPrev={() => setPage((p) => Math.max(0, p - 1))}
        onNext={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
      />
    </div>
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
    <div className="flex items-center justify-between">
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
