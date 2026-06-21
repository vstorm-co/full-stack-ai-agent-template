"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface Column<T> {
  /** Stable key for the column. */
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
  /** Extra classes for the <td>/<th> (e.g. width, hidden on mobile). */
  className?: string;
  /**
   * Hide this column below the given breakpoint so low-priority columns
   * collapse on small screens instead of forcing horizontal scroll.
   * Omit to keep the column always visible.
   */
  hideBelow?: "sm" | "md" | "lg";
}

/** Tailwind classes that hide a column until the given breakpoint. */
const hideBelowClass = {
  sm: "hidden sm:table-cell",
  md: "hidden md:table-cell",
  lg: "hidden lg:table-cell",
} as const;

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  getRowKey: (row: T, index: number) => string;
  loading?: boolean;
  /** Shown when not loading and rows is empty. */
  empty?: ReactNode;
  onRowClick?: (row: T) => void;
  /** Number of skeleton rows while loading. */
  skeletonRows?: number;
  className?: string;
}

const alignClass = { left: "text-left", right: "text-right", center: "text-center" } as const;

/** Flat, theme-aware table with built-in loading + empty states. */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  loading,
  empty,
  onRowClick,
  skeletonRows = 6,
  className,
}: DataTableProps<T>) {
  const showEmpty = !loading && rows && rows.length === 0;

  return (
    <div className={cn("border-border bg-card overflow-hidden rounded-xl border", className)}>
      <div className="scrollbar-thin overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-border border-b">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "text-muted-foreground px-4 py-2.5 font-mono text-[11px] font-medium tracking-wider uppercase",
                    alignClass[col.align ?? "left"],
                    col.hideBelow && hideBelowClass[col.hideBelow],
                    col.className,
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading &&
              Array.from({ length: skeletonRows }).map((_, i) => (
                <tr key={`sk-${i}`} className="border-border/60 border-b last:border-0">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-4 py-3",
                        col.hideBelow && hideBelowClass[col.hideBelow],
                        col.className,
                      )}
                    >
                      <div className="bg-foreground/10 h-4 w-2/3 animate-pulse rounded" />
                    </td>
                  ))}
                </tr>
              ))}

            {!loading &&
              rows?.map((row, i) => (
                <tr
                  key={getRowKey(row, i)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    "border-border/60 border-b transition-colors last:border-0",
                    onRowClick && "hover:bg-accent cursor-pointer",
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "text-foreground px-4 py-3",
                        alignClass[col.align ?? "left"],
                        col.hideBelow && hideBelowClass[col.hideBelow],
                        col.className,
                      )}
                    >
                      {col.cell(row)}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {showEmpty && (
        <div className="text-muted-foreground px-4 py-12 text-center text-sm">
          {empty ?? "No results."}
        </div>
      )}
    </div>
  );
}
