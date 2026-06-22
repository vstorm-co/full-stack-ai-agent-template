"use client";

import Link from "next/link";
{%- if cookiecutter.enable_i18n %}
import { useTranslations } from "next-intl";
{%- endif %}
import {
  Activity,
  Building2,
  ChevronDown,
  CreditCard,
  Database,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Receipt,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Star,
  Users,
  UserCircle,
  type LucideIcon,
} from "lucide-react";

{%- if cookiecutter.enable_i18n %}
import { LanguageSwitcherIcon } from "@/components/language-switcher";
{%- endif %}
import { ThemeToggle } from "@/components/theme";
{%- if cookiecutter.enable_teams %}
import { OrgSwitcher } from "@/components/teams";
{%- endif %}
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui";
import { useAuth } from "@/hooks";
import { useActiveRoute } from "@/lib/active-route";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { cn, isAppAdmin } from "@/lib/utils";
import { useAuthStore, useSidebarStore } from "@/stores";

type NavLeaf = { labelKey: string; href: string; icon: LucideIcon; descKey?: string };
type NavEntry =
  | { kind: "link"; labelKey: string; href: string; icon: LucideIcon; adminOnly?: boolean }
  | { kind: "menu"; labelKey: string; icon: LucideIcon; adminOnly?: boolean; items: NavLeaf[] };

