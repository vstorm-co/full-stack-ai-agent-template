import { Header, Sidebar } from "@/components/layout";
import { AuthGuard } from "@/components/layout/auth-guard";
import { CommandPalette } from "@/components/layout/command-palette";
import { MobileTabBar } from "@/components/layout/mobile-tab-bar";
import { PageTransition } from "@/components/layout/page-transition";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen flex-col">
        <Header />
        <Sidebar />
        <main
          id="main"
          tabIndex={-1}
          className="flex min-h-0 flex-1 flex-col overflow-auto p-3 pb-20 sm:p-6 sm:pb-20 lg:pb-6"
        >
          <PageTransition>{children}</PageTransition>
        </main>
        <MobileTabBar />
        <CommandPalette />
      </div>
    </AuthGuard>
  );
}
