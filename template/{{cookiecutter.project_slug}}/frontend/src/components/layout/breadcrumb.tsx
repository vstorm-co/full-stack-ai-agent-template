"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { ROUTES } from "@/lib/constants";

const ROUTE_LABELS: Record<string, string> = {
  [ROUTES.DASHBOARD]: "Dashboard",
  [ROUTES.CHAT]: "Chat",
{%- if cookiecutter.enable_rag %}
  [ROUTES.RAG]: "Knowledge Base",
{%- endif %}
  [ROUTES.PROFILE]: "Profile",
  "/settings": "Settings",
};

export function Breadcrumb() {
  const pathname = usePathname();

  // Extract the route part after locale
  const segments = pathname?.split("/").filter(Boolean) || [];
  const routeSegments = segments.length > 1 ? segments.slice(1) : segments;

  if (routeSegments.length <= 1) return null;

  const crumbs = routeSegments.map((_, i) => {
    const path = "/" + routeSegments.slice(0, i + 1).join("/");
    const segment = routeSegments[i] ?? "";
    const label = ROUTE_LABELS[path] || segment.charAt(0).toUpperCase() + segment.slice(1);
    const isLast = i === routeSegments.length - 1;
    return { path, label, isLast };
  });

  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => (
        <span key={crumb.path} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="text-muted-foreground h-3 w-3" />}
          {crumb.isLast ? (
            <span className="text-foreground font-medium">{crumb.label}</span>
          ) : (
            <Link href={crumb.path} className="text-muted-foreground hover:text-foreground transition-colors">
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
