import type { ChatMessage, ChatMessageFile, MessagePart, ToolCall } from "@/types";
{%- if cookiecutter.enable_deep_research %}
import { reconstructResearch, RESEARCH_TOOL_NAMES } from "@/lib/research-from-tools";
{%- endif %}

/**
 * Shape of a persisted message as returned by the backend (MessageRead).
 * Both the conversation history endpoint and the public demo endpoint return this.
 */
export interface RawToolCall {
  tool_call_id: string;
  tool_name: string;
  args: Record<string, unknown>;
  result?: unknown;
  status: string;
}

export interface RawMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  tool_calls?: RawToolCall[] | null;
  thinking?: string | null;
  user_rating?: number | null;
  rating_count?: { likes: number; dislikes: number } | null;
  files?: ChatMessageFile[] | null;
}

/**
 * Transform a persisted message into the live `ChatMessage` shape used by the chat UI.
 *
 * The DB stores flat fields (content + tool_calls) with no interleaving metadata, so we
 * reconstruct a realistic ordered timeline for assistant turns: tool parts first (tools ran
 * before the final answer), then the text part. Used by both the authenticated chat (when
 * loading a saved conversation) and the public demo replay.
 */
export function buildAssistantParts(
  toolCalls: ToolCall[],
  content: string,
  msgId: string,
  thinking?: string | null,
): MessagePart[] {
{%- if cookiecutter.enable_deep_research %}
  const research = reconstructResearch(toolCalls);
  const parts: MessagePart[] = [];
  if (thinking) {
    parts.push({ id: `${msgId}-thinking`, type: "thinking", content: thinking });
  }
  if (research) {
    parts.push({ id: `${msgId}-research`, type: "research", research });
  }
  for (const tc of toolCalls) {
    if (RESEARCH_TOOL_NAMES.has(tc.name)) continue;
    parts.push({ id: tc.id, type: "tool", toolCall: tc });
  }
  if (content) parts.push({ id: `${msgId}-text`, type: "text", content });
  return parts;
{%- else %}
  const parts: MessagePart[] = [];
  if (thinking) {
    parts.push({ id: `${msgId}-thinking`, type: "thinking" as const, content: thinking });
  }
  for (const tc of toolCalls) {
    parts.push({ id: tc.id, type: "tool" as const, toolCall: tc });
  }
  if (content) parts.push({ id: `${msgId}-text`, type: "text" as const, content });
  return parts;
{%- endif %}
}

export function conversationMessageToChatMessage(msg: RawMessage): ChatMessage {
  const toolCalls: ToolCall[] | undefined = msg.tool_calls?.map((tc) => ({
    id: tc.tool_call_id,
    name: tc.tool_name,
    args: tc.args,
    result: tc.result,
    status: (tc.status === "failed" ? "error" : tc.status) as ToolCall["status"],
  }));

  const parts: MessagePart[] | undefined =
    msg.role === "assistant"
      ? buildAssistantParts(toolCalls ?? [], msg.content, msg.id, msg.thinking)
      : undefined;

  const files = Array.isArray(msg.files) ? msg.files : undefined;

  return {
    id: msg.id,
    role: msg.role,
    content: msg.content,
    thinking: msg.thinking ?? undefined,
    timestamp: new Date(msg.created_at),
    conversationId: msg.conversation_id,
    toolCalls,
    parts,
    user_rating: msg.user_rating ?? undefined,
    rating_count: msg.rating_count ?? undefined,
    files,
    fileIds: files?.map((f) => f.id),
  };
}

export function conversationMessagesToChatMessages(msgs: RawMessage[]): ChatMessage[] {
  return msgs.map(conversationMessageToChatMessage);
}
