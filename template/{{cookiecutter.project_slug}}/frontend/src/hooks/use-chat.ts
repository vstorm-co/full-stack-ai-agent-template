"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { nanoid } from "nanoid";
import { useWebSocket } from "./use-websocket";
import { useChatStore, useAuthStore } from "@/stores";
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
import { useKBSelectionStore } from "@/stores";
{%- endif %}
import type {
  AskUserAnswer,
  AskUserQuestion,
  ChatMessageFile,
  Decision,
  PendingApproval,
  ToolCall,
  WSEvent,
} from "@/types";
import { WS_URL } from "@/lib/constants";
import { setUrlParam } from "@/lib/utils";
import { useConversationStore } from "@/stores";
{%- if cookiecutter.enable_deep_research %}
import { useResearchStore, useChatModeStore } from "@/stores";
import type { ContextUsage, ResearchTodo, SubagentStatus } from "@/types";
{%- endif %}
/** A message the user typed while the agent was busy / socket offline.
 *  Held outside the chat history until the drainer ships it. */
export interface QueuedMessage {
  id: string;
  content: string;
  fileIds?: string[];
  files?: ChatMessageFile[];
}

interface UseChatOptions {
  conversationId?: string | null;
  onConversationCreated?: (conversationId: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const { conversationId, onConversationCreated } = options;
  const { setCurrentConversationId, currentConversationId: currentConversationIdFromStore } =
    useConversationStore();
  const {
    messages,
    addMessage,
    updateMessage,
    appendTextDelta,
    appendThinkingDelta,
    addToolCallPart,
    updateToolCallPart,
    clearMessages,
  } = useChatStore();

  const [isProcessing, setIsProcessing] = useState(false);
  // Held in a ref instead of state because the WS handler reads it
  // synchronously: events arriving in the same tick (e.g. model_request_start
  // + text_delta in one server flush) need to see the just-created message id
  // without waiting for React's batched re-render. The handler never causes a
  // re-render based on this id, so state isn't needed.
  const currentMessageIdRef = useRef<string | null>(null);
  const setCurrentMessageId = useCallback((id: string | null) => {
    currentMessageIdRef.current = id;
  }, []);
  const currentGroupIdRef = useRef<string | null>(null);
  // Outbound queue: messages typed while agent is busy / socket offline. Held
  // here (not in the chat history) so the UI can surface them as cancellable
  // "pending" entries above the input. The ref is the source of truth for the
  // drainer effect; the parallel state triggers re-renders for the UI.
  const messageQueueRef = useRef<QueuedMessage[]>([]);
  const [queuedMessages, setQueuedMessages] = useState<QueuedMessage[]>([]);
  const modelRef = useRef<string | null>(null);
  const temperatureRef = useRef<number | null>(null);
  const thinkingEffortRef = useRef<"low" | "medium" | "high" | null>(null);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [pendingQuestions, setPendingQuestions] = useState<AskUserQuestion[] | null>(null);

  const handleWebSocketMessage = useCallback(
    (event: MessageEvent) => {
      const wsEvent: WSEvent = JSON.parse(event.data);

      const createNewMessage = (content: string): string => {
        if (currentMessageIdRef.current) {
          updateMessage(currentMessageIdRef.current, (msg) => ({
            ...msg,
            isStreaming: false,
          }));
        }

        const newMsgId = nanoid();
        // Use current conversationId from store to avoid closure issues
        const effectiveConversationId =
          currentConversationIdFromStore || conversationId || undefined;
        addMessage({
          id: newMsgId,
          role: "assistant",
          content,
          timestamp: new Date(),
          isStreaming: true,
          toolCalls: [],
          parts: content === "" ? [] : undefined,
          groupId: currentGroupIdRef.current || undefined,
          conversationId: effectiveConversationId,
          isTemporaryId: true,
        });
        setCurrentMessageId(newMsgId);
        return newMsgId;
      };

      switch (wsEvent.type) {
        case "conversation_created": {
          // Handle new conversation created by backend
          const { conversation_id } = wsEvent.data as { conversation_id: string };
          setCurrentConversationId(conversation_id);
          // Reflect the new ID in the URL so the page is refreshable + shareable.
          setUrlParam("id", conversation_id);
          // Update all messages that don't have a conversationId yet
          const { updateMessagesWhere } = useChatStore.getState();
          updateMessagesWhere(
            (msg) => !msg.conversationId,
            (msg) => ({ ...msg, conversationId: conversation_id }),
          );
          onConversationCreated?.(conversation_id);
          break;
        }

        case "message_saved": {
          // Assistant message was saved to database, update local ID to real database ID
          const { message_id } = wsEvent.data as { message_id: string };
          if (currentMessageIdRef.current) {
            // Update the current streaming message's ID to the real database ID
            updateMessage(currentMessageIdRef.current, (msg) => ({
              ...msg,
              id: message_id,
              isTemporaryId: false,
            }));
          } else {
            // Fallback: find the last assistant message with a temp ID
            // This handles cases where currentMessageId was already cleared
            const messages = useChatStore.getState().messages;
            const lastTemp = [...messages]
              .reverse()
              .find((msg) => msg.role === "assistant" && !!msg.isTemporaryId);
            if (lastTemp) {
              updateMessage(lastTemp.id, (msg) => ({
                ...msg,
                id: message_id,
                isTemporaryId: false,
              }));
            }
          }
          break;
        }

        case "model_request_start": {
          // PydanticAI/LangChain - create message immediately
          createNewMessage("");
          break;
        }

        case "text_delta": {
          // Append to the ordered parts timeline (extends the trailing
          // text part or starts a new one after a thinking/tool part).
          if (currentMessageIdRef.current) {
            const content = (wsEvent.data as { index: number; content: string }).content;
            appendTextDelta(currentMessageIdRef.current, content);
          }
          break;
        }

        case "thinking_delta": {
          // Reasoning trace from extended-thinking models — its own
          // ordered part so it renders before the tools/text that follow.
          if (!currentMessageIdRef.current) {
            createNewMessage("");
          }
          if (currentMessageIdRef.current) {
            const content = (wsEvent.data as { index: number; content: string }).content;
            appendThinkingDelta(currentMessageIdRef.current, content);
          }
          break;
        }

        case "llm_started":
        case "llm_completed": {
          // LLM lifecycle events - optionally show status
          break;
        }

        case "tool_call": {
          // Add tool call to current message
          if (currentMessageIdRef.current) {
            const { tool_name, args, tool_call_id } = wsEvent.data as {
              tool_name: string;
              args: Record<string, unknown>;
              tool_call_id: string;
            };
            const toolCall: ToolCall = {
              id: tool_call_id,
              name: tool_name,
              args,
              status: "running",
            };
            addToolCallPart(currentMessageIdRef.current, toolCall);
          }
          break;
        }

        case "tool_result": {
          // Update tool call with result
          if (currentMessageIdRef.current) {
            const { tool_call_id, content } = wsEvent.data as {
              tool_call_id: string;
              content: string;
            };
            updateToolCallPart(currentMessageIdRef.current, tool_call_id, {
              result: content,
              status: "completed",
            });
          }
          break;
        }

        case "final_result": {
          // Finalize message
          if (currentMessageIdRef.current) {
            const { output } = wsEvent.data as { output: string };
            // If the model returned text only via final_result (no streamed
            // text_delta), append it as the trailing text part.
            const fr = useChatStore
              .getState()
              .messages.find((m) => m.id === currentMessageIdRef.current);
            if (output && fr && !fr.content) {
              appendTextDelta(currentMessageIdRef.current, output);
            }
            updateMessage(currentMessageIdRef.current, (msg) => ({
              ...msg,
              isStreaming: false,
            }));
          }
          setIsProcessing(false);
          // Don't clear currentMessageId yet - we need it for message_saved event
          currentGroupIdRef.current = null;
          break;
        }

        case "error": {
          // Handle error
          if (currentMessageIdRef.current) {
            const id = currentMessageIdRef.current;
            const { message } = wsEvent.data as { message: string };
            const errText = `\n\n❌ Error: ${message || "Unknown error"}`;
            const cur = useChatStore.getState().messages.find((m) => m.id === id);
            if (cur?.parts) {
              appendTextDelta(id, errText);
            } else {
              updateMessage(id, (msg) => ({ ...msg, content: msg.content + errText }));
            }
            updateMessage(id, (msg) => ({ ...msg, isStreaming: false }));
          }
          setIsProcessing(false);
          break;
        }

        case "tool_approval_required": {
          // Human-in-the-Loop: AI wants to execute tools that need approval
          const { action_requests, review_configs } = wsEvent.data as {
            action_requests: Array<{
              id: string;
              tool_name: string;
              args: Record<string, unknown>;
            }>;
            review_configs: Array<{
              tool_name: string;
              allow_edit?: boolean;
              timeout?: number;
            }>;
          };
          setPendingApproval({
            actionRequests: action_requests,
            reviewConfigs: review_configs,
          });
          // Show pending tools in the current message
          if (currentMessageIdRef.current) {
            const id = currentMessageIdRef.current;
            const toolNames = action_requests.map((ar) => ar.tool_name).join(", ");
            const waitText = `\n\n⏸️ Waiting for approval: ${toolNames}`;
            const cur = useChatStore.getState().messages.find((m) => m.id === id);
            if (cur?.parts) {
              appendTextDelta(id, waitText);
            } else {
              updateMessage(id, (msg) => ({ ...msg, content: msg.content + waitText }));
            }
          }
          break;
        }

        case "ask_user": {
          const { questions } = wsEvent.data as {
            questions: { question: string; options: string[]; allow_custom: boolean }[];
          };
          setPendingQuestions(
            (questions ?? []).map((q) => ({
              question: q.question,
              options: q.options ?? [],
              allowCustom: q.allow_custom,
            })),
          );
          break;
        }

{%- if cookiecutter.enable_todo %}
        case "todo_event": {
          const { event_type, todo } = wsEvent.data as {
            event_type: string;
            todo: ResearchTodo;
          };
          useResearchStore.getState().applyTodoEvent(event_type, todo);
          break;
        }
{%- endif %}
{%- if cookiecutter.enable_subagents %}
        case "subagent_status": {
          useResearchStore.getState().upsertSubagent(wsEvent.data as SubagentStatus);
          break;
        }

        case "subagent_message": {
          useResearchStore.getState().addSubagentMessage(wsEvent.data as import("@/types").SubagentMessage);
          break;
        }
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
        case "context_usage": {
          useResearchStore.getState().setContextUsage(wsEvent.data as ContextUsage);
          break;
        }

        case "context_compacted": {
          useResearchStore.getState().incrementCompaction();
          break;
        }
{%- endif %}

        case "complete": {
          setIsProcessing(false);
          // Clear currentMessageId after complete (message_saved should have handled ID mapping)
          setCurrentMessageId(null);
          // The turn just debited credits server-side — nudge any mounted
          // billing view to refetch so the user doesn't see stale numbers.
          if (typeof window !== "undefined") {
            window.dispatchEvent(new Event("billing:refresh"));
          }
          break;
        }
      }
    },
    [
      // currentMessageId is read via currentMessageIdRef inside the handler,
      // so we deliberately omit it here — that's the whole point of the ref.
      addMessage,
      updateMessage,
      appendTextDelta,
      appendThinkingDelta,
      addToolCallPart,
      updateToolCallPart,
      setCurrentConversationId,
      setCurrentMessageId,
      onConversationCreated,
      currentConversationIdFromStore,
      conversationId,
    ],
  );

  // Access token lives in memory only (populated by login/refresh responses).
  // It is sent to the WS via Sec-WebSocket-Protocol rather than a URL query
  // string so it does not end up in access logs or Referer headers.
  const accessToken = useAuthStore((state) => state.accessToken);

  const wsUrl = `${WS_URL}/api/v1/ws/agent`;
  const wsProtocols = useMemo(
    () => (accessToken ? [`access_token.${accessToken}`, "chat"] : undefined),
    [accessToken],
  );

  // Guards against firing a token refresh on every backoff attempt — one
  // in-flight /me at a time is enough to recover a stale access token.
  const refreshingRef = useRef(false);

  const { isConnected, connect, disconnect, sendMessage } = useWebSocket({
    url: wsUrl,
    protocols: wsProtocols,
    onMessage: handleWebSocketMessage,
    // A dropped socket is often a stale access token. Refresh it so the
    // auto-reconnect (and the token-gated connect effect) uses a fresh one.
    // The hook only calls this on genuine drops (not deliberate disconnects),
    // and the ref keeps concurrent reconnect attempts from stampeding /me.
    onClose: () => {
      if (refreshingRef.current) return;
      refreshingRef.current = true;
      void (async () => {
        try {
          const res = await fetch("/api/auth/me");
          if (res.ok) {
            const data = (await res.json()) as { access_token?: string };
            if (data.access_token) useAuthStore.getState().setAccessToken(data.access_token);
          }
        } catch {
          // ignore — backoff reconnect will retry
        } finally {
          refreshingRef.current = false;
        }
      })();
    },
  });

  // Own the socket lifecycle here: only open once the in-memory access token is
  // available (the WS authenticates via Sec-WebSocket-Protocol). Connecting
  // before the token loads used to open a token-less socket that the server
  // rejects, triggering a reconnect storm + console errors on every page load.
  // When the token refreshes, `connect` changes identity → reconnect with it.
  useEffect(() => {
    if (!accessToken) return;
    connect();
    return () => disconnect();
  }, [accessToken, connect, disconnect]);

  const doSend = useCallback(
    (content: string, fileIds?: string[], files?: ChatMessageFile[]) => {
      const userMessageId = nanoid();
      addMessage({
        id: userMessageId,
        role: "user",
        content,
        timestamp: new Date(),
        conversationId: conversationId || undefined,
        fileIds,
        files,
      });
{%- if cookiecutter.enable_deep_research %}
      useResearchStore.getState().beginTurn(userMessageId);
{%- endif %}
      setIsProcessing(true);
      const payload: Record<string, unknown> = {
        message: content,
        conversation_id: conversationId || null,
      };
      if (fileIds?.length) payload.file_ids = fileIds;
      if (modelRef.current) payload.model = modelRef.current;
      if (temperatureRef.current !== null) payload.temperature = temperatureRef.current;
      if (thinkingEffortRef.current !== null) payload.thinking_effort = thinkingEffortRef.current;
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag %}
      const activeKBIds = useKBSelectionStore.getState().activeKBIds;
      if (activeKBIds.length) payload.active_knowledge_base_ids = activeKBIds;
{%- endif %}
{%- if cookiecutter.enable_deep_research %}
      payload.deep_research = useChatModeStore.getState().deepResearch;
{%- endif %}
      sendMessage(payload);
    },
    [addMessage, sendMessage, conversationId],
  );

