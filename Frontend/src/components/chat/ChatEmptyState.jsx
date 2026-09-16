/**
 * ChatEmptyState — shown when no messages exist.
 * Includes starter prompts that populate the composer.
 */

import { Sparkles } from "lucide-react";

const STARTER_PROMPTS = [
  "What's my developer score?",
  "Which repository is my strongest?",
  "What technologies do I use most?",
  "How can I improve my portfolio?",
  "What issues are open in my top repository?",
  "What was my latest pull request?",
];

export default function ChatEmptyState({ onPromptClick }) {
  return (
    <div className="chat-empty-state" role="region" aria-label="Chat welcome">
      <div className="chat-empty-icon">
        <Sparkles size={28} />
      </div>

      <h2 className="chat-empty-heading">Ask about your GitHub profile</h2>
      <p className="chat-empty-sub">
        Analyze your repositories, activity, technologies, portfolio and more.
      </p>

      <div className="chat-starter-grid" role="list">
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            className="chat-starter-chip"
            onClick={() => onPromptClick(prompt)}
            role="listitem"
            aria-label={`Ask: ${prompt}`}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
