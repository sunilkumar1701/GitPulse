/**
 * ChatAssistantMessage — assistant message with markdown rendering,
 * agent activity, source list, copy and regenerate actions.
 */

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, RotateCcw, Bot } from "lucide-react";

import ThinkingReasoning from "./ThinkingReasoning";
import SourceList from "./SourceList";

export default function ChatAssistantMessage({
  content,
  activities = [],
  sources = [],
  isStreaming = false,
  isError = false,
  onRegenerate,
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) {}
  };

  return (
    <div className="assistant-message-wrapper" role="listitem">
      <div className="assistant-avatar" aria-hidden="true">
        <Bot size={13} />
      </div>

      <div className="assistant-message-body">
        {/* Agent activity section */}
        {activities.length > 0 && (
          <ThinkingReasoning activities={activities} isActive={isStreaming && !content} />
        )}

        {/* Message content */}
        {content && (
          <div
            className={`assistant-message-content ${isError ? "assistant-error" : ""}`}
            aria-label="Assistant response"
            aria-live={isStreaming ? "polite" : undefined}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="md-link"
                  >
                    {children}
                  </a>
                ),
                code: ({ inline, children }) =>
                  inline ? (
                    <code className="md-inline-code">{children}</code>
                  ) : (
                    <pre className="md-code-block">
                      <code>{children}</code>
                    </pre>
                  ),
                table: ({ children }) => (
                  <div className="md-table-wrapper">
                    <table className="md-table">{children}</table>
                  </div>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
            {isStreaming && <span className="streaming-cursor" aria-hidden="true" />}
          </div>
        )}

        {/* Streaming placeholder */}
        {isStreaming && !content && activities.length === 0 && (
          <div className="assistant-thinking" aria-label="Assistant is thinking">
            <span className="thinking-dot" />
            <span className="thinking-dot" />
            <span className="thinking-dot" />
          </div>
        )}

        {/* Sources */}
        {!isStreaming && sources.length > 0 && (
          <SourceList sources={sources} />
        )}

        {/* Actions — only on completed messages */}
        {!isStreaming && content && !isError && (
          <div className="message-actions">
            <button
              className="msg-action-btn"
              onClick={handleCopy}
              title={copied ? "Copied!" : "Copy response"}
              aria-label={copied ? "Copied" : "Copy response"}
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
            </button>
            {onRegenerate && (
              <button
                className="msg-action-btn"
                onClick={onRegenerate}
                title="Regenerate response"
                aria-label="Regenerate response"
              >
                <RotateCcw size={12} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
