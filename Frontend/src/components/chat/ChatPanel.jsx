/**
 * ChatPanel — main chat UI orchestrator.
 *
 * Manages:
 * - Message list state
 * - Conversation history (for context)
 * - SSE streaming lifecycle
 * - Agent activity tracking
 * - Stop generation
 * - Regenerate last message
 * - New/Clear chat
 */

import { useState, useCallback, useRef } from "react";
import "./chat.css";

import ChatHeader from "./ChatHeader";
import ChatEmptyState from "./ChatEmptyState";
import ChatMessageList from "./ChatMessageList";
import ChatComposer from "./ChatComposer";
import { streamChat } from "../../services/chatService";
import { useDashboardContext } from "../../context/DashboardContext";

const MAX_HISTORY_TURNS = 6; // Keep last 6 messages for context

export default function ChatPanel({ onClose, username }) {
  const { dashboardData } = useDashboardContext();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [focusTrigger, setFocusTrigger] = useState(0);

  // Conversation history sent to backend for follow-up context
  const historyRef = useRef([]);
  const abortRef = useRef(null);

  // Build context history array (last N turns)
  const getHistory = useCallback(() => {
    const hist = historyRef.current;
    return hist.slice(-MAX_HISTORY_TURNS);
  }, []);

  const sendMessage = useCallback(
    (messageText) => {
      const text = (messageText || input).trim();
      if (!text || isStreaming) return;

      setInput("");

      // Add user message
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        // Placeholder for streaming assistant response
        {
          role: "assistant",
          content: "",
          activities: [],
          sources: [],
          isStreaming: true,
          isError: false,
        },
      ]);

      setIsStreaming(true);

      // Track streaming state locally
      let accumulatedContent = "";
      let currentActivities = [];
      let currentSources = [];

      const updateLastMessage = (updater) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === "assistant") {
            updated[updated.length - 1] = { ...last, ...updater(last) };
          }
          return updated;
        });
      };

      const abort = streamChat(
        {
          username,
          message: text,
          dashboardContext: dashboardData,
          conversationHistory: getHistory(),
          conversationSummary: null,
        },
        {
          onAgentStarted: () => {
            currentActivities = [];
            accumulatedContent = "";
          },

          onToolStarted: ({ tool, label }) => {
            currentActivities = [
              ...currentActivities,
              { label, tool, done: false },
            ];
            updateLastMessage((last) => ({
              activities: currentActivities,
            }));
          },

          onToolCompleted: ({ tool }) => {
            currentActivities = currentActivities.map((a) =>
              a.tool === tool ? { ...a, done: true } : a
            );
            // Mark all as done for the completed tool
            currentActivities = currentActivities.map((a) =>
              a.tool === tool ? { ...a, done: true } : a
            );
            updateLastMessage((last) => ({
              activities: currentActivities,
            }));
          },

          onMessageDelta: (chunk) => {
            accumulatedContent += chunk;
            const captured = accumulatedContent;
            updateLastMessage((last) => ({
              content: captured,
              activities: currentActivities,
            }));
          },

          onSource: (sources) => {
            currentSources = sources;
          },

          onMessageCompleted: () => {
            const finalContent = accumulatedContent;
            const finalActivities = currentActivities.map((a) => ({ ...a, done: true }));
            const finalSources = currentSources;

            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: finalContent,
                  activities: finalActivities,
                  sources: finalSources,
                  isStreaming: false,
                  isError: false,
                };
              }
              return updated;
            });

            // Update conversation history for follow-up context
            historyRef.current = [
              ...historyRef.current,
              { role: "user", content: text },
              { role: "assistant", content: finalContent },
            ].slice(-MAX_HISTORY_TURNS);

            setIsStreaming(false);
            abortRef.current = null;
          },

          onError: (errorMessage) => {
            updateLastMessage((last) => ({
              content: errorMessage,
              activities: currentActivities.map((a) => ({ ...a, done: true })),
              sources: [],
              isStreaming: false,
              isError: true,
            }));
            setIsStreaming(false);
            abortRef.current = null;
          },
        }
      );

      abortRef.current = abort;
    },
    [input, isStreaming, username, dashboardData, getHistory]
  );

  const handleStop = useCallback(() => {
    abortRef.current?.();
    abortRef.current = null;

    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last && last.role === "assistant" && last.isStreaming) {
        updated[updated.length - 1] = {
          ...last,
          isStreaming: false,
          content: last.content || "_(Generation stopped)_",
        };
      }
      return updated;
    });
    setIsStreaming(false);
  }, []);

  const handleRegenerate = useCallback(
    (msgIndex) => {
      // Find the user message preceding this assistant message
      const prevUserMsg = messages
        .slice(0, msgIndex)
        .reverse()
        .find((m) => m.role === "user");
      if (!prevUserMsg) return;

      // Remove the assistant message at index
      setMessages((prev) => prev.slice(0, msgIndex));
      sendMessage(prevUserMsg.content);
    },
    [messages, sendMessage]
  );

  const handleNewChat = useCallback(() => {
    handleStop();
    setMessages([]);
    historyRef.current = [];
    setInput("");
    setFocusTrigger((prev) => prev + 1);
  }, [handleStop]);

  const handleClearChat = handleNewChat;

  const handleStarterPrompt = useCallback(
    (prompt) => {
      setInput(prompt);
      // Small timeout so the input updates before sending
      setTimeout(() => sendMessage(prompt), 10);
    },
    [sendMessage]
  );

  const showEmpty = messages.length === 0;

  return (
    <div className="chat-panel" role="complementary" aria-label="GitHub AI Assistant">
      <ChatHeader
        onNewChat={handleNewChat}
        onClearChat={handleClearChat}
        onClose={onClose}
      />

      <div className="chat-body">
        {showEmpty ? (
          <ChatEmptyState onPromptClick={handleStarterPrompt} />
        ) : (
          <ChatMessageList
            messages={messages}
            onRegenerate={handleRegenerate}
          />
        )}
      </div>

      <ChatComposer
        value={input}
        onChange={setInput}
        onSend={() => sendMessage()}
        onStop={handleStop}
        isStreaming={isStreaming}
        disabled={false}
        focusTrigger={focusTrigger}
      />
    </div>
  );
}
