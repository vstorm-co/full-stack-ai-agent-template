"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Check,
  ExternalLink,
  Pencil,
  Plug,
  Plus,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Label,
  Switch,
} from "@/components/ui";
import { EmptyState } from "@/components/states";
import { ApiError } from "@/lib/api-client";
import { useMcpConnections } from "@/hooks";
import {
  catalogBaseUrl,
  logoDataUri,
  MCP_CATALOG,
  MCP_CATEGORIES,
  type McpCatalogEntry,
} from "@/lib/mcp-catalog";
import { listWorkspaceMcpServers, startMcpOAuth } from "@/lib/mcp-connections-api";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";
import type { McpConnectionRecord, McpToolInfo } from "@/lib/mcp-connections-api";

const NAME_PATTERN = /^[a-z0-9][a-z0-9-]{0,31}$/;

function errorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return fallback;
}

/** Brand logo with an initial-letter avatar fallback if the image can't load. */
function PluginLogo({ entry }: { entry: McpCatalogEntry }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span
        aria-hidden
        className="bg-foreground/10 text-foreground/70 flex h-[22px] w-[22px] shrink-0 items-center justify-center rounded text-xs font-semibold"
      >
        {entry.title.charAt(0).toUpperCase()}
      </span>
    );
  }
  return (
    // Plain <img> (not next/image) — the source is an inlined data URI, so
    // there's nothing for the image optimizer to fetch or cache.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={logoDataUri(entry.domain)}
      alt=""
      width={22}
      height={22}
      loading="lazy"
      onError={() => setFailed(true)}
      className="h-[22px] w-[22px] rounded object-contain"
    />
  );
}

function StatusDot({ connection }: { connection: McpConnectionRecord }) {
  const status = connection.last_status;
  const enabled = connection.is_enabled;
  return (
    <span
      className={cn(
        "mt-1.5 h-2 w-2 shrink-0 rounded-full",
        // Off (toggle disabled) reads as muted/inactive, regardless of last test.
        !enabled && "bg-foreground/20",
        enabled && status === "ok" && "bg-emerald-500",
        enabled && status === "error" && "bg-destructive",
        enabled && !status && "bg-foreground/40",
      )}
      title={
        !enabled
          ? "Off — not used in conversations"
          : status === "ok"
            ? "Reachable at last check"
            : status === "error"
              ? (connection.last_error ?? "Unreachable at last check")
              : "Not checked yet"
      }
    />
  );
}

