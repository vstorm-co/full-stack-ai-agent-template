"use client";

import {
  useEffect,
  useMemo,
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  useRef,
{%- endif %}
  useState,
} from "react";
import {
  Check,
  ChevronDown,
  Cpu,
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  Database,
  Lock,
{%- endif %}
  Settings2,
  Sliders,
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  Sparkles,
  Users,
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
  Telescope,
{%- endif %}
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui";
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
import { Checkbox } from "@/components/ui/checkbox";
import { useKnowledgeBases, useConversations } from "@/hooks";
import { useConversationStore, useKBSelectionStore } from "@/stores";
{%- else %}
import { useConversationStore } from "@/stores";
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
import { useChatModeStore } from "@/stores";
{%- endif %}
import { cn } from "@/lib/utils";
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
import type { KBScope, KnowledgeBase } from "@/types";
{%- endif %}

type ThinkingEffort = "off" | "low" | "medium" | "high";
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
type Tab = "kb" | "model" | "settings";
{%- else %}
type Tab = "model" | "settings";
{%- endif %}

interface ChatControlsProps {
  onModelChange?: (model: string | null) => void;
  onTemperatureChange?: (value: number | null) => void;
  onThinkingEffortChange?: (value: "low" | "medium" | "high" | null) => void;
}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
const SCOPE_META: Record<KBScope, { label: string; icon: LucideIcon }> = {
  personal: { label: "Personal", icon: Lock },
  org: { label: "Organization", icon: Users },
  app: { label: "App-wide", icon: Sparkles },
};

const SECTION_ORDER: KBScope[] = ["personal", "org", "app"];
{%- endif %}

const EFFORT_OPTIONS: { label: string; value: ThinkingEffort; hint: string }[] = [
  { label: "Off", value: "off", hint: "Direct answer, no reasoning" },
  { label: "Low", value: "low", hint: "Quick reasoning" },
  { label: "Medium", value: "medium", hint: "Balanced" },
  { label: "High", value: "high", hint: "Deep, slower" },
];

/**
 * Unified popover panel that replaces the 3 separate triggers (KB / Model /
 * Chat settings) with a single button that summarizes current state and opens
 * a tabbed control surface.
 */
export function ChatControls({
  onModelChange,
  onTemperatureChange,
  onThinkingEffortChange,
}: ChatControlsProps) {
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  const [tab, setTab] = useState<Tab>("kb");
{%- else %}
  const [tab, setTab] = useState<Tab>("model");
{%- endif %}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
  // ── KB state ────────────────────────────────────────────────────────────
  const { kbs, isLoading: kbsLoading, fetchKBs } = useKnowledgeBases();
  // Selector-narrowed subscriptions: re-render only when these specific fields
  // change. The whole-store form re-rendered ChatControls on every conv-store
  // mutation (incl. ones unrelated to KB), which combined with the inline
  // `setModel` ref from use-chat caused an effect-driven loop during streaming.
  const currentConversationId = useConversationStore((s) => s.currentConversationId);
  const conversations = useConversationStore((s) => s.conversations);
  const { updateActiveKBs } = useConversations();
  const activeKBIds = useKBSelectionStore((s) => s.activeKBIds);
  const toggleKB = useKBSelectionStore((s) => s.toggle);
  const hydrate = useKBSelectionStore((s) => s.hydrateFromConversation);

  const fetchedRef = useRef(false);
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    fetchKBs();
  }, [fetchKBs]);

  // Hydrate from a saved conversation once per conv switch. We guard with a
  // ref so even if upstream state re-emits the same conversation object with a
  // new identity (fetch refresh, etc.), we don't re-fire `set()` and trigger
  // another render cascade.
  const lastHydratedConvRef = useRef<string | null>(null);
  useEffect(() => {
    if (!currentConversationId) {
      lastHydratedConvRef.current = null;
      return;
    }
    if (lastHydratedConvRef.current === currentConversationId) return;
    const conversation = conversations.find((c) => c.id === currentConversationId);
    if (!conversation) return;
    lastHydratedConvRef.current = currentConversationId;
    hydrate(conversation.active_knowledge_base_ids ?? null);
  }, [currentConversationId, conversations, hydrate]);

  const activeIds = useMemo(() => new Set(activeKBIds), [activeKBIds]);
  const grouped = useMemo(
    () =>
      kbs.reduce<Record<KBScope, KnowledgeBase[]>>(
        (acc, kb) => {
          (acc[kb.scope] ??= []).push(kb);
          return acc;
        },
        { personal: [], org: [], app: [] },
      ),
    [kbs],
  );
  const sections = SECTION_ORDER.filter((s) => grouped[s].length > 0);
  const activeCount = activeIds.size;

  const handleKBToggle = async (kb: KnowledgeBase, checked: boolean) => {
    toggleKB(kb.id);
    if (currentConversationId) {
      const next = checked ? [...activeKBIds, kb.id] : activeKBIds.filter((id) => id !== kb.id);
      await updateActiveKBs(currentConversationId, next);
    }
  };
{%- else %}
  const { currentConversationId } = useConversationStore();
{%- endif %}

  // ── Model state ─────────────────────────────────────────────────────────
  const [availableModels, setAvailableModels] = useState<{ value: string; label: string }[]>([
    { value: "", label: "Default" },
  ]);
  const [selectedModel, setSelectedModel] = useState<{ value: string; label: string }>({
    value: "",
    label: "Default",
  });

  useEffect(() => {
    // Fetch model list once on mount. `onModelChange` is intentionally NOT in
    // deps — parents (use-chat) pass an inline arrow each render, so depending
    // on it triggers a refetch every render → infinite loop during streaming.
    fetch("/api/v1/agent/models", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.models) {
          const models = [
            { value: "", label: `Default (${data.default})` },
            ...data.models.map((m: string) => ({ value: m, label: m })),
          ];
          setAvailableModels(models);
          setSelectedModel(models[0]);
        }
      })
      .catch(() => {});
  }, []);

  // ── Settings state ──────────────────────────────────────────────────────
  const [temperature, setTemperature] = useState<number | null>(null);
  const [effort, setEffort] = useState<ThinkingEffort>("off");
  const settingsOverridden = temperature !== null || effort !== "off";
{%- if cookiecutter.enable_deep_research %}
  const deepResearch = useChatModeStore((s) => s.deepResearch);
{%- endif %}

  // ── Trigger summary ─────────────────────────────────────────────────────
  const triggerSummary = useMemo(() => {
    const parts: string[] = [];
{%- if cookiecutter.enable_deep_research %}
    if (deepResearch) parts.push("Research");
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
    if (activeCount > 0) parts.push(`${activeCount} KB${activeCount === 1 ? "" : "s"}`);
{%- endif %}
    if (selectedModel.value) parts.push(selectedModel.value);
    if (settingsOverridden) parts.push("Custom");
    return parts.length ? parts.join(" · ") : "Controls";
  }, [{% if cookiecutter.enable_deep_research %}deepResearch, {% endif %}{% if cookiecutter.enable_teams and cookiecutter.enable_rag %}activeCount, {% endif %}selectedModel, settingsOverridden]);

  const hasOverrides =
    {% if cookiecutter.enable_deep_research %}deepResearch || {% endif %}{% if cookiecutter.enable_teams and cookiecutter.enable_rag %}activeCount > 0 || {% endif %}selectedModel.value !== "" || settingsOverridden;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Chat controls"
          className={cn(
            "border-foreground/10 bg-card hover:border-foreground/25 hover:bg-foreground/[0.04] inline-flex items-center gap-1.5 rounded-full border py-1 pr-2 pl-2.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
            hasOverrides ? "text-foreground" : "text-foreground/65",
          )}
        >
          <Sliders className="h-3 w-3" />
          <span className="max-w-[200px] truncate">{triggerSummary}</span>
          {hasOverrides && (
            <span
              aria-hidden
              className="bg-brand inline-block h-1 w-1 rounded-full"
              {% raw %}style={{ boxShadow: "0 0 6px var(--color-brand)" }}{% endraw %}
            />
          )}
          <ChevronDown className="text-foreground/45 h-3 w-3" />
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className="border-foreground/10 bg-card/95 relative isolate w-[380px] overflow-hidden rounded-2xl border p-0 shadow-2xl backdrop-blur-xl"
      >
        {/* Brand glow corner */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-16 -right-12 -z-10 h-40 w-40 rounded-full blur-3xl"
          {% raw %}style={{
            background:
              "radial-gradient(circle, oklch(from var(--color-brand) l c h / 0.25), transparent 65%)",
          }}{% endraw %}
        />

        {/* Tabs */}
        <div className="border-foreground/10 flex items-center gap-1 border-b p-2">
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
          <TabButton icon={Database} label="KB" active={tab === "kb"} onClick={() => setTab("kb")} />
{%- endif %}
          {onModelChange && (
            <TabButton
              icon={Cpu}
              label="Model"
              active={tab === "model"}
              onClick={() => setTab("model")}
            />
          )}
          {onTemperatureChange && onThinkingEffortChange && (
            <TabButton
              icon={Settings2}
              label="Settings"
              active={tab === "settings"}
              onClick={() => setTab("settings")}
            />
          )}
        </div>

        {/* Body */}
        <div className="max-h-[420px] scrollbar-thin overflow-y-auto p-4">
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
          {tab === "kb" && (
            <KBPanel
              sections={sections}
              grouped={grouped}
              activeIds={activeIds}
              kbs={kbs}
              isLoading={kbsLoading}
              currentConversationId={currentConversationId}
              onToggle={handleKBToggle}
            />
          )}
{%- endif %}
          {tab === "model" && (
            <ModelPanel
              models={availableModels}
              selected={selectedModel}
              onPick={(m) => {
                setSelectedModel(m);
                onModelChange?.(m.value || null);
              }}
            />
          )}
          {tab === "settings" && (
            <SettingsPanel
              temperature={temperature}
              effort={effort}
              onTemperatureChange={(v) => {
                setTemperature(v);
                onTemperatureChange?.(v);
              }}
              onEffortChange={(v) => {
                setEffort(v);
                onThinkingEffortChange?.(v === "off" ? null : v);
              }}
            />
          )}
        </div>

        {/* Footer */}
        <div className="border-foreground/10 text-foreground/45 flex items-center justify-between border-t px-4 py-2 font-mono text-[10px] tracking-wider uppercase">
          <span className="inline-flex items-center gap-1.5">
            <span
              aria-hidden
              className="bg-brand inline-block h-1 w-1 animate-pulse rounded-full"
              {% raw %}style={{ boxShadow: "0 0 6px var(--color-brand)" }}{% endraw %}
            />
            {currentConversationId ? "Saved for this chat" : "Saves on send"}
          </span>
          <span>esc to close</span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function TabButton({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
        active
          ? "bg-foreground text-background"
          : "text-foreground/55 hover:bg-foreground/[0.04] hover:text-foreground",
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </button>
  );
}

{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
/** Knowledge bases panel — grouped by scope. */
function KBPanel({
  sections,
  grouped,
  activeIds,
  kbs,
  isLoading,
  currentConversationId,
  onToggle,
}: {
  sections: KBScope[];
  grouped: Record<KBScope, KnowledgeBase[]>;
  activeIds: Set<string>;
  kbs: KnowledgeBase[];
  isLoading: boolean;
  currentConversationId: string | null;
  onToggle: (kb: KnowledgeBase, checked: boolean) => void;
}) {
  const activeCount = activeIds.size;

  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between">
        <p className="text-foreground text-sm font-semibold">Knowledge bases</p>
        <span className="text-foreground/55 font-mono text-[10px] tabular-nums">
          {activeCount}/{kbs.length} active
        </span>
      </div>
      <p className="text-foreground/55 mb-4 text-xs leading-relaxed">
        Picked KBs are searched on every message you send.
      </p>

      {isLoading && kbs.length === 0 ? (
        <p className="text-foreground/55 py-3 text-xs">Loading…</p>
      ) : kbs.length === 0 ? (
        <div className="border-foreground/10 bg-foreground/[0.02] rounded-xl border px-4 py-6 text-center">
          <Database className="text-foreground/30 mx-auto mb-2 h-6 w-6" />
          <p className="text-foreground/65 text-xs">No knowledge bases yet.</p>
          <p className="text-foreground/45 mt-1 text-[11px]">
            Create one on the Knowledge Bases page.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sections.map((scope) => {
            const meta = SCOPE_META[scope];
            return (
              <section key={scope}>
                <div className="text-foreground/55 mb-2 flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase">
                  <meta.icon className="h-3 w-3" />
                  {meta.label}
                </div>
                <ul className="space-y-1">
                  {grouped[scope].map((kb) => {
                    const isActive = activeIds.has(kb.id);
                    return (
                      <li key={kb.id}>
                        <label
                          className={cn(
                            "flex cursor-pointer items-start gap-2.5 rounded-xl border p-2.5 transition-all",
                            isActive
                              ? "border-brand/40 bg-brand/[0.06]"
                              : "border-foreground/10 hover:border-foreground/25 hover:bg-foreground/[0.02]",
                          )}
                        >
                          <Checkbox
                            checked={isActive}
                            onCheckedChange={(c) => onToggle(kb, c as boolean)}
                            className="mt-0.5 shrink-0"
                          />
                          <div className="min-w-0 flex-1">
                            <p className="text-foreground truncate text-xs font-medium">
                              {kb.name}
                            </p>
                            {kb.description && (
                              <p className="text-foreground/55 mt-0.5 line-clamp-2 text-[11px] leading-relaxed">
                                {kb.description}
                              </p>
                            )}
                          </div>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      )}

      {!currentConversationId && kbs.length > 0 && (
        <p className="text-foreground/45 mt-4 font-mono text-[10px] tracking-wider uppercase">
          Draft selection — saves when you send.
        </p>
      )}
    </div>
  );
}
{%- endif %}

/** Model picker panel. */
function ModelPanel({
  models,
  selected,
  onPick,
}: {
  models: { value: string; label: string }[];
  selected: { value: string; label: string };
  onPick: (m: { value: string; label: string }) => void;
}) {
  return (
    <div>
      <p className="text-foreground mb-1 text-sm font-semibold">Model</p>
      <p className="text-foreground/55 mb-4 text-xs leading-relaxed">
        Pick the model that handles this conversation.
      </p>
      <ul className="space-y-1">
        {models.map((m) => {
          const isActive = selected.value === m.value;
          return (
            <li key={m.value || "default"}>
              <button
                type="button"
                onClick={() => onPick(m)}
                className={cn(
                  "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-xs transition-all",
                  isActive
                    ? "border-brand/40 bg-brand/[0.06] text-foreground"
                    : "border-foreground/10 text-foreground/75 hover:border-foreground/25 hover:bg-foreground/[0.02] hover:text-foreground",
                )}
              >
                <span className="truncate font-medium">{m.label}</span>
                {isActive && <Check className="text-brand h-3.5 w-3.5 shrink-0" />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Chat settings panel — temperature + thinking effort. */
function SettingsPanel({
  temperature,
  effort,
  onTemperatureChange,
  onEffortChange,
}: {
  temperature: number | null;
  effort: ThinkingEffort;
  onTemperatureChange: (v: number | null) => void;
  onEffortChange: (v: ThinkingEffort) => void;
}) {
{%- if cookiecutter.enable_deep_research %}
  const deepResearch = useChatModeStore((s) => s.deepResearch);
  const setDeepResearch = useChatModeStore((s) => s.setDeepResearch);
{%- endif %}
  return (
    <div className="space-y-6">
{%- if cookiecutter.enable_deep_research %}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between gap-3">
          <span className="text-foreground inline-flex items-center gap-1.5 text-sm font-semibold">
            <Telescope className="h-3.5 w-3.5" />
            Deep research
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={deepResearch}
            onClick={() => setDeepResearch(!deepResearch)}
            className={cn(
              "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors",
              deepResearch ? "bg-primary" : "bg-foreground/20",
            )}
          >
            <span
              className={cn(
                "bg-background inline-block h-4 w-4 transform rounded-full shadow transition-transform",
                deepResearch ? "translate-x-4" : "translate-x-0.5",
              )}
            />
          </button>
        </div>
        <p className="text-foreground/55 text-[11px] leading-relaxed">
          {deepResearch
            ? "Plans the work, delegates to parallel subagents, then composes a cited report — asking you to clarify the scope first when the request is vague."
            : "Answers directly in a single fast pass, with no planning or delegation."}
        </p>
      </div>
{%- endif %}
      {/* Temperature */}
      <div className="space-y-2.5">
        <div className="flex items-baseline justify-between">
          <label htmlFor="chat-temp" className="text-foreground text-sm font-semibold">
            Temperature
          </label>
          <span className="text-foreground font-mono text-xs tabular-nums">
            {temperature === null ? (
              <span className="text-foreground/55">default</span>
            ) : (
              temperature.toFixed(2)
            )}
          </span>
        </div>
        <input
          id="chat-temp"
          type="range"
          min={0}
          max={2}
          step={0.05}
          value={temperature ?? 0.7}
          onChange={(e) => onTemperatureChange(parseFloat(e.target.value))}
          className="bg-foreground/15 h-1.5 w-full cursor-pointer appearance-none rounded-full accent-[var(--color-brand)]"
        />
        <div className="text-foreground/45 flex justify-between font-mono text-[10px] tracking-wider uppercase">
          <span>focused</span>
          <span>creative</span>
        </div>
        {temperature !== null && (
          <button
            type="button"
            onClick={() => onTemperatureChange(null)}
            className="text-foreground/55 hover:text-foreground text-[11px] underline-offset-2 hover:underline"
          >
            Reset to server default
          </button>
        )}
      </div>

      {/* Thinking effort */}
      <div className="space-y-2.5">
        <div className="flex items-baseline justify-between">
          <span className="text-foreground text-sm font-semibold">Thinking effort</span>
          <span className="text-foreground/45 text-[10px]">model-dependent</span>
        </div>
        <div className="grid grid-cols-4 gap-1">
          {EFFORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onEffortChange(opt.value)}
              className={cn(
                "rounded-lg px-2 py-1.5 font-mono text-[11px] tracking-wider uppercase transition-colors",
                effort === opt.value
                  ? "bg-foreground text-background"
                  : "border-foreground/15 text-foreground/55 hover:text-foreground border",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className="text-foreground/55 text-[11px]">
          {EFFORT_OPTIONS.find((o) => o.value === effort)?.hint}
        </p>
      </div>

      <p className="text-foreground/45 text-[10px] leading-relaxed">
        Settings persist for the current chat session. Some controls are no-ops on models that
        don&apos;t support them.
      </p>
    </div>
  );
}
