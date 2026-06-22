import type { ChatMessage, ChatMessageFile, MessagePart, ToolCall } from "@/types";

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
      ? [
          ...(toolCalls ?? []).map((tc) => ({
            id: tc.id,
            type: "tool" as const,
            toolCall: tc,
          })),
          ...(msg.content
            ? [{ id: `${msg.id}-text`, type: "text" as const, content: msg.content }]
            : []),
        ]
      : undefined;

  const files = Array.isArray(msg.files) ? msg.files : undefined;

  return {
    id: msg.id,
    role: msg.role,
    content: msg.content,
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
