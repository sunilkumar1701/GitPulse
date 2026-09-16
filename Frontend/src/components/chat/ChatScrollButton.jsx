/**
 * ChatScrollButton — jump-to-latest button when user has scrolled up.
 */

import { ArrowDown } from "lucide-react";

export default function ChatScrollButton({ onClick, visible }) {
  if (!visible) return null;

  return (
    <button
      className="chat-scroll-btn"
      onClick={onClick}
      aria-label="Scroll to latest message"
      title="Scroll to bottom"
    >
      <ArrowDown size={14} />
    </button>
  );
}
