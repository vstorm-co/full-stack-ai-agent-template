"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Calendar, Check, Cog, Database, Plug } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Spinner,
  Switch,
} from "@/components/ui";
import { BrandIcon } from "@/components/marketing/brand-icon";
import type { ConnectorInfo, SyncSourceCreate } from "@/lib/rag-api";
import { cn } from "@/lib/utils";

interface SyncSourceWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connectors: ConnectorInfo[];
  collections: { name: string }[];
  defaultCollection?: string;
  onSubmit: (data: SyncSourceCreate) => Promise<void> | void;
  submitting?: boolean;
}

type Step = "connector" | "configure" | "schedule";

const STEPS: { id: Step; label: string; icon: typeof Plug }[] = [
  { id: "connector", label: "Pick source", icon: Plug },
  { id: "configure", label: "Configure", icon: Cog },
  { id: "schedule", label: "Schedule", icon: Calendar },
];

const SYNC_MODES = [
  { value: "full", label: "Full", description: "Reprocess everything every run" },
  { value: "new_only", label: "New only", description: "Only ingest files added since last sync" },
  { value: "update_only", label: "Update only", description: "Re-ingest files that changed" },
];

const SCHEDULE_PRESETS = [
  { value: 0, label: "Manual" },
  { value: 60, label: "Every hour" },
  { value: 360, label: "Every 6h" },
  { value: 1440, label: "Daily" },
];

const CONNECTOR_BRAND: Record<string, "gdrive" | "github" | "notion" | "slack" | "dropbox"> = {
  google_drive: "gdrive",
  gdrive: "gdrive",
  drive: "gdrive",
  github: "github",
  notion: "notion",
  slack: "slack",
  dropbox: "dropbox",
};