  const sendChatMessage = useCallback(
    (content: string, fileIds?: string[], files?: ChatMessageFile[]) => {
      // Queue when the agent is busy OR the socket is offline. The queue is
      // surfaced above the input as pending entries the user can cancel; the
      // drainer effect below pops the head as soon as the agent is idle.
      if (isProcessing || !isConnected) {
        const id = nanoid();
        messageQueueRef.current.push({ id, content, fileIds, files });
        setQueuedMessages([...messageQueueRef.current]);
        return;
      }
      doSend(content, fileIds, files);
    },
    [isProcessing, isConnected, doSend],
  );

  const cancelQueued = useCallback((id: string) => {
    messageQueueRef.current = messageQueueRef.current.filter((q) => q.id !== id);
    setQueuedMessages([...messageQueueRef.current]);
  }, []);

  const clearQueued = useCallback(() => {
    messageQueueRef.current = [];
    setQueuedMessages([]);
  }, []);

  const sendResumeDecisions = useCallback(
    (decisions: Decision[]) => {
      setPendingApproval(null);

      // Update message to show decisions were made
      if (currentMessageIdRef.current) {
        const approvedCount = decisions.filter((d) => d.type === "approve").length;
        const editedCount = decisions.filter((d) => d.type === "edit").length;
        const rejectedCount = decisions.filter((d) => d.type === "reject").length;

        const summaryParts: string[] = [];
        if (approvedCount > 0) summaryParts.push(`${approvedCount} approved`);
        if (editedCount > 0) summaryParts.push(`${editedCount} edited`);
        if (rejectedCount > 0) summaryParts.push(`${rejectedCount} rejected`);

        updateMessage(currentMessageIdRef.current, (msg) => ({
          ...msg,
          content: msg.content.replace(
            /\n\n⏸️ Waiting for approval:.*$/,
            `\n\n✅ Decisions: ${summaryParts.join(", ")}`,
          ),
        }));
      }

      // Send resume message to WebSocket
      sendMessage({
        type: "resume",
        decisions: decisions.map((d) => {
          if (d.type === "edit" && d.editedAction) {
            return {
              type: "edit",
              edited_action: d.editedAction,
            };
          }
          return { type: d.type };
        }),
      });
    },
    [updateMessage, sendMessage],
  );

