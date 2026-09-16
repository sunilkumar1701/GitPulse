/**
 * ChatMessageList — scrollable message list.
 *
 * Auto-follows during streaming.
 * Stops auto-scroll when user manually scrolls up.
 * Shows scroll-to-bottom button when needed.
 */

import { useEffect, useRef, useState, useCallback } from "react";

import ChatUserMessage from "./ChatUserMessage";
import ChatAssistantMessage from "./ChatAssistantMessage";
import ChatScrollButton from "./ChatScrollButton";

export default function ChatMessageList({ messages, onRegenerate }) {
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const userScrolledUp = useRef(false);

  const scrollToBottom = useCallback((behavior = "smooth") => {
    bottomRef.current?.scrollIntoView({ behavior, block: "end" });
    userScrolledUp.current = false;
    setShowScrollBtn(false);
  }, []);

  // Detect user scrolling up
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const isNearBottom = distanceFromBottom < 80;
    userScrolledUp.current = !isNearBottom;
    setShowScrollBtn(!isNearBottom);
  }, []);

  // Auto-scroll on new content unless user scrolled up
  useEffect(() => {
    if (!userScrolledUp.current) {
      requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    }
  }, [messages]);

  if (!messages || messages.length === 0) return null;

  return (
    <div className="chat-message-list-wrapper">
      <div
        className="chat-message-list"
        ref={scrollRef}
        onScroll={handleScroll}
        role="list"
        aria-label="Conversation"
        aria-live="polite"
      >
        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return <ChatUserMessage key={i} content={msg.content} />;
          }
          return (
            <ChatAssistantMessage
              key={i}
              content={msg.content}
              activities={msg.activities || []}
              sources={msg.sources || []}
              isStreaming={msg.isStreaming || false}
              isError={msg.isError || false}
              onRegenerate={
                !msg.isStreaming && onRegenerate
                  ? () => onRegenerate(i)
                  : undefined
              }
            />
          );
        })}
        <div ref={bottomRef} aria-hidden="true" />
      </div>

      <ChatScrollButton
        visible={showScrollBtn}
        onClick={() => scrollToBottom("smooth")}
      />
    </div>
  );
}
