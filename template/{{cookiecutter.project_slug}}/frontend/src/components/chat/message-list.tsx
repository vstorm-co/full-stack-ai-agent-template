"use client";

import type { ChatMessage } from "@/types";
import { MessageItem } from "./message-item";
{%- if cookiecutter.enable_deep_research %}
import { ResearchPanel, RESEARCH_TOOL_NAMES } from "./research-panel";
{%- endif %}

interface MessageListProps {
  messages: ChatMessage[];
  onRegenerate?: (messageId: string) => void;
}
{%- if cookiecutter.enable_deep_research %}

function messageHasResearch(m: ChatMessage): boolean {
  if (
    m.parts?.some(
      (p) => p.type === "tool" && !!p.toolCall && RESEARCH_TOOL_NAMES.has(p.toolCall.name),
    )
  ) {
    return true;
  }
  return Boolean(m.toolCalls?.some((tc) => RESEARCH_TOOL_NAMES.has(tc.name)));
}
{%- endif %}

export function MessageList({ messages, onRegenerate }: MessageListProps) {
  // Calculate group positions for timeline connector
  const getGroupPosition = (
    message: ChatMessage,
  ): "first" | "middle" | "last" | "single" | undefined => {
    if (!message.groupId) return undefined;

    const groupMessages = messages.filter((m) => m.groupId === message.groupId);
    if (groupMessages.length <= 1) return "single";

    const groupIndex = groupMessages.findIndex((m) => m.id === message.id);
    if (groupIndex === 0) return "first";
    if (groupIndex === groupMessages.length - 1) return "last";
    return "middle";
  };

  // Only allow regenerating the most recent assistant message — older ones
  // would diverge the transcript in a confusing way.
  const lastAssistantIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i]?.role === "assistant") return i;
    }
    return -1;
  })();
{%- if cookiecutter.enable_deep_research %}

  const panelTurnByAnchor = new Map<string, string>();
  {
    let turnId: string | null = null;
    let placed = false;
    for (const m of messages) {
      if (m.role === "user") {
        turnId = m.id;
        placed = false;
      } else if (!placed && turnId && messageHasResearch(m)) {
        panelTurnByAnchor.set(m.id, turnId);
        placed = true;
      }
    }
  }
{%- endif %}

  return (
    <div className="space-y-0">
{%- if cookiecutter.enable_deep_research %}
      {messages.map((message, index) => {
        const panelTurnId = panelTurnByAnchor.get(message.id);
        return (
          <div key={message.id}>
            {panelTurnId && <ResearchPanel turnId={panelTurnId} />}
            <MessageItem
              message={message}
              groupPosition={getGroupPosition(message)}
              onRegenerate={
                onRegenerate && index === lastAssistantIndex && !message.isStreaming
                  ? () => onRegenerate(message.id)
                  : undefined
              }
            />
          </div>
        );
      })}
{%- else %}
      {messages.map((message, index) => (
        <MessageItem
          key={message.id}
          message={message}
          groupPosition={getGroupPosition(message)}
          onRegenerate={
            onRegenerate && index === lastAssistantIndex && !message.isStreaming
              ? () => onRegenerate(message.id)
              : undefined
          }
        />
      ))}
{%- endif %}
    </div>
  );
}
