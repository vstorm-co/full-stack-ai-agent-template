"use client";

import { useEffect, useRef, useCallback } from "react";
import { useChat } from "@/hooks";
import { ChatControls } from "./chat-controls";
import { ChatEmptyState } from "./chat-empty-state";
import { ChatInput } from "./chat-input";
import { FilePreviewPanel } from "./file-preview-panel";
import { MessageList } from "./message-list";
import { PendingMessages } from "./pending-messages";
import { ToolApprovalDialog } from "./tool-approval-dialog";
import { QuestionPrompt } from "@/components/ui";
import type { PendingApproval, AskUserQuestion, AskUserAnswer, Decision } from "@/types";
import { useConversationStore, useChatStore } from "@/stores";
{%- if cookiecutter.enable_deep_research %}
import { useResearchStore } from "@/stores";
{%- endif %}
import { useConversations } from "@/hooks";
{%- if cookiecutter.use_auth %}
import { useSlashCommands } from "@/hooks";
{%- endif %}

export function ChatContainer() {
  return <AuthenticatedChatContainer />;
}

function AuthenticatedChatContainer() {
  const {
    currentConversationId,
    currentMessages,
    isLoading: isConversationLoading,
  } = useConversationStore();
  const { addMessage: addChatMessage } = useChatStore();
  const { fetchConversations } = useConversations();
  const prevConversationIdRef = useRef<string | null | undefined>(undefined);

  const handleConversationCreated = useCallback(() => {
    fetchConversations();
  }, [fetchConversations]);

  const {
    messages,
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage,
    stopGeneration,
    clearMessages,
    queuedMessages,
    cancelQueued,
    clearQueued,
    setModel,
    setTemperature,
    setThinkingEffort,
    pendingApproval,
    sendResumeDecisions,
    pendingQuestions,
    sendAskUserResponses,
  } = useChat({
    conversationId: currentConversationId,
    onConversationCreated: handleConversationCreated,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Clear messages when conversation changes, but NOT when going from null to a new ID
  // (that happens when a new chat is saved - we want to keep the messages)
  useEffect(() => {
    const prevId = prevConversationIdRef.current;
    const currId = currentConversationId;

    // Skip initial mount
    if (prevId === undefined) {
      prevConversationIdRef.current = currId;
      return;
    }

    // Clear messages when:
    // 1. Going from a conversation to null (new chat)
    // 2. Switching between two different conversations
    // Do NOT clear when going from null to a conversation (new chat being saved)
    const shouldClear =
      currId === null || // Going to new chat
      (prevId !== null && prevId !== currId); // Switching between conversations

    if (shouldClear) {
      clearMessages();
{%- if cookiecutter.enable_deep_research %}
      useResearchStore.getState().resetAll();
{%- endif %}
      // Drop any pending queue when switching threads — those messages were
      // typed in the previous conversation's context, sending them into a
      // different conversation would surprise the user.
      clearQueued();
    }

    prevConversationIdRef.current = currId;
  }, [currentConversationId, clearMessages, clearQueued]);

  // Load messages from conversation store when switching to a saved conversation
  useEffect(() => {
    if (currentMessages.length > 0) {
      clearMessages();
      currentMessages.forEach((msg) => {
        const toolCalls = msg.tool_calls?.map((tc) => ({
          id: tc.tool_call_id,
          name: tc.tool_name,
          args: tc.args,
          result: tc.result,
          status: (tc.status === "failed" ? "error" : tc.status) as
            | "pending"
            | "running"
            | "completed"
            | "error",
        }));
        // Reconstruct an ordered timeline for assistant turns. The DB has no
        // interleaving metadata, so we use the realistic order: tools ran
        // before the final answer → tool parts first, then the text.
        const parts =
          msg.role === "assistant"
            ? [
                ...(toolCalls ?? []).map((tc) => ({
                  id: tc.id,
                  type: "tool" as const,
                  toolCall: tc,
                })),
                ...(msg.content
                  ? [
                      {
                        id: `${msg.id}-text`,
                        type: "text" as const,
                        content: msg.content,
                      },
                    ]
                  : []),
              ]
            : undefined;
        addChatMessage({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at),
          conversationId: msg.conversation_id,
          toolCalls,
          parts,
          user_rating: msg.user_rating ?? undefined,
          rating_count: msg.rating_count ?? undefined,
          files:
            "files" in msg &&
            Array.isArray((msg as unknown as { files?: { id: string; filename: string }[] }).files)
              ? (
                  msg as unknown as {
                    files: {
                      id: string;
                      filename: string;
                      mime_type: string;
                      file_type: string;
                    }[];
                  }
                ).files
              : undefined,
          fileIds:
            "files" in msg && Array.isArray((msg as unknown as { files?: unknown[] }).files)
              ? (msg as unknown as { files: { id: string }[] }).files.map((f) => f.id)
              : undefined,
        });
      });
    }
  }, [currentMessages, addChatMessage, clearMessages]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    // Only auto-scroll if user is already near the bottom
    const isNearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 150;
    if (isNearBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);
  {%- if cookiecutter.use_auth %}
  const { commands: slashCommands } = useSlashCommands();
  {%- endif %}

  const handleRegenerate = useCallback(
    (assistantMessageId: string) => {
      const idx = messages.findIndex((m) => m.id === assistantMessageId);
      if (idx < 0) return;
      // Walk backwards to find the user message that prompted this turn.
      for (let i = idx - 1; i >= 0; i--) {
        const m = messages[i];
        if (m?.role === "user") {
          sendMessage(m.content, m.fileIds, m.files);
          return;
        }
      }
    },
    [messages, sendMessage],
  );

  // Slash command handlers — passed down to ChatInput so the / palette can
  // run them locally without going through the agent.
  const slashContext = {
    clearChat: clearMessages,
    regenerateLast: () => {
      // Find the last assistant message and trigger regenerate.
      for (let i = messages.length - 1; i >= 0; i--) {
        const m = messages[i];
        if (m && m.role === "assistant") {
          handleRegenerate(m.id);
          return;
        }
      }
    },
    openSettings: () => {
      // Best-effort: focus the settings popover trigger if it's mounted.
      document.querySelector<HTMLButtonElement>("[data-chat-settings-trigger]")?.click();
    },
  };

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      isLoadingConversation={
        currentConversationId !== null && isConversationLoading && messages.length === 0
      }
      sendMessage={sendMessage}
      onModelChange={setModel}
      onTemperatureChange={setTemperature}
      onThinkingEffortChange={setThinkingEffort}
      onRegenerate={handleRegenerate}
      slashContext={slashContext}
      {%- if cookiecutter.use_auth %}
      slashCommands={slashCommands}
      {%- endif %}
      queuedMessages={queuedMessages}
      onCancelQueued={cancelQueued}
      messagesEndRef={messagesEndRef}
      scrollContainerRef={scrollContainerRef}
      pendingApproval={pendingApproval}
      onResumeDecisions={sendResumeDecisions}
      pendingQuestions={pendingQuestions}
      onAnswerQuestions={sendAskUserResponses}
      onStop={stopGeneration}
    />
  );
}

interface ChatUIProps {
  messages: import("@/types").ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  /** True while a saved conversation is being loaded — show a skeleton, not empty state. */
  isLoadingConversation?: boolean;
  sendMessage: (
    content: string,
    fileIds?: string[],
    files?: import("@/types").ChatMessageFile[],
  ) => void;
  onModelChange?: (model: string | null) => void;
  onTemperatureChange?: (temperature: number | null) => void;
  onThinkingEffortChange?: (effort: "low" | "medium" | "high" | null) => void;
  onRegenerate?: (messageId: string) => void;
  slashContext?: import("./slash-commands").SlashCommandContext;
  slashCommands?: import("./slash-commands").SlashCommand[];
  queuedMessages?: import("@/hooks/use-chat").QueuedMessage[];
  onCancelQueued?: (id: string) => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  scrollContainerRef: React.RefObject<HTMLDivElement | null>;
  pendingApproval?: PendingApproval | null;
  onResumeDecisions?: (decisions: Decision[]) => void;
  pendingQuestions?: AskUserQuestion[] | null;
  onAnswerQuestions?: (answers: AskUserAnswer[]) => void;
  onStop?: () => void;
}

function ChatUI({
  messages,
  isConnected,
  isProcessing,
  isLoadingConversation,
  sendMessage,
  onModelChange,
  onTemperatureChange,
  onThinkingEffortChange,
  onRegenerate,
  slashContext,
  slashCommands,
  queuedMessages,
  onCancelQueued,
  messagesEndRef,
  scrollContainerRef,
  pendingApproval,
  onResumeDecisions,
  pendingQuestions,
  onAnswerQuestions,
  onStop,
}: ChatUIProps) {
  return (
    <div className="flex h-full w-full">
      <div className="mx-auto flex h-full max-w-4xl min-w-0 flex-1 flex-col">
        <div
          ref={scrollContainerRef}
          className="flex-1 scrollbar-thin overflow-y-auto px-2 py-4 sm:px-4 sm:py-6"
        >
          {isLoadingConversation ? (
            <ConversationSkeleton />
          ) : messages.length === 0 ? (
            <div className="flex h-full items-center">
              <ChatEmptyState onPick={(prompt) => sendMessage(prompt)} />
            </div>
          ) : (
            <MessageList messages={messages} onRegenerate={onRegenerate} />
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Human-in-the-Loop: Tool Approval Dialog */}
        {pendingApproval && onResumeDecisions && (
          <div className="px-2 pb-2 sm:px-4 sm:pb-2">
            <ToolApprovalDialog
              actionRequests={pendingApproval.actionRequests}
              reviewConfigs={pendingApproval.reviewConfigs}
              onDecisions={onResumeDecisions}
              disabled={!isConnected}
            />
          </div>
        )}

        {/* ask_user: interactive question card while the run is paused */}
        {pendingQuestions && pendingQuestions.length > 0 && onAnswerQuestions && (
          <div className="px-2 pb-2 sm:px-4 sm:pb-2">
            <QuestionPrompt
              questions={pendingQuestions}
              disabled={!isConnected}
              onComplete={onAnswerQuestions}
            />
          </div>
        )}

        <div className="px-2 pb-2 sm:px-4 sm:pb-4">
          {queuedMessages && queuedMessages.length > 0 && onCancelQueued && (
            <PendingMessages messages={queuedMessages} onCancel={onCancelQueued} />
          )}
          <div className="bg-card border-foreground/10 focus-within:border-foreground/30 rounded-2xl border shadow-sm transition-colors">
            <div className="px-3 pt-3 sm:px-4 sm:pt-4">
              <ChatInput
                onSend={sendMessage}
                disabled={
                  !isConnected ||
                  !!pendingApproval ||
                  !!(pendingQuestions && pendingQuestions.length)
                }
                isProcessing={isProcessing}
                onStop={onStop}
                slashContext={slashContext}
                commands={slashCommands}
              />
            </div>
            <div className="border-foreground/8 flex items-center justify-between border-t px-3 py-2 sm:px-4">
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 font-mono text-[10px] tracking-wider uppercase ${isConnected ? "text-foreground/55" : "text-destructive"}`}
                >
                  <span
                    className={`inline-block h-1.5 w-1.5 rounded-full ${
                      isConnected ? "bg-brand" : "bg-destructive"
                    } ${isConnected ? "animate-pulse" : ""}`}
                  />
                  {isConnected ? "Live" : "Offline"}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <ChatControls
                  onModelChange={onModelChange}
                  onTemperatureChange={onTemperatureChange}
                  onThinkingEffortChange={onThinkingEffortChange}
                />
              </div>
            </div>
          </div>
          <p className="text-foreground/40 mt-2 text-center font-mono text-[10px] tracking-wider uppercase">
            AI can make mistakes. Verify important information.
          </p>
        </div>
      </div>
      <FilePreviewPanel />
    </div>
  );
}

function ConversationSkeleton() {
  // Two faux message bubbles — left (assistant) and right (user) — at the rough
  // proportions a real exchange has, so the layout doesn't pop when messages
  // arrive. Just enough motion to signal "loading", no shimmer chrome.
  return (
    <div className="space-y-6 py-4 sm:py-6">
      <div className="flex gap-2 sm:gap-4">
        <div className="bg-foreground/10 h-8 w-8 shrink-0 animate-pulse rounded-full sm:h-9 sm:w-9" />
        <div className="flex max-w-[85%] flex-1 flex-col gap-2">
          <div className="bg-foreground/10 h-4 w-1/3 animate-pulse rounded-md" />
          <div className="bg-foreground/8 h-4 w-4/5 animate-pulse rounded-md" />
          <div className="bg-foreground/8 h-4 w-2/3 animate-pulse rounded-md" />
        </div>
      </div>
      <div className="flex flex-row-reverse gap-2 sm:gap-4">
        <div className="bg-foreground/10 h-8 w-8 shrink-0 animate-pulse rounded-full sm:h-9 sm:w-9" />
        <div className="flex max-w-[85%] flex-1 flex-col items-end gap-2">
          <div className="bg-foreground/10 h-4 w-1/4 animate-pulse rounded-md" />
          <div className="bg-foreground/8 h-4 w-3/5 animate-pulse rounded-md" />
        </div>
      </div>
      <div className="flex gap-2 sm:gap-4">
        <div className="bg-foreground/10 h-8 w-8 shrink-0 animate-pulse rounded-full sm:h-9 sm:w-9" />
        <div className="flex max-w-[85%] flex-1 flex-col gap-2">
          <div className="bg-foreground/8 h-4 w-3/4 animate-pulse rounded-md" />
          <div className="bg-foreground/8 h-4 w-1/2 animate-pulse rounded-md" />
        </div>
      </div>
    </div>
  );
}