export function SyncSourceWizard({
  open,
  onOpenChange,
  connectors,
  collections,
  defaultCollection,
  onSubmit,
  submitting,
}: SyncSourceWizardProps) {
  const [step, setStep] = useState<Step>("connector");
  const [form, setForm] = useState<SyncSourceCreate>({
    name: "",
    connector_type: "",
    collection_name: defaultCollection ?? "",
    config: {},
    sync_mode: "full",
    schedule_minutes: null,
  });

  // Reset state when dialog opens.
  useEffect(() => {
    if (open) {
      setStep("connector");
      setForm({
        name: "",
        connector_type: "",
        collection_name: defaultCollection ?? "",
        config: {},
        sync_mode: "full",
        schedule_minutes: null,
      });
    }
  }, [open, defaultCollection]);

  const selectedConnector = useMemo(
    () => connectors.find((c) => c.type === form.connector_type),
    [connectors, form.connector_type],
  );

  const stepIdx = STEPS.findIndex((s) => s.id === step);
  const enabledConnectors = connectors.filter((c) => c.enabled);

  const canAdvance = (() => {
    if (step === "connector") return Boolean(form.connector_type) && Boolean(form.name.trim());
    if (step === "configure") {
      if (!selectedConnector) return false;
      const required = Object.entries(selectedConnector.config_schema).filter(
        ([, f]) => f.required,
      );
      return required.every(([key]) => {
        const v = form.config[key];
        return v !== undefined && v !== null && v !== "";
      });
    }
    if (step === "schedule") return Boolean(form.collection_name);
    return false;
  })();

  const handleNext = () => {
    if (!canAdvance) return;
    if (step === "connector") setStep("configure");
    else if (step === "configure") setStep("schedule");
    else if (step === "schedule") onSubmit(form);
  };

  const handleBack = () => {
    if (step === "configure") setStep("connector");
    else if (step === "schedule") setStep("configure");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-2xl">
        <DialogHeader className="border-foreground/10 border-b px-6 py-4">
          <DialogTitle className="font-display text-base font-semibold">
            Add sync source
          </DialogTitle>
          <ol className="mt-3 flex items-center gap-2">
            {STEPS.map((s, i) => {
              const done = i < stepIdx;
              const active = s.id === step;
              return (
                <li key={s.id} className="flex flex-1 items-center gap-2">
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full transition-colors",
                      done && "bg-foreground text-background",
                      active && "bg-brand text-brand-foreground",
                      !done && !active && "bg-foreground/8 text-foreground/55",
                    )}
                  >
                    {done ? <Check className="h-3 w-3" /> : <s.icon className="h-3 w-3" />}
                  </div>
                  <span
                    className={cn(
                      "hidden font-mono text-[10px] tracking-wider uppercase sm:inline",
                      active || done ? "text-foreground" : "text-foreground/45",
                    )}
                  >
                    {s.label}
                  </span>
                  {i < STEPS.length - 1 && (
                    <span
                      className={cn(
                        "h-px flex-1",
                        i < stepIdx ? "bg-foreground" : "bg-foreground/15",
                      )}
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </DialogHeader>

        <div className="max-h-[60vh] scrollbar-thin overflow-y-auto px-6 py-5">
          {step === "connector" && (
            <ConnectorStep connectors={enabledConnectors} form={form} setForm={setForm} />
          )}
          {step === "configure" && selectedConnector && (
            <ConfigureStep connector={selectedConnector} form={form} setForm={setForm} />
          )}
          {step === "schedule" && (
            <ScheduleStep collections={collections} form={form} setForm={setForm} />
          )}
        </div>

        <div className="border-foreground/10 flex items-center justify-between border-t px-6 py-4">
          {step !== "connector" ? (
            <button
              type="button"
              onClick={handleBack}
              disabled={submitting}
              className="text-foreground/65 hover:text-foreground inline-flex items-center gap-1.5 text-sm font-medium"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="text-foreground/65 hover:text-foreground text-sm font-medium"
            >
              Cancel
            </button>
          )}

          <button
            type="button"
            onClick={handleNext}
            disabled={!canAdvance || submitting}
            className="bg-foreground text-background hover:bg-foreground/90 disabled:bg-foreground/30 inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed"
          >
            {submitting && step === "schedule" ? (
              <>
                <Spinner className="h-3.5 w-3.5" />
                Creating…
              </>
            ) : step === "schedule" ? (
              <>
                Create source
                <Check className="h-4 w-4" />
              </>
            ) : (
              <>
                Continue
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ConnectorStep({
  connectors,
  form,
  setForm,
}: {
  connectors: ConnectorInfo[];
  form: SyncSourceCreate;
  setForm: React.Dispatch<React.SetStateAction<SyncSourceCreate>>;
}) {
  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <Label
          htmlFor="source-name"
          className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
        >
          Source name
        </Label>
        <Input
          id="source-name"
          placeholder="e.g. Engineering docs (S3)"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          className="h-10 rounded-xl"
        />
      </div>

      <div className="space-y-2">
        <Label className="text-foreground/80 text-xs font-medium tracking-wider uppercase">
          Connector
        </Label>
        {connectors.length === 0 ? (
          <p className="border-foreground/10 bg-foreground/[0.03] text-foreground/65 rounded-xl border px-4 py-3 text-sm">
            No connectors enabled. Configure a connector in the backend first.
          </p>
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {connectors.map((conn) => {
              const isSelected = form.connector_type === conn.type;
              const brand = CONNECTOR_BRAND[conn.type];
              return (
                <button
                  key={conn.type}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, connector_type: conn.type, config: {} }))}
                  className={cn(
                    "flex items-center gap-3 rounded-xl border p-3.5 text-left transition-colors",
                    isSelected
                      ? "border-brand bg-brand/[0.06]"
                      : "border-foreground/10 bg-card hover:border-foreground/30",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
                      isSelected
                        ? "bg-brand text-brand-foreground"
                        : "bg-foreground/8 text-foreground",
                    )}
                  >
                    {brand ? (
                      <BrandIcon name={brand} className="h-4 w-4" aria-hidden />
                    ) : (
                      <Database className="h-4 w-4" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground text-sm font-semibold">{conn.name}</p>
                    <p className="text-foreground/55 truncate font-mono text-[10px] tracking-wider uppercase">
                      {conn.type}
                    </p>
                  </div>
                  {isSelected && <Check className="text-brand h-4 w-4 shrink-0" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ConfigureStep({
  connector,
  form,
  setForm,
}: {
  connector: ConnectorInfo;
  form: SyncSourceCreate;
  setForm: React.Dispatch<React.SetStateAction<SyncSourceCreate>>;
}) {
  const fields = Object.entries(connector.config_schema);

  if (fields.length === 0) {
    return (
      <div className="border-foreground/10 bg-foreground/[0.03] rounded-xl border p-5 text-center">
        <Cog className="text-foreground/45 mx-auto h-6 w-6" />
        <p className="text-foreground/70 mt-3 text-sm">
          No additional configuration needed for{" "}
          <span className="text-foreground font-medium">{connector.name}</span>.
        </p>
        <p className="text-foreground/50 mt-1 text-xs">Continue to schedule the source.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-foreground/65 text-sm">
        Configure {connector.name}. Required fields are marked with{" "}
        <span className="text-destructive">*</span>.
      </p>
      {fields.map(([key, field]) => (
        <div key={key} className="space-y-1.5">
          <Label
            htmlFor={`cfg-${key}`}
            className="text-foreground/80 text-xs font-medium tracking-wider uppercase"
          >
            {field.label}
            {field.required && <span className="text-destructive ml-0.5">*</span>}
          </Label>
          {field.type === "boolean" ? (
            <div className="flex items-center gap-3 py-1">
              <Switch
                id={`cfg-${key}`}
                checked={!!form.config[key]}
                onCheckedChange={(val) =>
                  setForm((f) => ({ ...f, config: { ...f.config, [key]: val } }))
                }
              />
              {field.help && <span className="text-foreground/55 text-xs">{field.help}</span>}
            </div>
          ) : (
            <>
              <Input
                id={`cfg-${key}`}
                type={field.secret ? "password" : field.type === "integer" ? "number" : "text"}
                placeholder={field.default !== undefined ? String(field.default) : ""}
                value={
                  form.config[key] !== undefined && form.config[key] !== null
                    ? String(form.config[key])
                    : ""
                }
                onChange={(e) => {
                  const val =
                    field.type === "integer"
                      ? e.target.value
                        ? Number(e.target.value)
                        : ""
                      : e.target.value;
                  setForm((f) => ({ ...f, config: { ...f.config, [key]: val } }));
                }}
                className="h-10 rounded-xl"
              />
              {field.help && <p className="text-foreground/55 text-xs">{field.help}</p>}
            </>
          )}
        </div>
      ))}
    </div>
  );
}

function ScheduleStep({
  collections,
  form,
  setForm,
}: {
  collections: { name: string }[];
  form: SyncSourceCreate;
  setForm: React.Dispatch<React.SetStateAction<SyncSourceCreate>>;
}) {
  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <Label className="text-foreground/80 text-xs font-medium tracking-wider uppercase">
          Target collection
        </Label>
        <Select
          value={form.collection_name}
          onValueChange={(val) => setForm((f) => ({ ...f, collection_name: val }))}
        >
          <SelectTrigger className="h-10 rounded-xl">
            <SelectValue placeholder="Select collection…" />
          </SelectTrigger>
          <SelectContent>
            {collections.map((c) => (
              <SelectItem key={c.name} value={c.name}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-foreground/80 text-xs font-medium tracking-wider uppercase">
          Sync mode
        </Label>
        <div className="grid gap-2 sm:grid-cols-3">
          {SYNC_MODES.map((mode) => {
            const active = (form.sync_mode ?? "full") === mode.value;
            return (
              <button
                key={mode.value}
                type="button"
                onClick={() => setForm((f) => ({ ...f, sync_mode: mode.value }))}
                className={cn(
                  "rounded-xl border p-3 text-left transition-colors",
                  active
                    ? "border-brand bg-brand/[0.06]"
                    : "border-foreground/10 bg-card hover:border-foreground/30",
                )}
              >
                <p className="text-foreground text-sm font-semibold">{mode.label}</p>
                <p className="text-foreground/55 mt-0.5 text-xs">{mode.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-foreground/80 text-xs font-medium tracking-wider uppercase">
          Schedule
        </Label>
        <div className="flex flex-wrap gap-2">
          {SCHEDULE_PRESETS.map((p) => {
            const active = (form.schedule_minutes ?? 0) === p.value;
            return (
              <button
                key={p.value}
                type="button"
                onClick={() =>
                  setForm((f) => ({ ...f, schedule_minutes: p.value === 0 ? null : p.value }))
                }
                className={cn(
                  "border-foreground/15 inline-flex rounded-full border px-3 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
                  active
                    ? "bg-foreground text-background border-foreground"
                    : "text-foreground/65 hover:text-foreground hover:border-foreground/40",
                )}
              >
                {p.label}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Label htmlFor="custom-schedule" className="text-foreground/55 text-xs">
            Custom (minutes):
          </Label>
          <Input
            id="custom-schedule"
            type="number"
            min={0}
            placeholder="0 = manual"
            value={form.schedule_minutes ?? ""}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                schedule_minutes: e.target.value ? Number(e.target.value) : null,
              }))
            }
            className="h-9 w-32 rounded-xl"
          />
        </div>
      </div>
    </div>
  );
}
