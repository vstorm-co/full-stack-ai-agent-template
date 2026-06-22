{% raw %}"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, Play, RotateCcw, Square } from "lucide-react";
import { MessageItem } from "@/components/chat/message-item";
import { useConversationReplay } from "@/hooks/use-conversation-replay";
import { conversationMessagesToChatMessages, type RawMessage } from "@/lib/conversation-to-chat";

interface DemoReplayProps {
  rawMessages: RawMessage[];
}

const playBtnRingStyle = { inset: "-10px", borderRadius: "9999px" };
const playBtnGlowStyle = { boxShadow: "0 0 60px oklch(from var(--color-brand) l c h / 0.5)" };
const scrollbarStyle: React.CSSProperties = { scrollbarWidth: "thin", scrollbarColor: "var(--color-border) transparent" };

export function DemoReplay({ rawMessages }: DemoReplayProps) {
  const messages = useMemo(() => conversationMessagesToChatMessages(rawMessages), [rawMessages]);
  const { isReplaying, displayMessages, tick, start, stop } = useConversationReplay(messages);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const [following, setFollowing] = useState(true);
  const lastAutoY = useRef(0);

  const showPrePlay = !hasPlayed && !isReplaying;
  const progress = messages.length > 0 ? Math.round((displayMessages.length / messages.length) * 100) : 0;

  const play = () => {
    setHasPlayed(true);
    setFollowing(true);
    start();
  };

  // Keep the latest step ~1/3 up from the bottom while replaying — scroll the inner container.
  useEffect(() => {
    if (!isReplaying || !following) return;
    const container = scrollRef.current;
    const el = bottomRef.current;
    if (!container || !el) return;
    const delta =
      el.getBoundingClientRect().top - container.getBoundingClientRect().top - container.clientHeight * 0.66;
    if (delta > 2) {
      container.scrollBy({ top: delta, behavior: "auto" });
      lastAutoY.current = container.scrollTop;
    }
  }, [tick, isReplaying, following]);

  // Disengage auto-scroll when the user scrolls up manually.
  useEffect(() => {
    if (!isReplaying) return;
    const container = scrollRef.current;
    if (!container) return;
    const onScroll = () => {
      if (Math.abs(container.scrollTop - lastAutoY.current) < 4) return;
      if (container.scrollTop < lastAutoY.current) setFollowing(false);
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, [isReplaying]);

  const jumpToActive = () => {
    setFollowing(true);
    const container = scrollRef.current;
    const el = bottomRef.current;
    if (!container || !el) return;
    const delta =
      el.getBoundingClientRect().top - container.getBoundingClientRect().top - container.clientHeight * 0.66;
    container.scrollBy({ top: delta, behavior: "auto" });
    lastAutoY.current = container.scrollTop;
  };

  const blurStyle = { filter: "blur(6px)", opacity: 0.25, pointerEvents: "none" as const, userSelect: "none" as const };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] w-full max-w-4xl flex-col px-4">
      {/* Messages — scrollable container, fills remaining height */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-thumb:hover]:bg-brand/50"
        style={scrollbarStyle}
      >
        <div
          className="transition-[filter,opacity] duration-700"
          style={showPrePlay ? blurStyle : undefined}
        >
          {(showPrePlay ? messages : displayMessages).map((message) => (
            <MessageItem key={message.id} message={message} />
          ))}
        </div>
        <div ref={bottomRef} className="h-0" />
        {isReplaying && <div aria-hidden className="h-[30vh]" />}
      </div>

      {/* Pre-play overlay — cinematic reveal moment */}
      {showPrePlay && (
        <div
          className="fixed inset-0 z-30 flex flex-col items-center justify-center gap-7 bg-foreground/60 backdrop-blur-sm"
        >
          {/* Glowing play button */}
          <button
            type="button"
            onClick={play}
            className="group/btn relative outline-none"
            aria-label="Watch replay"
          >
            <span
              className="absolute inset-0 animate-ping rounded-full bg-brand/30"
            />
            <span
              className="absolute animate-ping rounded-full bg-brand/12 [animation-delay:420ms]"
              style={playBtnRingStyle}
            />
            <span
              className="bg-brand relative flex h-24 w-24 items-center justify-center rounded-full shadow-lg transition-transform duration-300 group-hover/btn:scale-[1.06] group-active/btn:scale-95"
              style={playBtnGlowStyle}
            >
              <Play className="h-10 w-10 translate-x-1 fill-white text-white" />
            </span>
          </button>

          <div className="text-center">
            <p className="text-xl font-semibold text-white">Watch the agent work</p>
            <p className="mt-1.5 font-mono text-sm text-white/60">
              {messages.length} messages · replayed live
            </p>
          </div>
        </div>
      )}

      {/* Jump-to-active button — re-engages auto-scroll after manual scroll-up */}
      {isReplaying && !following && (
        <button
          type="button"
          onClick={jumpToActive}
          className="step-reveal border-border bg-card/95 text-foreground/80 hover:border-brand/50 hover:text-foreground fixed right-4 bottom-24 z-20 inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-xs font-medium shadow-lg backdrop-blur transition-colors"
        >
          <ArrowDown className="h-3.5 w-3.5" />
          Jump to active
        </button>
      )}

      {/* Bottom bar — pinned by flex column, no window sticky needed */}
      <div className="bg-background/90 -mx-4 border-t border-border/50 px-4 py-4 backdrop-blur">
        {/* Progress bar — appears once replay has started */}
        {hasPlayed && (
          <div className="mb-3.5 h-px w-full overflow-hidden rounded-full bg-border">
            <div
              className="bg-brand h-full rounded-full transition-[width] duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        <div className="mx-auto flex max-w-3xl items-center justify-center gap-3">
          {showPrePlay ? (
            <button
              type="button"
              onClick={play}
              className="bg-brand inline-flex items-center gap-2 rounded-full px-8 py-3 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
            >
              <Play className="h-4 w-4 fill-current" />
              Watch the agent work
            </button>
          ) : isReplaying ? (
            <button
              type="button"
              onClick={stop}
              className="border-border bg-muted text-foreground/80 hover:bg-muted/70 inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-sm font-medium transition-colors"
            >
              <Square className="h-3.5 w-3.5" />
              Stop
            </button>
          ) : (
            <button
              type="button"
              onClick={play}
              className="bg-brand inline-flex items-center gap-2 rounded-full px-7 py-3 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
            >
              <RotateCcw className="h-4 w-4" />
              Watch again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
{% endraw %}