const NAV: NavEntry[] = [
  { kind: "link", labelKey: "dashboard", href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { kind: "link", labelKey: "chat", href: ROUTES.CHAT, icon: MessageSquare },
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  {
    kind: "menu",
    labelKey: "knowledge",
    icon: Database,
    items: [
      { labelKey: "knowledgeBases", href: ROUTES.KB, icon: Database, descKey: "knowledgeBasesDesc" },
      { labelKey: "ragSearch", href: ROUTES.RAG, icon: Search, descKey: "ragSearchDesc" },
    ],
  },
{%- endif %}
{%- if cookiecutter.enable_teams %}
  {
    kind: "menu",
    labelKey: "team",
    icon: Building2,
    items: [
      { labelKey: "organizations", href: ROUTES.ORGS, icon: Building2, descKey: "organizationsDesc" },
    ],
  },
{%- endif %}
{%- if cookiecutter.enable_billing %}
  { kind: "link", labelKey: "billing", href: ROUTES.BILLING, icon: CreditCard },
{%- endif %}
  {
    kind: "menu",
    labelKey: "admin",
    icon: ShieldCheck,
    adminOnly: true,
    items: [
      { labelKey: "overview", href: ROUTES.ADMIN, icon: LayoutDashboard },
      { labelKey: "users", href: ROUTES.ADMIN_USERS, icon: Users },
      { labelKey: "conversations", href: ROUTES.ADMIN_CONVERSATIONS, icon: MessageSquare },
      { labelKey: "ratings", href: ROUTES.ADMIN_RATINGS, icon: Star },
{%- if cookiecutter.enable_billing %}
      { labelKey: "stripeEvents", href: ROUTES.ADMIN_STRIPE_EVENTS, icon: Receipt },
{%- endif %}
      { labelKey: "systemHealth", href: ROUTES.ADMIN_SYSTEM, icon: Activity },
    ],
  },
];

function NavMenu({ entry }: { entry: Extract<NavEntry, { kind: "menu" }> }) {
  const isActive = useActiveRoute();
{%- if cookiecutter.enable_i18n %}
  const t = useTranslations("nav");
{%- endif %}
  const active = entry.items.some((i) => isActive(i.href));
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors outline-none",
            active
              ? "bg-foreground/5 text-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-foreground/5",
          )}
        >
          <entry.icon className="h-3.5 w-3.5" />
{%- if cookiecutter.enable_i18n %}
          {t(entry.labelKey)}
{%- else %}
          {entry.labelKey}
{%- endif %}
          <ChevronDown className="h-3 w-3 opacity-60" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-60">
        {entry.items.map((item) => (
          <DropdownMenuItem key={item.href} asChild>
            <Link href={item.href} className="flex items-start gap-2.5">
              <item.icon className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
              <span className="flex flex-col">
{%- if cookiecutter.enable_i18n %}
                <span className="text-sm font-medium">{t(item.labelKey)}</span>
                {item.descKey && (
                  <span className="text-muted-foreground text-xs">{t(item.descKey)}</span>
                )}
{%- else %}
                <span className="text-sm font-medium">{item.labelKey}</span>
{%- endif %}
              </span>
            </Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const avatarVersion = useAuthStore((s) => s.avatarVersion);
  const { toggle } = useSidebarStore();
  const isActive = useActiveRoute();
{%- if cookiecutter.enable_i18n %}
  const t = useTranslations("nav");
  const tc = useTranslations("common");
{%- endif %}
  const isAdmin = isAppAdmin(user);

  const openSearch = () => window.dispatchEvent(new CustomEvent("command-palette:open"));

  return (
    <header className="bg-background/95 supports-[backdrop-filter]:bg-background/70 sticky top-0 z-40 w-full border-b backdrop-blur">
      <div className="flex h-14 items-center justify-between gap-2 px-3 sm:px-6">
        <div className="flex items-center gap-1 sm:gap-3">
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0 lg:hidden" onClick={toggle}>
            <Menu className="h-5 w-5" />
{%- if cookiecutter.enable_i18n %}
            <span className="sr-only">{t("toggleMenu")}</span>
{%- else %}
            <span className="sr-only">Toggle menu</span>
{%- endif %}
          </Button>

          <Link
            href={ROUTES.DASHBOARD}
            className="flex items-center gap-2 pr-1 text-sm font-bold tracking-tight sm:text-base"
          >
            <span
              aria-hidden
              className="bg-foreground text-background inline-flex h-6 w-6 items-center justify-center rounded-md"
            >
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <span className="hidden sm:inline">{APP_NAME}</span>
          </Link>

          <nav className="hidden items-center gap-0.5 lg:flex">
            {NAV.filter((e) => !e.adminOnly || isAdmin).map((entry) =>
              entry.kind === "link" ? (
                <Link
                  key={entry.href}
                  href={entry.href}
                  aria-current={isActive(entry.href) ? "page" : undefined}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive(entry.href)
                      ? "bg-foreground/5 text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-foreground/5",
                  )}
                >
                  <entry.icon className="h-3.5 w-3.5" />
{%- if cookiecutter.enable_i18n %}
                  {t(entry.labelKey)}
{%- else %}
                  {entry.labelKey}
{%- endif %}
                </Link>
              ) : (
                <NavMenu key={entry.labelKey} entry={entry} />
              ),
            )}
          </nav>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={openSearch}
{%- if cookiecutter.enable_i18n %}
            aria-label={tc("search")}
            title={`${tc("search")} (⌘K)`}
{%- else %}
            aria-label="Search"
            title="Search (⌘K)"
{%- endif %}
            className="text-muted-foreground hover:text-foreground hover:bg-accent focus-visible:ring-ring inline-flex h-9 w-9 items-center justify-center rounded-lg transition-colors outline-none focus-visible:ring-1"
          >
            <Search className="h-[1.1rem] w-[1.1rem]" />
{%- if cookiecutter.enable_i18n %}
            <span className="sr-only">{tc("search")}</span>
{%- else %}
            <span className="sr-only">Search</span>
{%- endif %}
          </button>

{%- if cookiecutter.enable_i18n %}
          <div className="ml-0.5 hidden items-center sm:flex">
            <LanguageSwitcherIcon />
          </div>
{%- endif %}
          <ThemeToggle className="text-muted-foreground hover:text-foreground hover:bg-accent h-9 w-9 rounded-lg [&_svg]:size-[1.1rem]" />

          {isAuthenticated && <div className="bg-border mx-1.5 hidden h-5 w-px sm:block" />}

{%- if cookiecutter.enable_teams %}
          {isAuthenticated && <OrgSwitcher />}
{%- endif %}

          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="hover:bg-accent focus-visible:ring-ring ml-0.5 flex items-center gap-1.5 rounded-full p-0.5 pr-2 transition-colors outline-none focus-visible:ring-1">
                  <Avatar className="h-7 w-7">
                    {user?.avatar_url && (
                      <AvatarImage src={`/api/users/avatar/${user.id}?v=${avatarVersion}`} alt={user.email} />
                    )}
                    <AvatarFallback className="bg-foreground text-background text-[10px] font-semibold">
                      {user?.email?.substring(0, 2).toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                  <ChevronDown className="text-muted-foreground h-3 w-3" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="flex flex-col">
                  <span className="truncate text-sm font-semibold">
                    {user?.full_name || user?.email?.split("@")[0]}
                  </span>
                  <span className="text-muted-foreground truncate text-xs font-normal">
                    {user?.email}
                  </span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href={ROUTES.PROFILE}>
                    <UserCircle className="mr-2 h-4 w-4" />
{%- if cookiecutter.enable_i18n %}
                    {t("profile")}
{%- else %}
                    Profile
{%- endif %}
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href={ROUTES.SETTINGS}>
                    <Settings className="mr-2 h-4 w-4" />
{%- if cookiecutter.enable_i18n %}
                    {t("settings")}
{%- else %}
                    Settings
{%- endif %}
                  </Link>
                </DropdownMenuItem>
{%- if cookiecutter.enable_billing %}
                <DropdownMenuItem asChild>
                  <Link href={ROUTES.BILLING}>
                    <CreditCard className="mr-2 h-4 w-4" />
{%- if cookiecutter.enable_i18n %}
                    {t("billing")}
{%- else %}
                    Billing
{%- endif %}
                  </Link>
                </DropdownMenuItem>
{%- endif %}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
                  <LogOut className="mr-2 h-4 w-4" />
{%- if cookiecutter.enable_i18n %}
                  {t("logout")}
{%- else %}
                  Logout
{%- endif %}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="ml-1 flex items-center gap-1.5">
              <Button variant="ghost" size="sm" asChild className="h-9 rounded-lg">
{%- if cookiecutter.enable_i18n %}
                <Link href={ROUTES.LOGIN}>{t("login")}</Link>
{%- else %}
                <Link href={ROUTES.LOGIN}>Login</Link>
{%- endif %}
              </Button>
              <Button size="sm" asChild className="h-9 rounded-lg">
{%- if cookiecutter.enable_i18n %}
                <Link href={ROUTES.REGISTER}>{t("register")}</Link>
{%- else %}
                <Link href={ROUTES.REGISTER}>Register</Link>
{%- endif %}
              </Button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
