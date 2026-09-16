/**
 * ChatUserMessage — user message bubble with copy action.
 */

import { useState } from "react";
import { Copy, Check } from "lucide-react";

export default function ChatUserMessage({ content }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) {}
  };

  return (
    <div className="user-message-wrapper" role="listitem">
      <div className="user-message-bubble" aria-label="Your message">
        <p className="user-message-text">{content}</p>
      </div>
      <div className="message-actions">
        <button
          className="msg-action-btn"
          onClick={handleCopy}
          title={copied ? "Copied!" : "Copy message"}
          aria-label={copied ? "Copied" : "Copy message"}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      </div>
    </div>
  );
}
