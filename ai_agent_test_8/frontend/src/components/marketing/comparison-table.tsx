import { Check, Minus, X, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type Cell = "yes" | "partial" | "no";

interface ComparisonTableProps {
  /** Product name — the highlighted column. */
  brand: string;
  /** Names of the two alternatives compared against. */
  alternatives: [string, string];
  rows: { feature: string; cells: [Cell, Cell, Cell] }[];
}

const ICON: Record<Cell, LucideIcon> = { yes: Check, partial: Minus, no: X };
const ICON_CLASS: Record<Cell, string> = {
  yes: "text-brand",
  partial: "text-foreground/35",
  no: "text-foreground/25",
};

function CellMark({ value }: { value: Cell }) {
  const Icon = ICON[value];
  return (
    <span className="flex justify-center">
      <Icon className={cn("h-5 w-5", ICON_CLASS[value])} strokeWidth={2.5} />
    </span>
  );
}

export function ComparisonTable({ brand, alternatives, rows }: ComparisonTableProps) {
  return (
    <>
      <div className="mb-14 max-w-2xl">
        <div className="mb-5">
          <span className="eyebrow-badge">Why teams choose us</span>
        </div>
        <h2 className="text-display-lg text-foreground [&_em]:font-accent [&_em]:font-normal [&_em]:italic">
          The difference is the <em>grounding.</em>
        </h2>
      </div>

      <div className="border-foreground/12 bg-card overflow-hidden rounded-2xl border">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left">
            <thead>
              <tr className="border-foreground/10 border-b">
                <th className="text-foreground/55 eyebrow px-6 py-5 font-medium">Capability</th>
                <th className="px-6 py-5 text-center">
                  <span className="bg-brand text-brand-foreground font-display inline-flex rounded-full px-3 py-1 text-sm font-bold">
                    {brand}
                  </span>
                </th>
                {alternatives.map((alt) => (
                  <th
                    key={alt}
                    className="text-foreground/60 px-6 py-5 text-center text-sm font-semibold"
                  >
                    {alt}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={row.feature}
                  className={cn(i < rows.length - 1 && "border-foreground/[0.07] border-b")}
                >
                  <td className="text-foreground px-6 py-4 text-sm font-medium">{row.feature}</td>
                  <td className="bg-brand/[0.05] px-6 py-4">
                    <CellMark value={row.cells[0]} />
                  </td>
                  <td className="px-6 py-4">
                    <CellMark value={row.cells[1]} />
                  </td>
                  <td className="px-6 py-4">
                    <CellMark value={row.cells[2]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
