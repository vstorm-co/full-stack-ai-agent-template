{% raw %}"use client";

import { useState } from "react";
import { notFound } from "next/navigation";
import { Sparkles, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/dashboard/page-header";
import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState } from "@/components/states";
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Button,
  ConfirmDialog,
  FormField,
  IconButton,
  Input,
  SectionHeading,
} from "@/components/ui";

/**
 * Dev-only component gallery — a lightweight stand-in for Storybook that keeps
 * the design system honest. Renders the core primitives in one place so visual
 * regressions are easy to spot. Hidden in production builds.
 */
export default function ComponentGalleryPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <Gallery />;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-border bg-card rounded-xl border p-5">
      <SectionHeading eyebrow="Primitive" title={title} className="mb-4" />
      <div className="flex flex-wrap items-start gap-3">{children}</div>
    </section>
  );
}

function Gallery() {
  const [confirmOpen, setConfirmOpen] = useState(false);

  return (
    <div className="space-y-6 pb-8">
      <PageHeader eyebrow="Dev" title="Component gallery" description="Core design-system primitives, in one place." />

      <Section title="Button variants">
        {(["default", "secondary", "outline", "ghost", "destructive", "link"] as const).map((v) => (
          <Button key={v} variant={v}>
            {v}
          </Button>
        ))}
      </Section>

      <Section title="Button sizes">
        <Button size="sm">sm</Button>
        <Button size="default">default</Button>
        <Button size="lg">lg</Button>
        <IconButton aria-label="Sparkles" size="icon-sm">
          <Sparkles />
        </IconButton>
        <IconButton aria-label="Delete" size="icon">
          <Trash2 />
        </IconButton>
      </Section>

      <Section title="Badges">
        {(["default", "secondary", "outline", "destructive"] as const).map((v) => (
          <Badge key={v} variant={v}>
            {v}
          </Badge>
        ))}
      </Section>

      <Section title="Alerts">
        <div className="w-full space-y-2">
          {(["default", "warning", "destructive", "success"] as const).map((v) => (
            <Alert key={v} variant={v}>
              <AlertTitle>{v} alert</AlertTitle>
              <AlertDescription>Something worth the user&apos;s attention.</AlertDescription>
            </Alert>
          ))}
        </div>
      </Section>

      <Section title="FormField">
        <div className="w-full max-w-sm space-y-4">
          <FormField label="Display name" htmlFor="g-name" description="Visible to teammates.">
            <Input id="g-name" placeholder="Ada Lovelace" />
          </FormField>
          <FormField label="Email" htmlFor="g-email" error="That email is already taken." required>
            <Input id="g-email" type="email" defaultValue="taken@example.com" />
          </FormField>
        </div>
      </Section>

      <Section title="StatCard">
        <div className="grid w-full gap-3 sm:grid-cols-3">
          <StatCard label="Credits" value="1,240" delta={12.5} deltaLabel="vs prior 7d" />
          <StatCard label="Conversations" value="38" footer="across all chats" />
          <StatCard label="Knowledge base" value="0" unit="vectors" />
        </div>
      </Section>

      <Section title="EmptyState">
        <div className="w-full">
          <EmptyState
            icon={Sparkles}
            title="Nothing here yet"
            description="Create your first item to get started."
            cta={{ label: "Create", onClick: () => {} }}
          />
        </div>
      </Section>

      <Section title="ConfirmDialog">
        <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
          Delete something…
        </Button>
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="Delete this resource?"
          description="This action cannot be undone."
          destructive
          confirmText="DELETE"
          confirmLabel="Delete"
          onConfirm={() => setConfirmOpen(false)}
        />
      </Section>
    </div>
  );
}
{% endraw %}
