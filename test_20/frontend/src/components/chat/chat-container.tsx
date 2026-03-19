"use client";

import { useEffect, useRef, useCallback } from "react";
import { useChat, useLocalChat } from "@/hooks";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { ToolApprovalDialog } from "./tool-approval-dialog";
import { Bot } from "lucide-react";
import type { PendingApproval, Decision } from "@/types";
import { useConversationStore, useChatStore, useAuthStore } from "@/stores";
import { useConversations } from "@/hooks";
interface ChatContainerProps {
  useLocalStorage?: boolean;
}

export function ChatContainer({ useLocalStorage = false }: ChatContainerProps) {
  const { isAuthenticated } = useAuthStore();

  const shouldUseLocal = useLocalStorage || !isAuthenticated;

  if (shouldUseLocal) {
    return <LocalChatContainer />;
  }

  return <AuthenticatedChatContainer />;
}

function AuthenticatedChatContainer() {
  const { currentConversationId, currentMessages } = useConversationStore();
  const { addMessage: addChatMessage } = useChatStore();
  const { fetchConversations } = useConversations();
  const prevConversationIdRef = useRef<string | null | undefined>(undefined);

  const handleConversationCreated = useCallback(
    (conversationId: string) => {
      fetchConversations();
    },
    [fetchConversations]
  );

  const {
    messages,
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
    pendingApproval,
    sendResumeDecisions,
  } = useChat({
    conversationId: currentConversationId,
    onConversationCreated: handleConversationCreated,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    }

    prevConversationIdRef.current = currId;
  }, [currentConversationId, clearMessages]);

  // Load messages from conversation store when switching to a saved conversation
  useEffect(() => {
    if (currentMessages.length > 0) {
      currentMessages.forEach((msg) => {
        addChatMessage({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at),
          toolCalls: msg.tool_calls?.map((tc) => ({
            id: tc.tool_call_id,
            name: tc.tool_name,
            args: tc.args,
            result: tc.result,
            status: tc.status === "failed" ? "error" : tc.status,
          })),
          fileIds: "files" in msg && Array.isArray((msg as unknown as { files?: unknown[] }).files)
            ? ((msg as unknown as { files: { id: string }[] }).files).map((f) => f.id)
            : undefined,
        });
      });
    }
  }, [currentMessages, addChatMessage]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      sendMessage={sendMessage}

      messagesEndRef={messagesEndRef}
      pendingApproval={pendingApproval}
      onResumeDecisions={sendResumeDecisions}
    />
  );
}

function LocalChatContainer() {
  const {
    messages,
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
    pendingApproval,
    sendResumeDecisions,
  } = useLocalChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <ChatUI
      messages={messages}
      isConnected={isConnected}
      isProcessing={isProcessing}
      sendMessage={sendMessage}

      messagesEndRef={messagesEndRef}
      pendingApproval={pendingApproval}
      onResumeDecisions={sendResumeDecisions}
    />
  );
}

interface ChatUIProps {
  messages: import("@/types").ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  sendMessage: (content: string, fileIds?: string[]) => void;

  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  // Human-in-the-Loop support
  pendingApproval?: PendingApproval | null;
  onResumeDecisions?: (decisions: Decision[]) => void;
}

function ChatUI({
  messages,
  isConnected,
  isProcessing,
  sendMessage,
  messagesEndRef,
  pendingApproval,
  onResumeDecisions,
}: ChatUIProps) {
  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col">
      <div className="scrollbar-thin flex-1 overflow-y-auto px-2 py-4 sm:px-4 sm:py-6">
        {messages.length === 0 ? (
          <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-4">
            <div className="bg-secondary flex h-14 w-14 items-center justify-center rounded-full sm:h-16 sm:w-16">
              <Bot className="h-7 w-7 sm:h-8 sm:w-8" />
            </div>
            <div className="px-4 text-center">
              <p className="text-foreground text-base font-medium sm:text-lg">AI Assistant</p>
              <p className="text-sm">Start a conversation to get help</p>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
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

      <div className="px-2 pb-2 sm:px-4 sm:pb-4">
        <div className="bg-card rounded-xl border p-3 shadow-sm sm:p-4">
          {/* Status indicator */}
          <div className="mb-2 flex items-center gap-1.5">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`}
            />
            <span className="text-muted-foreground text-[11px]">
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
          <ChatInput
            onSend={sendMessage}
            disabled={!isConnected || isProcessing || !!pendingApproval}
            isProcessing={isProcessing}
          />
        </div>
      </div>
    </div>
  );
}
