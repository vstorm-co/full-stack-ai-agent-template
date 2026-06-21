"use client";

import { create } from "zustand";
import type { ChatMessage, MessagePart, ToolCall } from "@/types";

function newPartId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `part-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;

  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updater: (msg: ChatMessage) => ChatMessage) => void;
  updateMessagesWhere: (
    predicate: (msg: ChatMessage) => boolean,
    updater: (msg: ChatMessage) => ChatMessage,
  ) => void;
  addToolCall: (messageId: string, toolCall: ToolCall) => void;
  updateToolCall: (messageId: string, toolCallId: string, update: Partial<ToolCall>) => void;
  /** Append a streamed text delta — extends the trailing text part or
   *  starts a new one, keeping the flat ``content`` aggregate in sync. */
  appendTextDelta: (messageId: string, text: string) => void;
  /** Append a streamed reasoning delta — same logic for "thinking" parts. */
  appendThinkingDelta: (messageId: string, text: string) => void;
  /** Add a tool call as an ordered part (and to the flat ``toolCalls``). */
  addToolCallPart: (messageId: string, toolCall: ToolCall) => void;
  /** Update a tool call inside its part and the flat ``toolCalls``. */
  updateToolCallPart: (messageId: string, toolCallId: string, update: Partial<ToolCall>) => void;
  setStreaming: (streaming: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (id, updater) =>
    set((state) => ({
      messages: state.messages.map((msg) => (msg.id === id ? updater(msg) : msg)),
    })),

  updateMessagesWhere: (predicate, updater) =>
    set((state) => ({
      messages: state.messages.map((msg) => (predicate(msg) ? updater(msg) : msg)),
    })),

  addToolCall: (messageId, toolCall) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId ? { ...msg, toolCalls: [...(msg.toolCalls || []), toolCall] } : msg,
      ),
    })),

  updateToolCall: (messageId, toolCallId, update) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              toolCalls: msg.toolCalls?.map((tc) =>
                tc.id === toolCallId ? { ...tc, ...update } : tc,
              ),
            }
          : msg,
      ),
    })),

  appendTextDelta: (messageId, text) =>
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id !== messageId) return msg;
        const parts: MessagePart[] = msg.parts ? [...msg.parts] : [];
        const last = parts[parts.length - 1];
        if (last && last.type === "text") {
          parts[parts.length - 1] = { ...last, content: (last.content ?? "") + text };
        } else {
          parts.push({ id: newPartId(), type: "text", content: text });
        }
        return { ...msg, parts, content: msg.content + text };
      }),
    })),

  appendThinkingDelta: (messageId, text) =>
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id !== messageId) return msg;
        const parts: MessagePart[] = msg.parts ? [...msg.parts] : [];
        const last = parts[parts.length - 1];
        if (last && last.type === "thinking") {
          parts[parts.length - 1] = { ...last, content: (last.content ?? "") + text };
        } else {
          parts.push({ id: newPartId(), type: "thinking", content: text });
        }
        return { ...msg, parts, thinking: (msg.thinking ?? "") + text };
      }),
    })),

  addToolCallPart: (messageId, toolCall) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              parts: [...(msg.parts ?? []), { id: newPartId(), type: "tool", toolCall }],
              toolCalls: [...(msg.toolCalls || []), toolCall],
            }
          : msg,
      ),
    })),

  updateToolCallPart: (messageId, toolCallId, update) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId
          ? {
              ...msg,
              parts: msg.parts?.map((p) =>
                p.type === "tool" && p.toolCall && p.toolCall.id === toolCallId
                  ? { ...p, toolCall: { ...p.toolCall, ...update } }
                  : p,
              ),
              toolCalls: msg.toolCalls?.map((tc) =>
                tc.id === toolCallId ? { ...tc, ...update } : tc,
              ),
            }
          : msg,
      ),
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  clearMessages: () => set({ messages: [] }),
}));
