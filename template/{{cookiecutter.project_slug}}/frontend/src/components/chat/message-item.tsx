"use client";

import { cn } from "@/lib/utils";
import type { ChatMessage, ChatMessageFile } from "@/types";
import { ToolCallCard } from "./tool-call-card";
import { MarkdownContent } from "./markdown-content";
import { CopyButton } from "./copy-button";
import { RatingButtons } from "./rating-buttons";
import { useChatStore, useFilePreviewStore } from "@/stores";
import { Bot, FileText, Paperclip, RefreshCw, User } from "lucide-react";
import Image from "next/image";
import { useAuthStore } from "@/stores";
import { getFileUrl } from "@/lib/file-api";
{%- if cookiecutter.enable_deep_research %}
import type { MessagePart } from "@/types";
import { RESEARCH_TOOL_NAMES } from "./research-panel";
{%- endif %}

interface MessageItemProps {
  message: ChatMessage;
  groupPosition?: "first" | "middle" | "last" | "single";
  onRegenerate?: () => void;
}

export function MessageItem({ message, groupPosition, onRegenerate }: MessageItemProps) {
  const isUser = message.role === "user";
  const updateMessage = useChatStore((state) => state.updateMessage);
  const openPreview = useFilePreviewStore((s) => s.open);
  const { user: authUser } = useAuthStore();
  const isGrouped = groupPosition && groupPosition !== "single";
{%- if cookiecutter.enable_deep_research %}

  if (!isUser) {
    const stepParts = message.parts ?? [];
    const hasFiles = (message.files?.length ?? 0) > 0 || (message.fileIds?.length ?? 0) > 0;
    const showPlaceholder =
      message.isStreaming &&
      !message.content &&
      stepParts.length === 0 &&
      (!message.toolCalls || message.toolCalls.length === 0);
    const hasVisibleParts =
      stepParts.length > 0
        ? visibleParts(stepParts).some(
            (p) =>
              (p.type === "thinking" && Boolean(p.content)) ||
              (p.type === "tool" && Boolean(p.toolCall)) ||
              (p.type === "text" && Boolean(p.content)),
          )
        : Boolean(message.thinking) ||
          Boolean(message.content) ||
          Boolean(message.toolCalls?.some((tc) => !RESEARCH_TOOL_NAMES.has(tc.name)));
    if (!showPlaceholder && !hasVisibleParts && !hasFiles) return null;
  }
{%- endif %}

  return (
    <div
      className={cn(
        "group relative flex gap-2 overflow-visible sm:gap-4",
        isGrouped ? "py-2 sm:py-3" : "py-3 sm:py-4",
        isUser && "flex-row-reverse",
      )}
    >
      {/* Timeline connector line for grouped messages */}
      {isGrouped && !isUser && (
        <div
          className="absolute left-[15px] w-0.5 bg-orange-500/40 sm:left-[17px]"
          style={
            groupPosition === "first"
              ? { top: "24px", bottom: "0" }
              : groupPosition === "last"
                ? { top: "0", height: "24px" }
                : { top: "0", bottom: "0" }
          }
        />
      )}

      <div
        className={cn(
          "z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-full sm:h-9 sm:w-9",
          isUser ? "bg-primary text-primary-foreground" : "bg-orange-500/10 text-orange-500",
          isGrouped && !isUser && "ring-background ring-2",
        )}
      >
        {isUser && authUser?.avatar_url ? (
          <Image
            src={`/api/users/avatar/${authUser.id}`}
            alt=""
            width={36}
            height={36}
            className="h-full w-full object-cover"
            unoptimized
          />
        ) : isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4 sm:h-5 sm:w-5" />
        )}
      </div>

      <div
        className={cn(
          "max-w-[88%] flex-1 space-y-2 overflow-hidden sm:max-w-[85%]",
          isUser && "flex flex-col items-end",
        )}
      >
        {/* Attachments — images render as previews, others as file chips */}
        {isUser &&
          (() => {
            const attachments: AttachmentDisplay[] =
              message.files && message.files.length > 0
                ? message.files.map((f) => ({ kind: kindFor(f), file: f }))
                : (message.fileIds ?? []).map((id) => ({ kind: "unknown" as const, id }));
            if (attachments.length === 0) return null;
            return (
              <div className="flex flex-wrap gap-2">
                {attachments.map((att) =>
                  att.kind === "image" ? (
                    <button
                      type="button"
                      key={att.file.id}
                      onClick={() => openPreview(att.file)}
                      className="hover:ring-foreground/30 block overflow-hidden rounded-xl border ring-2 ring-transparent transition-all"
                      title={`Open ${att.file.filename}`}
                    >
                      <Image
                        src={getFileUrl(att.file.id)}
                        alt={att.file.filename}
                        width={320}
                        height={256}
                        className="h-auto max-h-64 w-auto max-w-xs object-contain"
                        unoptimized
                      />
                    </button>
                  ) : "file" in att ? (
                    <FileChip
                      key={att.file.id}
                      filename={att.file.filename}
                      hint={att.file.mime_type}
                      onClick={() => openPreview(att.file)}
                    />
                  ) : (
                    <FileChip key={att.id} filename="Attached file" href={getFileUrl(att.id)} />
                  ),
                )}
              </div>
            );
          })()}

        {(() => {
          const rawParts = message.parts ?? [];
{%- if cookiecutter.enable_deep_research %}
          const parts = visibleParts(rawParts);
{%- else %}
          const parts = rawParts;
{%- endif %}
          const useParts = !isUser && parts.length > 0;

          // "Thinking…" placeholder — shown until anything streams in.
          const showPlaceholder =
            !isUser &&
            message.isStreaming &&
            !message.content &&
            parts.length === 0 &&
            (!message.toolCalls || message.toolCalls.length === 0);

          const ThinkingBlock = ({ text, open }: { text: string; open: boolean }) => (
            <details
              className="border-foreground/10 bg-muted/40 group rounded-2xl rounded-tl-sm border px-3 py-2 sm:px-4"
              open={open}
            >
              <summary className="text-foreground/55 hover:text-foreground/80 flex cursor-pointer items-center gap-2 font-mono text-[10px] tracking-wider uppercase select-none">
                <span className="bg-foreground/30 inline-block h-1.5 w-1.5 rounded-full" />
                Thinking
                {message.isStreaming && (
                  <span className="bg-foreground/40 inline-block h-1 w-1 animate-pulse rounded-full" />
                )}
              </summary>
              <pre className="text-foreground/65 mt-2 max-h-72 overflow-y-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                {text}
              </pre>
            </details>
          );

          const TextBubble = ({
            text,
            showCursor,
          }: {
            text: string;
            showCursor: boolean;
          }) => (
            <div
              className={cn(
                "relative rounded-2xl px-3 py-2 sm:px-4 sm:py-2.5",
                isUser
                  ? "bg-primary text-primary-foreground rounded-tr-sm"
                  : "bg-muted rounded-tl-sm",
              )}
            >
              {isUser ? (
                <p className="text-sm break-words whitespace-pre-wrap">{text}</p>
              ) : (
                <div className="prose-sm max-w-none text-sm">
                  <MarkdownContent content={text} />
                  {showCursor && (
                    <span className="ml-1 inline-block h-4 w-1.5 animate-pulse rounded-full bg-current" />
                  )}
                </div>
              )}
            </div>
          );

          return (
            <>
              {showPlaceholder && (
                <div
                  className="bg-muted flex items-center gap-2 rounded-2xl rounded-tl-sm px-4 py-2.5"
                  role="status"
                  aria-live="polite"
                >
                  <div className="flex gap-1" aria-hidden="true">
                    <span className="bg-muted-foreground/40 h-1.5 w-1.5 animate-bounce rounded-full [animation-delay:0ms]" />
                    <span className="bg-muted-foreground/40 h-1.5 w-1.5 animate-bounce rounded-full [animation-delay:150ms]" />
                    <span className="bg-muted-foreground/40 h-1.5 w-1.5 animate-bounce rounded-full [animation-delay:300ms]" />
                  </div>
                  <span className="text-muted-foreground text-xs">Thinking...</span>
                </div>
              )}

              {useParts
                ? /* Ordered timeline: render each part in arrival order. */
                  parts.map((part, i) => {
                    if (part.type === "thinking" && part.content) {
                      return (
                        <ThinkingBlock
                          key={part.id}
                          text={part.content}
                          open={Boolean(message.isStreaming) && i === parts.length - 1}
                        />
                      );
                    }
                    if (part.type === "tool" && part.toolCall) {
                      return (
                        <div key={part.id} className="w-full">
                          <ToolCallCard toolCall={part.toolCall} />
                        </div>
                      );
                    }
                    if (part.type === "text" && part.content) {
                      return (
                        <TextBubble
                          key={part.id}
                          text={part.content}
                          showCursor={
                            Boolean(message.isStreaming) && i === parts.length - 1
                          }
                        />
                      );
                    }
                    return null;
                  })
                : /* Legacy fallback: CrewAI / user / pre-parts messages. */
                  <>
                    {!isUser && message.thinking && (
                      <ThinkingBlock
                        text={message.thinking}
                        open={Boolean(message.isStreaming)}
                      />
                    )}
                    {message.content && (
                      <TextBubble
                        text={message.content}
                        showCursor={!isUser && Boolean(message.isStreaming)}
                      />
                    )}
                    {message.toolCalls && message.toolCalls.length > 0 && (
                      <div className="w-full space-y-2">
                        {message.toolCalls
{%- if cookiecutter.enable_deep_research %}
                          .filter((tc) => !RESEARCH_TOOL_NAMES.has(tc.name))
{%- endif %}
                          .map((toolCall) => (
                            <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                          ))}
                      </div>
                    )}
                  </>}
            </>
          );
        })()}

        {!message.isStreaming && message.content && (
          <div className={cn("flex items-center gap-2", isUser && "flex-row-reverse")}>
            {message.timestamp && (
              <span className="text-muted-foreground text-[10px]">
                {new Date(message.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
            <CopyButton
              text={message.content}
              className={cn(
                "h-6 w-6 rounded-md sm:opacity-0 sm:group-hover:opacity-100",
                isUser ? "bg-secondary hover:bg-secondary/80" : "bg-muted hover:bg-muted/80",
              )}
            />
            {!isUser && onRegenerate && (
              <button
                type="button"
                onClick={onRegenerate}
                title="Regenerate response"
                aria-label="Regenerate response"
                className="bg-muted hover:bg-muted/80 text-foreground/70 hover:text-foreground inline-flex h-6 w-6 items-center justify-center rounded-md transition-colors sm:opacity-0 sm:group-hover:opacity-100"
              >
                <RefreshCw className="h-3 w-3" />
              </button>
            )}
            {!isUser && (
              <RatingButtons
                messageId={message.id}
                conversationId={message.conversationId ?? ""}
                currentRating={message.user_rating ?? null}
                ratingCount={message.rating_count ?? undefined}
                isAssistant={!isUser}
                onRatingChange={(updatedData) => {
                  updateMessage(message.id, (msg) => ({
                    ...msg,
                    user_rating: updatedData.rating,
                    rating_count: updatedData.rating_count,
                  }));
                }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

{%- if cookiecutter.enable_deep_research %}
function visibleParts(parts: MessagePart[]): MessagePart[] {
  return parts.filter(
    (p) => !(p.type === "tool" && !!p.toolCall && RESEARCH_TOOL_NAMES.has(p.toolCall.name)),
  );
}
{%- endif %}

// --- Attachment helpers ---------------------------------------------------

type AttachmentDisplay =
  | { kind: "image"; file: ChatMessageFile }
  | { kind: "file"; file: ChatMessageFile }
  | { kind: "unknown"; id: string };

function kindFor(file: ChatMessageFile): "image" | "file" {
  if (file.file_type === "image") return "image";
  if (file.mime_type.startsWith("image/")) return "image";
  return "file";
}

function FileChip({
  filename,
  hint,
  onClick,
  href,
}: {
  filename: string;
  hint?: string;
  /** When provided, clicking opens the file in the preview panel. */
  onClick?: () => void;
  /** Fallback for legacy attachments without full metadata — opens in new tab. */
  href?: string;
}) {
  const ext = filename.includes(".") ? filename.split(".").pop()!.toLowerCase() : null;
  const className =
    "border-foreground/15 bg-card hover:border-foreground/40 inline-flex max-w-xs items-center gap-2 rounded-xl border px-3 py-2 transition-colors text-left";
  const inner = (
    <>
      <span className="bg-foreground/8 text-foreground/65 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
        <FileText className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-foreground block truncate text-sm font-medium">{filename}</span>
        {ext && (
          <span className="text-foreground/55 font-mono text-[10px] tracking-wider uppercase">
            {ext}
          </span>
        )}
      </span>
      <Paperclip className="text-foreground/40 h-3.5 w-3.5 shrink-0" />
    </>
  );
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className} title={hint ?? filename}>
        {inner}
      </button>
    );
  }
  return (
    <a
      href={href ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      className={className}
      title={hint ?? filename}
    >
      {inner}
    </a>
  );
}
