import type { ComponentProps } from "react";
import { AlertTriangle, Info, Lightbulb } from "lucide-react";

type CalloutVariant = "info" | "tip" | "warn";

const CALLOUT_STYLES: Record<CalloutVariant, { icon: typeof Info; classes: string }> = {
  info: {
    icon: Info,
    classes: "border-foreground/15 bg-foreground/[0.04] text-foreground/85",
  },
  tip: {
    icon: Lightbulb,
    classes: "border-brand/40 bg-brand/[0.06] text-foreground",
  },
  warn: {
    icon: AlertTriangle,
    classes: "border-yellow-500/30 bg-yellow-500/[0.06] text-foreground",
  },
};

function Callout({
  variant = "info",
  children,
}: {
  variant?: CalloutVariant;
  children: React.ReactNode;
}) {
  const { icon: Icon, classes } = CALLOUT_STYLES[variant];
  return (
    <div className={`my-7 flex gap-3 rounded-2xl border p-5 ${classes}`}>
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="min-w-0 flex-1 [&>:first-child]:mt-0 [&>:last-child]:mb-0">{children}</div>
    </div>
  );
}

function Anchor(props: ComponentProps<"a">) {
  const { href = "" } = props;
  const isExternal = /^https?:\/\//.test(href);
  if (isExternal) {
    return <a {...props} target="_blank" rel="noopener noreferrer" />;
  }
  return <a {...props} />;
}

export const blogMdxComponents = {
  Callout,
  a: Anchor,
};
