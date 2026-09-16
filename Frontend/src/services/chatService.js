/**
 * chatService.js — SSE streaming chat service
 *
 * Opens a streaming POST request to /api/chat using the Fetch API.
 * Parses SSE events and calls the appropriate callbacks.
 *
 * Security: Supabase access token added via Authorization header.
 * The GROQ_API_KEY and GITHUB_MCP_PAT never reach the browser.
 */

import { supabase } from "./supabaseClient";

const API_BASE =
  import.meta.env.VITE_API_URL || "http://localhost:5000/api";

/**
 * Stream a chat message to the backend.
 *
 * @param {Object} params
 * @param {string} params.username — GitHub username
 * @param {string} params.message — Current user message
 * @param {Object|null} params.dashboardContext — Dashboard data
 * @param {Array} params.conversationHistory — [{role, content}]
 * @param {string|null} params.conversationSummary — Compact summary
 * @param {Object} callbacks — SSE event handlers
 * @param {Function} callbacks.onAgentStarted
 * @param {Function} callbacks.onToolStarted — ({tool, label})
 * @param {Function} callbacks.onToolCompleted — ({tool, success})
 * @param {Function} callbacks.onMessageDelta — (content: string)
 * @param {Function} callbacks.onSource — (sources: Array)
 * @param {Function} callbacks.onMessageCompleted
 * @param {Function} callbacks.onError — (message: string)
 * @returns {Function} abort — call to cancel the stream
 */
export function streamChat(
  {
    username,
    message,
    dashboardContext = null,
    conversationHistory = [],
    conversationSummary = null,
  },
  {
    onAgentStarted = () => {},
    onToolStarted = () => {},
    onToolCompleted = () => {},
    onMessageDelta = () => {},
    onSource = () => {},
    onMessageCompleted = () => {},
    onError = () => {},
  } = {}
) {
  const controller = new AbortController();

  (async () => {
    try {
      // Get Supabase auth token
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;

      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          username,
          message,
          dashboard_context: dashboardContext,
          conversation_history: conversationHistory,
          conversation_summary: conversationSummary,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errText = await response.text().catch(() => "");
        let errMsg = "Failed to connect to AI service.";
        try {
          const errJson = JSON.parse(errText);
          if (errJson.detail) errMsg = errJson.detail;
        } catch (_) {}
        if (response.status === 401) errMsg = "Authentication required. Please sign in again.";
        if (response.status === 429) errMsg = "The AI service is temporarily rate-limited. Please try again shortly.";
        onError(errMsg);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (!json) continue;

          let event;
          try {
            event = JSON.parse(json);
          } catch (_) {
            continue;
          }

          switch (event.type) {
            case "agent_started":
              onAgentStarted();
              break;
            case "tool_started":
              onToolStarted({ tool: event.tool, label: event.label });
              break;
            case "tool_completed":
              onToolCompleted({ tool: event.tool, success: event.success });
              break;
            case "message_delta":
              onMessageDelta(event.content ?? "");
              break;
            case "source":
              onSource(event.sources ?? []);
              break;
            case "message_completed":
              onMessageCompleted();
              break;
            case "error":
              onError(event.message ?? "An error occurred.");
              break;
            default:
              break;
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") return; // User cancelled
      console.error("Chat stream error:", err);
      onError("Couldn't connect to the AI service. Please try again.");
    }
  })();

  return () => controller.abort();
}