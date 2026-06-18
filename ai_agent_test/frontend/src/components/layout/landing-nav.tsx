"use client";

import Link from "next/link";
import { useAuth } from "@/hooks";
import { ThemeToggle } from "@/components/theme";
import { LanguageSwitcherCompact } from "@/components/language-switcher";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { LogOut, User } from "lucide-react";

interface LandingNavProps {
  signInLabel: string;
  getStartedLabel: string;
  dashboardLabel: string;
}

export function LandingNav({ signInLabel, getStartedLabel, dashboardLabel }: LandingNavProps) {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <div className="fixed top-0 right-0 left-0 z-50 flex justify-center px-4 pt-4">
      <nav className="navbar-beam relative flex h-12 w-full max-w-3xl items-center justify-between rounded-full px-4 sm:px-6">
        <Link href={ROUTES.HOME} className="text-foreground text-sm font-bold tracking-tight">
          {APP_NAME}
        </Link>

        <div className="flex items-center gap-1.5 sm:gap-2">
          <Link
            href={ROUTES.PRICING}
            className="text-muted-foreground hover:text-foreground hidden rounded-full px-3 py-1.5 text-xs font-medium transition-colors sm:inline-flex"
          >
            Pricing
          </Link>
          <LanguageSwitcherCompact />
          <ThemeToggle />
          {isAuthenticated ? (
            <>
              <Link
                href={ROUTES.DASHBOARD}
                className="bg-brand text-foreground hover:bg-brand-hover rounded-full px-4 py-1.5 text-xs font-semibold transition-colors"
              >
                {dashboardLabel}
              </Link>
              <span className="text-muted-foreground hidden items-center gap-1 text-xs sm:flex">
                <User className="h-3 w-3" />
                {user?.email?.split("@")[0]}
              </span>
              <button
                onClick={logout}
                className="text-muted-foreground hover:text-foreground rounded-full p-1.5 transition-colors"
                title="Logout"
              >
                <LogOut className="h-3.5 w-3.5" />
              </button>
            </>
          ) : (
            <>
              <Link
                href={ROUTES.LOGIN}
                className="text-muted-foreground hover:text-foreground rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
              >
                {signInLabel}
              </Link>
              <Link
                href={ROUTES.REGISTER}
                className="bg-brand text-foreground hover:bg-brand-hover hidden rounded-full px-4 py-1.5 text-xs font-semibold transition-colors sm:inline-flex"
              >
                {getStartedLabel}
              </Link>
            </>
          )}
        </div>
      </nav>
    </div>
  );
}
