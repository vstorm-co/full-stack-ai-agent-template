"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { nanoid } from "nanoid";
import { useWebSocket } from "./use-websocket";
{%- if cookiecutter.enable_rag %}
import { useChatStore, useAuthStore, useKBSelectionStore } from "@/stores";
{%- else %}
import { useChatStore, useAuthStore } from "@/stores";
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
    addToolCall,
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
  // Human-in-the-Loop: pending tool approval state
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [pendingQuestions, setPendingQuestions] = useState<AskUserQuestion[] | null>(null);

  const handleWebSocketMessage = useCallback(
    (event: MessageEvent) => {
      const wsEvent: WSEvent = JSON.parse(event.data);

      // Helper to create a new message
      const createNewMessage = (content: string): string => {
        // Mark previous message as not streaming before creating new one
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
          // Streamed turns (empty seed) use the ordered parts timeline.
          // CrewAI seeds content directly → keep parts undefined so it
          // falls back to the legacy layout (it's already multi-message).
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
          if (typeof window !== "undefined") {
            const url = new URL(window.location.href);
            if (url.searchParams.get("id") !== conversation_id) {
              url.searchParams.set("id", conversation_id);
              window.history.replaceState({}, "", url.toString());
            }
          }
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

        case "crew_start":
        case "crew_started": {
          // CrewAI - generate groupId for this execution, wait for agent events
          currentGroupIdRef.current = nanoid();
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

        // CrewAI agent events - each agent gets its own message container
        case "agent_started": {
          const { agent } = wsEvent.data as {
            agent: string;
            task: string;
          };
          // Create NEW message for this agent (groupId read from ref)
          createNewMessage(`🤖 **${agent}** is starting...`);
          break;
        }

        case "agent_completed": {
          // Finalize current agent's message with output
          if (currentMessageIdRef.current) {
            const { agent, output } = wsEvent.data as {
              agent: string;
              output: string;
            };
            updateMessage(currentMessageIdRef.current, (msg) => ({
              ...msg,
              content: `✅ **${agent}**\n\n${output}`,
              isStreaming: false,
            }));
          }
          break;
        }

        // CrewAI task events - create separate message for each task
        case "task_started": {
          const { description, agent } = wsEvent.data as {
            task_id: string;
            description: string;
            agent: string;
          };
          // Create NEW message for this task (groupId read from ref)
          createNewMessage(`📋 **Task** (${agent})\n\n${description}`);
          break;
        }

        case "task_completed": {
          // Finalize the task message
          if (currentMessageIdRef.current) {
            const { output, agent } = wsEvent.data as {
              task_id: string;
              output: string;
              agent: string;
            };
            updateMessage(currentMessageIdRef.current, (msg) => ({
              ...msg,
              content: `✅ **Task completed** (${agent})\n\n${output}`,
              isStreaming: false,
            }));
          }
          break;
        }

        // CrewAI tool events
        case "tool_started": {
          if (currentMessageIdRef.current) {
            const { tool_name, tool_args, agent } = wsEvent.data as {
              tool_name: string;
              tool_args: string;
              agent: string;
            };
            const toolCall: ToolCall = {
              id: nanoid(),
              name: tool_name,
              args: { input: tool_args, agent },
              status: "running",
            };
            addToolCall(currentMessageIdRef.current, toolCall);
          }
          break;
        }

        case "tool_finished": {
          // Tool finished - update last tool call status
          if (currentMessageIdRef.current) {
            const { tool_name, tool_result } = wsEvent.data as {
              tool_name: string;
              tool_result: string;
              agent: string;
            };
            // Find and update the matching tool call
            updateMessage(currentMessageIdRef.current, (msg) => {
              const toolCalls = msg.toolCalls || [];
              const lastToolCall = toolCalls.find(
                (tc) => tc.name === tool_name && tc.status === "running",
              );
              if (lastToolCall) {
                return {
                  ...msg,
                  toolCalls: toolCalls.map((tc) =>
                    tc.id === lastToolCall.id
                      ? { ...tc, result: tool_result, status: "completed" as const }
                      : tc,
                  ),
                };
              }
              return msg;
            });
          }
          break;
        }

        // LLM events (can be used for showing thinking status)
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
{%- if cookiecutter.enable_deep_research %}

        case "todo_event": {
          const { event_type, todo } = wsEvent.data as {
            event_type: string;
            todo: ResearchTodo;
          };
          useResearchStore.getState().applyTodoEvent(event_type, todo);
          break;
        }

        case "subagent_status": {
          useResearchStore.getState().upsertSubagent(wsEvent.data as SubagentStatus);
          break;
        }

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
      addToolCall,
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

  const { isConnected, connect, disconnect, sendMessage } = useWebSocket({
    url: wsUrl,
    protocols: wsProtocols,
    onMessage: handleWebSocketMessage,
  });

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
{%- if cookiecutter.enable_rag %}
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

  // Human-in-the-Loop: send resume message with user decisions
  const sendResumeDecisions = useCallback(
    (decisions: Decision[]) => {
      // Clear pending approval state
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
