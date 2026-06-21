import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface SectionCardProps {
  title: string;
  description?: string;
  action?: ReactNode;
  children?: ReactNode;
}

export function SectionCard({ title, description, action, children }: SectionCardProps) {
  return (
    <section className="border-border bg-card rounded-xl border">
      <header className="border-border flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4">
        <div className="min-w-0 flex-1">
          <h2 className="text-foreground text-sm font-semibold">{title}</h2>
          {description && <p className="text-muted-foreground mt-1 text-xs">{description}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      {children && <div className="px-5 py-5">{children}</div>}
    </section>
  );
}

interface SettingsSectionProps {
  title: string;
  description?: string;
  /** Right-aligned action (e.g. "Save changes" button). */
  action?: ReactNode;
  /** Subdued danger styling for destructive sections. */
  danger?: boolean;
  children: ReactNode;
  className?: string;
}

export function SettingsSection({
  title,
  description,
  action,
  danger,
  children,
  className,
}: SettingsSectionProps) {
  return (
    <section
      className={cn(
        "bg-card rounded-2xl border p-5 sm:p-6",
        danger ? "border-destructive/30 bg-destructive/[0.03]" : "border-foreground/10",
        className,
      )}
    >
      <header
        className={cn("flex flex-wrap items-start justify-between gap-3", children ? "mb-5" : "")}
      >
        <div className="min-w-0 flex-1">
          <h2
            className={cn(
              "font-display text-base font-semibold tracking-tight",
              danger ? "text-destructive" : "text-foreground",
            )}
          >
            {title}
          </h2>
          {description && (
            <p className="text-foreground/65 mt-1 text-sm leading-relaxed">{description}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      {children}
    </section>
  );
}

interface SettingsRowProps {
  label: string;
  description?: string;
  /** Form/control on the right. */
  control: ReactNode;
  className?: string;
}

export function SettingsRow({ label, description, control, className }: SettingsRowProps) {
  return (
    <div
      className={cn(
        "border-foreground/8 flex flex-wrap items-start justify-between gap-3 border-t pt-4 first:border-0 first:pt-0",
        className,
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="text-foreground text-sm font-medium">{label}</p>
        {description && (
          <p className="text-foreground/55 mt-0.5 text-xs leading-relaxed">{description}</p>
        )}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}
