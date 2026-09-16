/**
 * ChatHeader — compact chat panel header.
 * Shows "GitHub AI" branding and New/Clear chat actions.
 */

import { Bot, Plus, Trash2, X } from "lucide-react";

export default function ChatHeader({ onNewChat, onClearChat, onClose }) {
  return (
    <div className="chat-header-bar">
      <div className="chat-header-brand">
        <div className="chat-header-icon">
          <Bot size={16} />
        </div>
        <div className="chat-header-titles">
          <span className="chat-header-title">GitHub AI</span>
          <span className="chat-header-subtitle">Developer Assistant</span>
        </div>
      </div>

      <div className="chat-header-actions">
        <button
          className="chat-icon-btn"
          onClick={onNewChat}
          title="New Chat"
          aria-label="New Chat"
        >
          <Plus size={15} />
        </button>
        <button
          className="chat-icon-btn"
          onClick={onClearChat}
          title="Clear Chat"
          aria-label="Clear Chat"
        >
          <Trash2 size={15} />
        </button>
        <button
          className="chat-icon-btn chat-close-btn"
          onClick={onClose}
          title="Close"
          aria-label="Close chat"
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
}