  const sendAskUserResponses = useCallback(
    (answers: AskUserAnswer[]) => {
      if (!isConnected) return;
      setPendingQuestions(null);
      sendMessage({ type: "ask_user_response", answers });
    },
    [isConnected, sendMessage],
  );

  const stopGeneration = useCallback(() => {
    sendMessage({ type: "stop" });
    if (currentMessageIdRef.current) {
      updateMessage(currentMessageIdRef.current, (msg) => ({ ...msg, isStreaming: false }));
    }
    setCurrentMessageId(null);
    currentGroupIdRef.current = null;
    setIsProcessing(false);
    setPendingApproval(null);
    setPendingQuestions(null);
{%- if cookiecutter.enable_deep_research %}
    useResearchStore.getState().markCurrentTurnStopped();
{%- endif %}
  }, [sendMessage, updateMessage, setCurrentMessageId]);

  // Drain message queue when processing finishes AND we're back online.
  // Re-runs on either flip so a reconnect after offline → drains; a busy turn
  // ending → drains the next one.
  useEffect(() => {
    if (isConnected && !isProcessing && messageQueueRef.current.length > 0) {
      const next = messageQueueRef.current.shift();
      setQueuedMessages([...messageQueueRef.current]);
      if (next) {
        // Small debounce so the UI shows the queue clearing visibly before
        // the next user bubble lands; also avoids racing the WS state flip.
        setTimeout(() => doSend(next.content, next.fileIds, next.files), 100);
      }
    }
  }, [isProcessing, isConnected, doSend]);

  return {
    messages,
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage: sendChatMessage,
    stopGeneration,
    clearMessages,
    queuedMessages,
    cancelQueued,
    clearQueued,
    setModel: (model: string | null) => {
      modelRef.current = model;
    },
    setTemperature: (temperature: number | null) => {
      temperatureRef.current = temperature;
    },
    setThinkingEffort: (effort: "low" | "medium" | "high" | null) => {
      thinkingEffortRef.current = effort;
    },
    // Human-in-the-Loop support
    pendingApproval,
    sendResumeDecisions,
    pendingQuestions,
    sendAskUserResponses,
  };
}
