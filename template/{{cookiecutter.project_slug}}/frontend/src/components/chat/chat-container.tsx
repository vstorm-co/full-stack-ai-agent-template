"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useChat } from "@/hooks";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";
import { ToolApprovalDialog } from "./tool-approval-dialog";
import { Bot, ChevronDown, Check } from "lucide-react";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui";
import type { PendingApproval, Decision } from "@/types";
import { useConversationStore, useChatStore, useAuthStore } from "@/stores";
import { useConversations } from "@/hooks";

export function ChatContainer() {
  return <AuthenticatedChatContainer />;
}

function AuthenticatedChatContainer() {
  const { currentConversationId, currentMessages } = useConversationStore();
  const { addMessage: addChatMessage } = useChatStore();
  const { fetchConversations } = useConversations();
  const prevConversationIdRef = useRef<string | null | undefined>(undefined);

  const handleConversationCreated = useCallback((conversationId: string) => {
    fetchConversations();
  }, [fetchConversations]);

  const {
    messages,
    isConnected,
    isProcessing,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
    setModel,
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
      clearMessages();
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
  }, [currentMessages, addChatMessage, clearMessages]);

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
      onModelChange={setModel}
      messagesEndRef={messagesEndRef}
      pendingApproval={pendingApproval}
      onResumeDecisions={sendResumeDecisions}
    />
  );
}

function ModelSelector({ onChange }: { onChange: (model: string | null) => void }) {
  const [availableModels, setAvailableModels] = useState<{value: string; label: string}[]>([
    { value: "", label: "Default" },
  ]);
  const [selected, setSelected] = useState(availableModels[0]);

  useEffect(() => {
    fetch("/api/v1/agent/models", { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.models) {
          const models = [
            { value: "", label: `Default (${data.default})` },
            ...data.models.map((m: string) => ({ value: m, label: m })),
          ];
          setAvailableModels(models);
          setSelected(models[0]);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors">
          {selected.label}
          <ChevronDown className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {availableModels.map((m) => (
          <DropdownMenuItem key={m.value} onClick={() => { setSelected(m); onChange(m.value || null); }} className="flex items-center justify-between text-xs">
            {m.label}
            {selected.value === m.value && <Check className="h-3.5 w-3.5" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

interface ChatUIProps {
  messages: import("@/types").ChatMessage[];
  isConnected: boolean;
  isProcessing: boolean;
  sendMessage: (content: string, fileIds?: string[]) => void;
  onModelChange?: (model: string | null) => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  pendingApproval?: PendingApproval | null;
  onResumeDecisions?: (decisions: Decision[]) => void;
}

function ChatUI({
  messages,
  isConnected,
  isProcessing,
  sendMessage,
  onModelChange,
  messagesEndRef,
  pendingApproval,
  onResumeDecisions,
}: ChatUIProps) {
  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
      <div className="flex-1 overflow-y-auto px-2 py-4 sm:px-4 sm:py-6 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-4">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-secondary flex items-center justify-center">
              <Bot className="h-7 w-7 sm:h-8 sm:w-8" />
            </div>
            <div className="text-center px-4">
              <p className="text-base sm:text-lg font-medium text-foreground">AI Assistant</p>
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
        <div className="rounded-xl border bg-card shadow-sm">
          <div className="px-3 pt-3 sm:px-4 sm:pt-4">
            <ChatInput
              onSend={sendMessage}
              disabled={!isConnected || !!pendingApproval}
              isProcessing={isProcessing}
            />
          </div>
          <div className="flex items-center justify-between px-3 pb-2 sm:px-4 sm:pb-3">
            <div className="flex items-center gap-1">
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`}
              />
            </div>
            {onModelChange && (
              <ModelSelector onChange={onModelChange} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
