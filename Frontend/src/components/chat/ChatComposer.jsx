/**
 * ChatComposer — polished fixed-bottom message composer.
 *
 * Features:
 * - Auto-resize textarea
 * - Enter sends / Shift+Enter newline
 * - Send button → Stop button during generation
 * - Keyboard accessible
 * - Focus management
 */

import { useRef, useEffect, useCallback } from "react";
import { Send, Square } from "lucide-react";

export default function ChatComposer({
  value,
  onChange,
  onSend,
  onStop,
  isStreaming,
  disabled = false,
  focusTrigger = 0,
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }, [value]);

  // Focus on mount or trigger
  useEffect(() => {
    if (!isStreaming && !disabled) {
      textareaRef.current?.focus();
    }
  }, [isStreaming, disabled, focusTrigger]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!isStreaming && value.trim()) {
          onSend();
        }
      }
    },
    [isStreaming, value, onSend]
  );

  const handleSendOrStop = useCallback(() => {
    if (isStreaming) {
      onStop?.();
    } else if (value.trim()) {
      onSend();
    }
  }, [isStreaming, value, onSend, onStop]);

  const canSend = !disabled && (isStreaming || value.trim().length > 0);

  return (
    <div className="chat-composer" role="form" aria-label="Send a message">
      <div className={`chat-composer-inner ${disabled ? "composer-disabled" : ""}`}>
        <textarea
          ref={textareaRef}
          className="chat-composer-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your GitHub..."
          rows={1}
          disabled={disabled || isStreaming}
          aria-label="Message input"
          aria-multiline="true"
          aria-disabled={disabled || isStreaming}
        />

        <button
          className={`chat-send-btn ${isStreaming ? "chat-stop-btn" : ""} ${!canSend ? "chat-send-disabled" : ""}`}
          onClick={handleSendOrStop}
          disabled={!canSend}
          aria-label={isStreaming ? "Stop generation" : "Send message"}
          title={isStreaming ? "Stop" : "Send"}
        >
          {isStreaming ? <Square size={14} fill="currentColor" /> : <Send size={14} />}
        </button>
      </div>

      <p className="chat-composer-hint">
        {isStreaming
          ? "Generating response..."
          : "Enter to send · Shift+Enter for newline"}
      </p>
    </div>
  );
}
