"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Database,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Plus,
  Search,
  Settings,
  Star,
  UserCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { useAuth } from "@/hooks";
import { apiClient } from "@/lib/api-client";
import { ROUTES } from "@/lib/constants";

interface ConversationItem {
  id: string;
  title: string | null;
  updated_at?: string | null;
}

export function CommandPalette() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [conversations, setConversations] = useState<ConversationItem[]>([]);

  // Global ⌘K / Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Fetch recent conversations once when opened
  useEffect(() => {
    if (!open) return;
    if (conversations.length > 0) return;
    apiClient
      .get<{ items: ConversationItem[] }>("/conversations?limit=10")
      .then((d) => setConversations(d.items))
      .catch(() => setConversations([]));
  }, [open, conversations.length]);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Command palette"
      shouldFilter
      overlayClassName="bg-background/50 fixed inset-0 z-[60] backdrop-blur-sm"
      contentClassName="border-foreground/15 bg-card text-foreground fixed left-1/2 top-[12vh] z-[61] w-[min(92vw,640px)] -translate-x-1/2 overflow-hidden rounded-2xl border shadow-2xl"
    >
      <div className="border-foreground/10 flex items-center gap-3 border-b px-4 py-3">
        <Search className="text-foreground/45 h-4 w-4" />
        <Command.Input
          autoFocus
          value={search}
          onValueChange={setSearch}
          placeholder="Search or jump to…"
          className="text-foreground placeholder:text-foreground/45 flex-1 bg-transparent text-sm outline-none"
        />
        <kbd className="border-foreground/15 text-foreground/55 hidden rounded-md border px-1.5 py-0.5 font-mono text-[10px] sm:inline-block">
          ESC
        </kbd>
      </div>

      <Command.List className="max-h-[60vh] overflow-y-auto px-2 py-2">
        <Command.Empty className="text-foreground/55 px-4 py-10 text-center text-sm">
          No matches.
        </Command.Empty>

        <Group heading="Quick actions">
          <PaletteItem
            icon={Plus}
            label="Start new chat"
            onSelect={() => go(ROUTES.CHAT)}
            shortcut="⌘N"
          />
          <PaletteItem
            icon={Database}
            label="Upload to knowledge base"
            onSelect={() => go(ROUTES.RAG)}
          />
        </Group>

        {conversations.length > 0 && (
          <Group heading="Recent conversations">
            {conversations.slice(0, 8).map((c) => (
              <PaletteItem
                key={c.id}
                icon={MessageSquare}
                label={c.title?.trim() || "Untitled conversation"}
                onSelect={() => go(`${ROUTES.CHAT}?id=${c.id}`)}
              />
            ))}
          </Group>
        )}

        <Group heading="Navigate">
          <PaletteItem
            icon={LayoutDashboard}
            label="Dashboard"
            onSelect={() => go(ROUTES.DASHBOARD)}
          />
          <PaletteItem icon={MessageSquare} label="Chat" onSelect={() => go(ROUTES.CHAT)} />
          <PaletteItem icon={UserCircle} label="Profile" onSelect={() => go(ROUTES.PROFILE)} />
          <PaletteItem icon={Settings} label="Settings" onSelect={() => go(ROUTES.SETTINGS)} />
          <PaletteItem
            icon={BookOpen}
            label="API documentation"
            onSelect={() => {
              setOpen(false);
              window.open("/docs", "_blank");
            }}
          />
        </Group>
        {user?.role === "admin" && (
          <Group heading="Admin">
            <PaletteItem
              icon={Star}
              label="Response ratings"
              onSelect={() => go(ROUTES.ADMIN_RATINGS)}
            />
            <PaletteItem
              icon={Activity}
              label="All conversations"
              onSelect={() => go(ROUTES.ADMIN_CONVERSATIONS)}
            />
          </Group>
        )}

        <Group heading="Account">
          <PaletteItem
            icon={LogOut}
            label="Sign out"
            onSelect={() => {
              setOpen(false);
              logout();
            }}
          />
        </Group>
      </Command.List>

      <div className="border-foreground/10 text-foreground/45 flex items-center justify-between border-t px-4 py-2 font-mono text-[10px] tracking-wider uppercase">
        <span className="inline-flex items-center gap-1.5">
          <kbd className="border-foreground/15 rounded border px-1 py-0.5">↑↓</kbd>
          Navigate
        </span>
        <span className="inline-flex items-center gap-1.5">
          <kbd className="border-foreground/15 rounded border px-1 py-0.5">↵</kbd>
          Open
        </span>
      </div>
    </Command.Dialog>
  );
}

function Group({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <Command.Group
      heading={heading}
      className="[&_[cmdk-group-heading]]:text-foreground/45 [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:uppercase"
    >
      {children}
    </Command.Group>
  );
}

function PaletteItem({
  icon: Icon,
  label,
  onSelect,
  shortcut,
}: {
  icon: LucideIcon;
  label: string;
  onSelect: () => void;
  shortcut?: string;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="text-foreground/85 hover:bg-foreground/5 data-[selected=true]:bg-foreground/8 data-[selected=true]:text-foreground flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
    >
      <Icon className="h-4 w-4 shrink-0 opacity-70" />
      <span className="flex-1 truncate">{label}</span>
      {shortcut ? (
        <kbd className="border-foreground/15 text-foreground/55 rounded border px-1.5 py-0.5 font-mono text-[10px]">
          {shortcut}
        </kbd>
      ) : (
        <ArrowRight className="text-foreground/30 h-3.5 w-3.5 opacity-0 transition-opacity data-[selected=true]:opacity-100" />
      )}
    </Command.Item>
  );
}