export function McpConnectionsManager() {
  const { connections, isLoading, error, refresh, create, update, remove, test } =
    useMcpConnections();
  const { data: workspaceServers = [] } = useQuery({
    queryKey: qk.mcpConnections.workspace(),
    queryFn: listWorkspaceMcpServers,
  });
  const workspaceNames = new Set(workspaceServers.map((server) => server.name));

  // Surface the result of an OAuth redirect (see the /oauth/callback route),
  // then strip the query params so a page refresh doesn't re-toast.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const result = params.get("mcp_oauth");
    if (!result) return;
    if (result === "success") {
      const name = params.get("name");
      toast.success(name ? `${name} connected.` : "Plugin connected.");
      void refresh();
    } else {
      toast.error(params.get("reason") ?? "Authorization failed.");
    }
    params.delete("mcp_oauth");
    params.delete("name");
    params.delete("reason");
    const qs = params.toString();
    window.history.replaceState({}, "", window.location.pathname + (qs ? `?${qs}` : ""));
  }, [refresh]);

  // Add/edit dialog state.
  const [editingId, setEditingId] = useState<string | "new" | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftUrl, setDraftUrl] = useState("");
  const [draftToken, setDraftToken] = useState("");
  const [clearToken, setClearToken] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Catalog connect state: entry awaiting a token, and the card being connected.
  const [connectEntry, setConnectEntry] = useState<McpCatalogEntry | null>(null);
  const [connectToken, setConnectToken] = useState("");
  const [connectingId, setConnectingId] = useState<string | null>(null);

  // Tool-picker dialog state (opened after a successful test).
  const [toolPicker, setToolPicker] = useState<{
    connection: McpConnectionRecord;
    tools: McpToolInfo[];
    checked: Set<string>;
  } | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const editing =
    editingId !== null && editingId !== "new"
      ? (connections.find((c) => c.id === editingId) ?? null)
      : null;

  const openCreate = () => {
    setEditingId("new");
    setDraftName("");
    setDraftUrl("");
    setDraftToken("");
    setClearToken(false);
  };

  const openEdit = (connection: McpConnectionRecord) => {
    setEditingId(connection.id);
    setDraftName(connection.name);
    setDraftUrl(connection.url);
    setDraftToken("");
    setClearToken(false);
  };

  const closeDialog = () => {
    if (submitting) return;
    setEditingId(null);
  };

  const handleSubmit = async () => {
    const name = draftName.trim().toLowerCase();
    const url = draftUrl.trim();
    const token = draftToken.trim();
    if (!NAME_PATTERN.test(name)) {
      toast.error("Name must be lowercase letters, digits, and hyphens (max 32 chars).");
      return;
    }
    if (!/^https?:\/\//.test(url)) {
      toast.error("URL must start with http:// or https://");
      return;
    }
    setSubmitting(true);
    try {
      if (editingId === "new") {
        const created = await create({ name, url, ...(token ? { auth_token: token } : {}) });
        toast.success(`Connection "${name}" added.`);
        setEditingId(null);
        void handleEditTools(created);
      } else if (editingId) {
        // Send only what actually changed — re-sending the same URL would reset
        // the connection's last-checked status for no reason.
        await update(editingId, {
          ...(name !== editing?.name ? { name } : {}),
          ...(url !== editing?.url ? { url } : {}),
          // Omit auth_token to keep the stored one; "" clears it.
          ...(token ? { auth_token: token } : clearToken ? { auth_token: "" } : {}),
        });
        toast.success(`Connection "${name}" updated.`);
        setEditingId(null);
      }
    } catch (e) {
      toast.error(errorMessage(e, "Failed to save connection"));
    } finally {
      setSubmitting(false);
    }
  };

  /** Probe the server; returns discovered tools or null (after toasting the error). */
  const probeConnection = async (connection: McpConnectionRecord) => {
    setTestingId(connection.id);
    try {
      const result = await test(connection.id);
      if (!result.ok) {
        toast.error(result.error ?? "Server is unreachable.");
        return null;
      }
      return result.tools;
    } catch (e) {
      toast.error(errorMessage(e, "Test failed"));
      return null;
    } finally {
      setTestingId(null);
    }
  };

  const openToolPicker = (connection: McpConnectionRecord, tools: McpToolInfo[]) => {
    setToolPicker({
      connection,
      tools,
      checked: new Set(
        connection.allowed_tools === null ? tools.map((t) => t.name) : connection.allowed_tools,
      ),
    });
  };

  const handleTest = async (connection: McpConnectionRecord) => {
    const tools = await probeConnection(connection);
    if (tools) toast.success(`Connected — ${tools.length} tools available.`);
  };

  const handleEditTools = async (connection: McpConnectionRecord) => {
    const tools = await probeConnection(connection);
    if (tools) openToolPicker(connection, tools);
  };

  /** Connection already pointing at this catalog entry, if any.
   * Fixed-URL entries match by base URL (query ignored); personal-url
   * entries (e.g. Zapier) match by the connection name. */
  const connectionFor = (entry: McpCatalogEntry) =>
    connections.find((c) =>
      entry.auth === "personal-url"
        ? c.name === entry.id
        : catalogBaseUrl(c.url) === catalogBaseUrl(entry.url),
    ) ?? null;

  const doCatalogConnect = async (entry: McpCatalogEntry, secret?: string) => {
    setConnectingId(entry.id);
    try {
      // The credential can be a bearer header (default), a URL query param
      // (tokenPlacement: "url"), or the user's whole personal server URL.
      let url = entry.url;
      let token: string | undefined = secret;
      if (entry.auth === "personal-url") {
        url = secret ?? "";
        token = undefined;
      } else if (entry.tokenPlacement === "url" && secret) {
        url = entry.url.replace("{token}", encodeURIComponent(secret));
        token = undefined;
      }
      const created = await create({
        name: entry.id,
        url,
        ...(token ? { auth_token: token } : {}),
      });
      toast.success(`${entry.title} connected.`);
      setConnectEntry(null);
      setConnectToken("");
      void handleEditTools(created);
    } catch (e) {
      toast.error(errorMessage(e, `Failed to connect ${entry.title}`));
    } finally {
      setConnectingId(null);
    }
  };

  /** Kick off the OAuth flow: get the consent URL, then send the browser there. */
  const startOAuth = async (name: string, url: string, title: string) => {
    setConnectingId(name);
    try {
      const { authorization_url } = await startMcpOAuth({ name, url });
      window.location.href = authorization_url;
    } catch (e) {
      toast.error(errorMessage(e, `Couldn't start sign-in for ${title}`));
      setConnectingId(null);
    }
    // On success the browser navigates away — leave connectingId set.
  };

  const handleCatalogConnect = (entry: McpCatalogEntry) => {
    if (entry.auth === "oauth") {
      void startOAuth(entry.id, entry.url, entry.title);
      return;
    }
    if (entry.auth === "token" || entry.auth === "personal-url") {
      setConnectToken("");
      setConnectEntry(entry);
      return;
    }
    void doCatalogConnect(entry);
  };

  const handleToggle = async (connection: McpConnectionRecord, next: boolean) => {
    try {
      await update(connection.id, { is_enabled: next });
    } catch (e) {
      toast.error(errorMessage(e, "Failed to toggle"));
    }
  };

  const handleDelete = async (connection: McpConnectionRecord) => {
    if (!confirm(`Remove connection "${connection.name}"?`)) return;
    try {
      await remove(connection.id);
      toast.success(`Connection "${connection.name}" removed.`);
    } catch (e) {
      toast.error(errorMessage(e, "Failed to delete"));
    }
  };

  const handleSaveTools = async () => {
    if (!toolPicker) return;
    const { connection, tools, checked } = toolPicker;
    setSubmitting(true);
    try {
      if (checked.size === tools.length) {
        // Everything selected → store NULL so future server tools flow through.
        await update(connection.id, { clear_allowed_tools: true });
      } else {
        await update(connection.id, { allowed_tools: [...checked] });
      }
      toast.success("Tool selection saved.");
      setToolPicker(null);
    } catch (e) {
      toast.error(errorMessage(e, "Failed to save tools"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      {error && (
        <div className="border-destructive/30 bg-destructive/5 text-destructive flex items-center justify-between rounded-xl border px-4 py-3 text-sm">
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={() => refresh()}>
            Retry
          </Button>
        </div>
      )}

      {workspaceServers.length > 0 && (
        <section className="space-y-3">
          <div>
            <h3 className="text-foreground text-sm font-semibold">Workspace plugins</h3>
            <p className="text-foreground/55 mt-0.5 text-xs">
              Set up by your administrator — always available to the assistant.
            </p>
          </div>
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {workspaceServers.map((server) => (
              <li key={server.name} className="flex items-center gap-3 px-4 py-3">
                <Building2 className="text-foreground/45 h-4 w-4 shrink-0" />
                <div className="min-w-0 flex-1">
                  <span className="text-foreground text-sm font-medium">{server.name}</span>
                  <p className="text-foreground/55 mt-0.5 text-xs">
                    {server.allowed_tools === null
                      ? "All tools exposed"
                      : `${server.allowed_tools.length} tools selected`}
                  </p>
                </div>
                <span className="text-foreground/45 border-foreground/15 rounded-full border px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase">
                  Workspace
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <div>
          <h3 className="text-foreground text-sm font-semibold">Browse plugins</h3>
          <p className="text-foreground/55 mt-0.5 text-xs">
            Curated, verified servers — connect with one click.
          </p>
        </div>
        <div className="space-y-5">
          {[...MCP_CATEGORIES]
            .sort((a, b) => a.label.localeCompare(b.label))
            .map((category) => {
              const entries = MCP_CATALOG.filter((e) => e.category === category.id).sort((a, b) =>
                a.title.localeCompare(b.title),
              );
              if (entries.length === 0) return null;
              return (
                <div key={category.id} className="space-y-3">
                  <div className="flex items-center gap-3">
                    <h4 className="text-foreground/50 shrink-0 font-mono text-[10px] font-medium tracking-[0.12em] uppercase">
                      {category.label}
                    </h4>
                    <span aria-hidden className="bg-foreground/10 h-px flex-1" />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {entries.map((entry) => {
                      const existing = connectionFor(entry);
                      const busy = connectingId === entry.id;
                      // A workspace server claims the tool prefix this entry
                      // would use, so a personal connection under the same name
                      // would be dropped from every turn. Say so instead.
                      const shadowed = workspaceNames.has(entry.id);
                      // An OAuth connection that hasn't finished consent isn't
                      // really connected yet — offer to finish signing in.
                      const needsAuth =
                        existing?.auth_type === "oauth" && !existing.oauth_authorized;
                      const isOAuth = entry.auth === "oauth";
                      return (
                        <div
                          key={entry.id}
                          className="border-foreground/10 flex flex-col gap-2 rounded-xl border px-4 py-3"
                        >
                          <div className="flex items-start gap-2.5">
                            <PluginLogo entry={entry} />
                            <div className="min-w-0 flex-1">
                              <p className="text-foreground text-sm font-semibold">{entry.title}</p>
                              <p className="text-foreground/55 mt-0.5 text-xs leading-relaxed">
                                {entry.description}
                              </p>
                            </div>
                          </div>
                          {entry.example && (
                            <p className="text-foreground/45 text-[11px] italic">{entry.example}</p>
                          )}
                          <div className="mt-auto flex items-center justify-between gap-2 pt-1">
                            <span className="text-foreground/45 font-mono text-[10px] tracking-wider uppercase">
                              {entry.auth === "none"
                                ? "No account needed"
                                : entry.auth === "oauth"
                                  ? "One-click sign-in"
                                  : entry.auth === "personal-url"
                                    ? "Your personal link"
                                    : "Token required"}
                            </span>
                            {shadowed ? (
                              <span className="text-foreground/65 inline-flex items-center gap-1 text-xs font-medium">
                                <Building2 className="text-foreground/45 h-3.5 w-3.5" />
                                Provided by your workspace
                              </span>
                            ) : existing && !needsAuth ? (
                              <span className="text-foreground/65 inline-flex items-center gap-1 text-xs font-medium">
                                <Check className="h-3.5 w-3.5 text-emerald-500" />
                                Connected
                              </span>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleCatalogConnect(entry)}
                                disabled={busy}
                              >
                                {busy
                                  ? isOAuth
                                    ? "Redirecting…"
                                    : "Connecting…"
                                  : needsAuth
                                    ? "Finish sign-in"
                                    : isOAuth
                                      ? "Sign in"
                                      : "Connect"}
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <div>
            <h3 className="text-foreground text-sm font-semibold">Your connections</h3>
            <p className="text-foreground/55 mt-0.5 text-xs">
              Only connect servers you trust — their tools and descriptions become part of the
              conversation.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={openCreate}>
            <Plus className="mr-1 h-3.5 w-3.5" />
            Add custom server
          </Button>
        </div>

        {connections.length === 0 ? (
          <EmptyState
            title="No connections yet"
            description="Connect a plugin from the catalog above, or add a custom MCP server."
          />
        ) : (
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {connections.map((connection) => (
              <li key={connection.id} className="flex items-start gap-3 px-4 py-3">
                <StatusDot connection={connection} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="text-foreground text-sm font-medium">{connection.name}</span>
                    <span className="text-foreground/45 truncate font-mono text-xs">
                      {/* Query string may carry an API key — never render it. */}
                      {connection.url.split("?")[0]}
                      {connection.url.includes("?") && "?…"}
                    </span>
                  </div>
                  <p className="text-foreground/55 mt-0.5 text-xs">
                    {connection.allowed_tools === null
                      ? "All tools exposed"
                      : `${connection.allowed_tools.length} tools selected`}
                    {connection.auth_type === "oauth"
                      ? connection.oauth_authorized
                        ? " · signed in"
                        : " · not authorized"
                      : connection.has_auth_token && " · token set"}
                    {connection.last_status === "error" && connection.last_error && (
                      <span className="text-destructive"> · {connection.last_error}</span>
                    )}
                  </p>
                </div>
                {connection.auth_type === "oauth" && !connection.oauth_authorized ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void startOAuth(connection.name, connection.url, connection.name)}
                    disabled={connectingId === connection.name}
                  >
                    <Plug className="mr-1 h-3.5 w-3.5" />
                    {connectingId === connection.name ? "Redirecting…" : "Authorize"}
                  </Button>
                ) : (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleEditTools(connection)}
                      disabled={testingId === connection.id}
                      title="Choose which tools the assistant may use"
                    >
                      <SlidersHorizontal className="mr-1 h-3.5 w-3.5" />
                      Tools
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleTest(connection)}
                      disabled={testingId === connection.id}
                    >
                      <Plug className="mr-1 h-3.5 w-3.5" />
                      {testingId === connection.id ? "Testing…" : "Test"}
                    </Button>
                  </>
                )}
                <Switch
                  checked={connection.is_enabled}
                  onCheckedChange={(v) => handleToggle(connection, v)}
                  disabled={isLoading}
                  aria-label={`Toggle ${connection.name}`}
                />
                {connection.auth_type !== "oauth" && (
                  <button
                    type="button"
                    onClick={() => openEdit(connection)}
                    className="text-foreground/55 hover:bg-foreground/5 hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                    title="Edit"
                    aria-label="Edit"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => handleDelete(connection)}
                  className="text-foreground/55 hover:bg-destructive/10 hover:text-destructive inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                  title="Delete"
                  aria-label="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Dialog open={editingId !== null} onOpenChange={(o) => !o && closeDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingId === "new" ? "Add MCP server" : `Edit "${draftName}"`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="mcp-name">Name</Label>
              <Input
                id="mcp-name"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value.toLowerCase())}
                placeholder="github"
                maxLength={32}
                autoFocus
                className="mt-1.5"
              />
              <p className="text-foreground/45 mt-1 text-[11px]">
                Lowercase letters, digits, hyphens. Also used to prefix the server&apos;s tool names
                in chat.
              </p>
            </div>
            <div>
              <Label htmlFor="mcp-url">Server URL</Label>
              <Input
                id="mcp-url"
                value={draftUrl}
                onChange={(e) => setDraftUrl(e.target.value)}
                placeholder="https://example.com/mcp"
                maxLength={2048}
                className="mt-1.5 font-mono text-sm"
              />
              <p className="text-foreground/45 mt-1 text-[11px]">
                Streamable HTTP endpoint of the MCP server.
              </p>
            </div>
            <div>
              <Label htmlFor="mcp-token">Bearer token (optional)</Label>
              <Input
                id="mcp-token"
                type="password"
                value={draftToken}
                onChange={(e) => {
                  setDraftToken(e.target.value);
                  if (e.target.value) setClearToken(false);
                }}
                placeholder={editing?.has_auth_token ? "•••••• (stored — type to replace)" : "sk-…"}
                maxLength={4096}
                className="mt-1.5 font-mono text-sm"
              />
              <p className="text-foreground/45 mt-1 text-[11px]">
                Sent as an Authorization header. Stored encrypted; never shown again.
              </p>
              {editing?.has_auth_token && !draftToken && (
                <div className="mt-2 flex items-center gap-2">
                  <Switch
                    id="mcp-clear-token"
                    checked={clearToken}
                    onCheckedChange={setClearToken}
                  />
                  <Label htmlFor="mcp-clear-token" className="text-xs font-normal">
                    Remove the stored token
                  </Label>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={closeDialog} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : editingId === "new" ? "Add & test" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={connectEntry !== null}
        onOpenChange={(o) => !o && connectingId === null && setConnectEntry(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect {connectEntry?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-foreground/55 text-xs leading-relaxed">
              {connectEntry?.description}
            </p>
            <div>
              <Label htmlFor="catalog-token">
                {connectEntry?.auth === "personal-url" ? "Your personal link" : "Access token"}
              </Label>
              <Input
                id="catalog-token"
                type={connectEntry?.auth === "personal-url" ? "text" : "password"}
                value={connectToken}
                onChange={(e) => setConnectToken(e.target.value)}
                placeholder={
                  connectEntry?.auth === "personal-url"
                    ? "https://mcp.zapier.com/api/mcp/s/…"
                    : "Paste your token here"
                }
                maxLength={4096}
                autoFocus
                className="mt-1.5 font-mono text-sm"
              />
              <p className="text-foreground/45 mt-1 text-[11px]">
                {connectEntry?.auth === "personal-url"
                  ? "The link contains your private key — treat it like a password."
                  : "Stored encrypted; never shown again."}
              </p>
              {connectEntry?.tokenHelp && (
                <a
                  href={connectEntry.tokenHelp.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-foreground mt-2 inline-flex items-center gap-1 text-xs underline underline-offset-2"
                >
                  {connectEntry.tokenHelp.label}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setConnectEntry(null)}
              disabled={connectingId !== null}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!connectEntry) return;
                const secret = connectToken.trim();
                if (connectEntry.auth === "personal-url" && !/^https:\/\//.test(secret)) {
                  toast.error("Paste the full https:// link from your provider.");
                  return;
                }
                void doCatalogConnect(connectEntry, secret);
              }}
              disabled={connectingId !== null || !connectToken.trim()}
            >
              {connectingId !== null ? "Connecting…" : "Connect"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={toolPicker !== null}
        onOpenChange={(o) => !o && !submitting && setToolPicker(null)}
      >
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Tools from &quot;{toolPicker?.connection.name}&quot;</DialogTitle>
          </DialogHeader>
          <p className="text-foreground/55 text-xs">
            Pick which tools the assistant may use. Selecting all keeps future server tools enabled
            automatically.
          </p>
          <ul className="border-foreground/10 divide-foreground/8 divide-y rounded-xl border">
            {toolPicker?.tools.map((tool) => {
              const checked = toolPicker.checked.has(tool.name);
              return (
                <li key={tool.name} className="flex items-start gap-3 px-4 py-2.5">
                  <div className="min-w-0 flex-1">
                    <code className="text-foreground bg-foreground/8 rounded px-1.5 py-0.5 font-mono text-xs">
                      {tool.name}
                    </code>
                    {tool.description && (
                      <p className="text-foreground/55 mt-1 line-clamp-2 text-xs">
                        {tool.description}
                      </p>
                    )}
                  </div>
                  <Switch
                    checked={checked}
                    onCheckedChange={(v) =>
                      setToolPicker((prev) => {
                        if (!prev) return prev;
                        const next = new Set(prev.checked);
                        if (v) next.add(tool.name);
                        else next.delete(tool.name);
                        return { ...prev, checked: next };
                      })
                    }
                    aria-label={`Toggle ${tool.name}`}
                  />
                </li>
              );
            })}
          </ul>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setToolPicker(null)} disabled={submitting}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveTools}
              disabled={submitting || toolPicker?.checked.size === 0}
            >
              {submitting ? "Saving…" : "Save selection"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
