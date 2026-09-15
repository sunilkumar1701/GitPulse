"""
Agent loop — the core agentic execution engine.

Implements a true iterative agent loop:
  1. Build context
  2. Call GPT-OSS 120B via Groq
  3. If no tool calls → stream final answer
  4. If tool calls → execute via FastAPI → loop
  5. MAX_AGENT_STEPS = 8 (safety cap, not a question limit)

Emits SSE events:
  - agent_started
  - tool_started
  - tool_completed
  - message_delta
  - source
  - message_completed
  - error

Security:
  - GROQ_API_KEY never leaves FastAPI
  - GITHUB_MCP_PAT never goes to the LLM
  - Tool results are normalized before being fed back
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from groq import RateLimitError, APIConnectionError, APIStatusError, APITimeoutError

from app.clients.groq_client import get_groq_client, handle_groq_error
from app.agent.prompt_builder import build_messages
from app.agent.tool_registry import get_groq_tool_definitions, has_tools, get_tool
from app.agent.tool_executor import execute_tool
from app.agent.response_builder import build_sources
from app.agent.schemas import ConversationTurn
from app.core.config import get_settings

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 8

# Token budget targets
SAFE_INPUT_TOKEN_TARGET = 6500
HARD_CONTEXT_GUARD = 7000

def _sse(event: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(event)}\n\n"


def _compact_old_tool_result(content_str: str) -> str:
    """
    Semantic Fact Extractor.
    Extracts identifiers and scalar facts from previous tool results to preserve state,
    while dropping bloated lists and strings to prevent context explosion.
    """
    if len(content_str) < 200:
        return content_str # Already small enough
        
    try:
        data = json.loads(content_str)
        if isinstance(data, dict):
            # If it's a paginated wrapper like {"items": [...]}, just keep the top-level scalars
            compact = {}
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)):
                    if isinstance(v, str) and len(v) > 200:
                        if k == "content":
                            compact[k] = v[:150] + "... [truncated for history]"
                        continue # drop huge strings (descriptions/readme)
                    compact[k] = v
                elif isinstance(v, list) and k in ["items", "results"]:
                    # Keep a tiny representation of all items for continuity
                    summary_list = []
                    for item in v:
                        if isinstance(item, dict):
                            rep = {ik: iv for ik, iv in item.items() if ik in [
                                "name", "full_name", "owner", "number", "state", "sha",
                                "stars", "stargazers_count", "title", "url",
                                "createdAt", "repository", "language", "forks", "forks_count"
                            ]}
                            if rep:
                                summary_list.append(rep)
                    if summary_list:
                        compact[f"{k}_summary"] = summary_list
            
            # If nothing was extracted, keep at least the keys to show what was there
            if not compact:
                compact["note"] = f"List containing keys: {list(data.keys())}"
                
            return json.dumps(compact)
            
        elif isinstance(data, list):
             # If direct list, keep summaries of all items
             summary_list = []
             for item in data:
                  if isinstance(item, dict):
                       rep = {ik: iv for ik, iv in item.items() if ik in [
                           "name", "full_name", "owner", "number", "state", "sha",
                           "stars", "stargazers_count", "title", "url",
                           "createdAt", "repository", "language", "forks", "forks_count"
                       ]}
                       if rep:
                           summary_list.append(rep)
             if summary_list:
                  return json.dumps({"note": "Truncated list summaries", "items_summary": summary_list})
             return json.dumps({"note": f"List of {len(data)} items"})
             
    except Exception:
        pass
        
    return '{"note": "[Prior step result compressed to save tokens]"}'


async def run_agent(
    username: str,
    question: str,
    dashboard_data: dict[str, Any] | None,
    history: list[ConversationTurn] | None,
    summary: str | None,
) -> AsyncGenerator[str, None]:
    """
    Run the agentic loop and yield SSE events.

    Args:
        username: GitHub username being analyzed.
        question: Current user message.
        dashboard_data: Dashboard analysis data.
        history: Recent conversation history.
        summary: Optional summary of older conversation.

    Yields:
        SSE-formatted strings.
    """
    settings = get_settings()
    client = get_groq_client()

    yield _sse({"type": "agent_started"})

    # Build initial messages and get routing context
    messages, source_mode, capabilities, operation, metric = build_messages(  # type: ignore
        username=username,
        question=question,
        dashboard_data=dashboard_data,
        history=history,
        summary=summary,
    )

    # Tool definitions — computed early for budget logging, but may be cleared by short-circuit paths
    tools = get_groq_tool_definitions() if (has_tools() and source_mode in ["mcp", "hybrid"]) else []

    # Token estimation and [CHAT BUDGET] breakdown
    sys_tokens = len(messages[0].get("content", "")) // 4 if messages else 0
    dash_tokens = len(messages[1].get("content", "")) // 4 if len(messages) > 1 and "Dashboard data" in messages[1].get("content", "") else 0
    hist_tokens = sum(len(m.get("content", "")) // 4 for m in messages[2:-1]) if len(messages) > 2 else 0
    tools_schema_tokens = len(json.dumps(tools)) // 4 if tools else 0
    
    est_tokens = len(json.dumps(messages)) // 4 + tools_schema_tokens

    # Progressive Context Reduction
    if est_tokens > SAFE_INPUT_TOKEN_TARGET:
        logger.warning("Token budget exceeded SAFE limit (%d > %d). Progressively reducing...", est_tokens, SAFE_INPUT_TOKEN_TARGET)
        # 1. Drop conversation history
        messages = [m for m in messages if m["role"] == "system" or "Dashboard data" in m.get("content", "") or m == messages[-1]]
        est_tokens = len(json.dumps(messages)) // 4 + tools_schema_tokens
        
        # 2. If still too large, drop dashboard context
        if est_tokens > SAFE_INPUT_TOKEN_TARGET:
             messages = [m for m in messages if m["role"] == "system" or m == messages[-1]]
             est_tokens = len(json.dumps(messages)) // 4 + tools_schema_tokens

    if est_tokens > HARD_CONTEXT_GUARD:
        logger.error("Token budget exceeded HARD limit: %d > %d", est_tokens, HARD_CONTEXT_GUARD)
        yield _sse({"type": "error", "message": "The required context is too large. Please ask a more specific question or clear your chat history."})
        return

    import uuid
    request_id = str(uuid.uuid4())
    step = 0

    logger.info(
        "\n[CHAT BUDGET]\n"
        "request_id=%s\n"
        "step=%d\n"
        "source_mode=%s\n"
        "capabilities=%s\n"
        "operation=%s\n"
        "metric=%s\n"
        "system_tokens=%d\n"
        "dashboard_tokens=%d\n"
        "history_tokens=%d\n"
        "tool_schema_tokens=%d\n"
        "estimated_input_tokens=%d\n"
        "actual_input_tokens=0\n"
        "tools_exposed=%d\n"
        "tools_called=0\n",
        request_id, step, source_mode, capabilities, operation, metric,
        sys_tokens, dash_tokens, hist_tokens, tools_schema_tokens, est_tokens, 1 if tools else 0
    )

    tool_results: list[dict] = []
    executed_tool_signatures: set[str] = set()
    mcp_recovery_attempted = False
    evidence_states: list[dict] = []  # Track evidence across all tool calls

    logger.info(
        "\n[CHAT ROUTE]\n"
        "request_id=%s\n"
        "source_mode=%s\n"
        "capabilities=%s\n"
        "operation=%s\n"
        "metric=%s\n",
        request_id, source_mode, capabilities, operation, metric
    )


    # Pre-LLM short-circuit: language bytes/percentage queries are CAPABILITY_UNAVAILABLE
    # Detect before spending any LLM tokens on a call that will fail at contract validation.
    if source_mode in ["mcp", "hybrid"] and "LANGUAGES" in capabilities:
        import re as _re
        q_lower = question.lower()
        if _re.search(r'\b(byte|bytes|percentage|percent|%|byte[-\s]?weighted)\b', q_lower):
            lang_limitation = (
                "I checked GitHub through MCP, but the connected MCP server provides only each repository's "
                "primary language — not language byte counts or percentages. "
                "I can show you which primary language appears most often across your repositories, "
                "but I cannot determine the most-used language by bytes from the available data."
            )
            for i in range(0, len(lang_limitation), 4):
                yield _sse({"type": "message_delta", "content": lang_limitation[i:i+4]})
                await asyncio.sleep(0)
            yield _sse({"type": "message_completed"})
            logger.info(
                "[LANG BYTES SHORT-CIRCUIT] request_id=%s capability=LANGUAGES status=CAPABILITY_UNAVAILABLE",
                request_id
            )
            # Clear tools so budget shows tools_exposed=0
            tools = []
            return

    # Task 4: Deterministic Pre-LLM Execution (Count, Sum, Top-N, Latest-N)
    if source_mode in ["mcp", "hybrid"] and operation in ["count", "sum", "top_n", "latest_n"] and capabilities:
        # Select authoritative capability: skip PROFILE when a domain-specific cap is available
        cap = capabilities[0]
        for c in capabilities:
            if c != "PROFILE":
                cap = c
                break
        tool_name = None
        args = {}

        # Extract requested N from question for top_n (e.g., "top 3", "top 5", "top 10")
        _top_n_limit = 3  # default
        _MAX_TOP_N = 10   # token-safety cap
        if operation == "top_n":
            import re as _re_top
            _n_match = _re_top.search(r'\btop\s+(\d+)\b', question.lower())
            if _n_match:
                _top_n_limit = min(int(_n_match.group(1)), _MAX_TOP_N)

        if operation == "count" and cap == "REPOSITORIES":
            tool_name = "search_repositories"
            args = {"query": f"user:{username}", "perPage": 1}
        elif operation == "sum" and cap == "REPOSITORIES" and metric:
            tool_name = "search_repositories"
            args = {"query": f"user:{username}", "perPage": 100}
        elif operation == "top_n" and cap == "REPOSITORIES" and metric:
            tool_name = "search_repositories"
            args = {"query": f"user:{username}", "sort": metric, "perPage": _top_n_limit}
        elif operation == "latest_n" and cap == "PULL_REQUESTS":
            tool_name = "search_pull_requests"
            # search_pull_requests is already scoped to PRs — do NOT add is:pr
            args = {"query": f"author:{username}", "sort": "created", "order": "desc", "perPage": 1}
        elif operation == "latest_n" and cap == "REPOSITORIES":
            tool_name = "search_repositories"
            args = {"query": f"user:{username}", "sort": "updated", "order": "desc", "perPage": 1}

        if tool_name:
            logger.info("[PRE-LLM EXEC] request_id=%s tool=%s operation=%s metric=%s", request_id, tool_name, operation, metric)
            yield _sse({"type": "tool_started", "tool": tool_name, "label": "Checking GitHub deterministically"})
            
            raw_result = await execute_tool(tool_name, args, {"capability": cap, "operation": operation, "metric": metric, "username": username})
            formatted_result = None
            evidence_state = raw_result.get("evidence", {})
            
            if raw_result["success"] and raw_result.get("result"):
                res_data = raw_result["result"]
                
                if operation == "count":
                    count = res_data.get("total_count", 0) if isinstance(res_data, dict) else len(res_data)
                    formatted_result = {"count": count, "count_source": "native_total" if isinstance(res_data, dict) and "total_count" in res_data else "local_fallback"}
                    evidence_state["evidence_status"] = "SUCCESS"
                    
                elif operation == "sum":
                    formatted_result = res_data
                    evidence_state["evidence_status"] = "SUCCESS"
                    
                elif operation == "top_n":
                    items = res_data.get("items", res_data) if isinstance(res_data, dict) else res_data
                    if isinstance(items, list):
                        formatted_result = []
                        for item in items:
                            if isinstance(item, dict):
                                m_val = item.get(metric)
                                if m_val is None and metric == "stars": m_val = item.get("stargazers_count")
                                if m_val is None and metric == "forks": m_val = item.get("forks_count")
                                formatted_result.append({"name": item.get("name") or item.get("full_name"), metric: m_val})
                    evidence_state["evidence_status"] = "SUCCESS" if formatted_result else "NOT_FOUND"
                    
                elif operation == "latest_n":
                    items = res_data.get("items", res_data) if isinstance(res_data, dict) else res_data
                    if isinstance(items, list) and len(items) > 0:
                        item = items[0]
                        # Extract repository with fallback order:
                        # 1. repository field  2. repository_url field  3. parse from html_url
                        _repo = item.get("repository")
                        if not _repo:
                            _repo_url = item.get("repository_url") or ""
                            if _repo_url:
                                # repository_url is like https://api.github.com/repos/owner/repo
                                _repo_url_parts = _repo_url.rstrip("/").split("/")
                                if len(_repo_url_parts) >= 2:
                                    _repo = "/".join(_repo_url_parts[-2:])
                        if not _repo:
                            _html = item.get("html_url") or item.get("url") or ""
                            import re as _re_repo
                            _m = _re_repo.search(r'github\.com/([^/]+/[^/]+)/', _html)
                            _repo = _m.group(1) if _m else None
                        formatted_result = {
                            "number": item.get("number"),
                            "title": item.get("title"),
                            "repository": _repo,
                            "createdAt": item.get("created_at") or item.get("createdAt"),
                            "state": item.get("state"),
                            "url": item.get("html_url") or item.get("url")
                        }
                    evidence_state["evidence_status"] = "SUCCESS" if formatted_result else "NOT_FOUND"

            pre_llm_result = {
                "success": raw_result["success"],
                "result": formatted_result if raw_result["success"] else None,
                "error": raw_result.get("error", ""),
                "evidence": evidence_state
            }
            tool_results.append(pre_llm_result)
            if evidence_state:
                evidence_states.append(evidence_state)
                
            yield _sse({"type": "tool_completed", "tool": tool_name, "success": raw_result["success"]})
            
            tool_result_content = (
                json.dumps(pre_llm_result["result"], default=str)
                if pre_llm_result["success"] and pre_llm_result["result"] is not None
                else pre_llm_result.get("error", "Tool execution failed.")
            )
            messages.append({
                "role": "user",
                "content": f"[System: Background MCP Execution completed automatically based on your request. Result:\n{tool_result_content}\nSummarize this for the user.]"
            })
            executed_tool_signatures.add(f"{tool_name}:{json.dumps(args, sort_keys=True)}:null")

    try:
        while step < MAX_AGENT_STEPS:
            step += 1
            logger.info("Agent step %d/%d (Request %s)", step, MAX_AGENT_STEPS, request_id)

            # Multi-step context compression: compress tool results from older steps
            if step > 1:
                for idx, m in enumerate(messages):
                    if m["role"] == "tool":
                        # Only keep the full result for the most recent step's tools
                        # We approximate "most recent" by checking if it's near the end
                        if idx < len(messages) - 3:
                            m["content"] = _compact_old_tool_result(m.get("content", ""))

            try:
                # Non-streaming call to get tool calls; streaming for final answer
                # We use non-streaming for tool-call steps (need complete response)
                # and streaming only for the final text response.
                kwargs = {
                    "model": settings.GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 1024,
                    "stream": False,
                }
                if tools:
                    kwargs["tools"] = tools
                    
                response = await client.chat.completions.create(**kwargs)

            except RateLimitError as e:
                logger.warning("Groq rate limit: %s", str(e))
                yield _sse({"type": "error", "message": handle_groq_error(e)})
                return
            except (APIConnectionError, APIStatusError, APITimeoutError) as e:
                logger.error("Groq API error (streaming): %s", str(e))
                yield _sse({"type": "error", "message": handle_groq_error(e)})
                return
            except asyncio.CancelledError:
                logger.info("Agent cancelled by client disconnect")
                return
            except Exception as e:
                logger.error("Groq unexpected error: %s", str(e))
                yield _sse({"type": "error", "message": "Couldn't complete that request. Please try again."})
                return

            choice = response.choices[0] if response.choices else None
            if not choice:
                yield _sse({"type": "error", "message": "No response from AI service."})
                return

            message = choice.message

            # Check for tool calls
            tool_calls = message.tool_calls or []

            if not tool_calls:
                # MCP Execution Invariant — not applicable for dashboard or clarification modes
                if source_mode in ["mcp", "hybrid"] and not tool_results:
                    if not mcp_recovery_attempted and step < MAX_AGENT_STEPS:
                        mcp_recovery_attempted = True
                        logger.warning(
                            "[MCP INVARIANT] request_id=%s step=%d: Model attempted to answer without MCP execution.",
                            request_id, step
                        )
                        # Capability-aware recovery — tell the model EXACTLY which workflow to use
                        cap_instructions = ""
                        if capabilities:
                            from app.agent.tool_registry import get_compact_tool_catalog
                            cap_instructions = (
                                f" The required capabilities are: {', '.join(capabilities)}. "
                                "Use the AVAILABLE MCP TOOLS catalog in your system prompt to find "
                                "the correct tool and arguments for these capabilities. "
                                "Execute the most specific available workflow for the first capability now."
                            )
                        force_prompt = (
                            "INVARIANT FAILURE: You must execute an MCP tool to retrieve the authoritative "
                            "GitHub data for this request. Do not fabricate an answer."
                            + cap_instructions +
                            " If you genuinely cannot execute any available tool for this capability, "
                            "explicitly state: 'I couldn't retrieve that GitHub data due to a capability limitation.'"
                        )
                        messages.append({
                            "role": "assistant",
                            "content": message.content or "I am ready."
                        })
                        messages.append({
                            "role": "system",
                            "content": force_prompt
                        })
                        continue  # Force one bounded recovery step
                    else:
                        # Recovery failed — honest answer
                        logger.error(
                            "[MCP INVARIANT FAILED] request_id=%s tools_called=%d: Aborting fabrication.",
                            request_id, len(tool_results)
                        )
                        final_content = "I couldn't retrieve that GitHub data."
                else:
                    # No tool calls — check evidence boundary before streaming final answer
                    # Task 5: Hard Evidence Boundary
                    if tool_results and evidence_states:
                        statuses = [e.get("evidence_status", "UNKNOWN") for e in evidence_states]
                        # If no capability succeeded or returned partial, prevent LLM from fabricating
                        if all(s not in ["SUCCESS", "PARTIAL"] for s in statuses):
                            logger.error(
                                "[EVIDENCE BOUNDARY] All evidence failed (%s). Aborting LLM fabrication.", statuses
                            )
                            if "NOT_FOUND" in statuses:
                                errors = [e.get("error") for e in evidence_states if e.get("evidence_status") == "NOT_FOUND" and e.get("error")]
                                msg = errors[0] if errors else "The requested GitHub data was not found."
                            elif "AMBIGUOUS" in statuses:
                                errors = [e.get("error") for e in evidence_states if e.get("evidence_status") == "AMBIGUOUS" and e.get("error")]
                                msg = errors[0] if errors else "The requested repository is ambiguous."
                            else:
                                msg = "I could not retrieve the required GitHub data to answer your question."
                            yield _sse({"type": "error", "message": msg})
                            return
                        
                        # Apply README Truncation constraint
                        for e in evidence_states:
                            if e.get("capability") == "README_CODE" and e.get("evidence_status") == "SUCCESS":
                                # The tool executor returns a structured object now:
                                # We check if it is truncated or marked partial
                                for tr in tool_results:
                                    if tr.get("evidence") == e:
                                        res_data = tr.get("result", {})
                                        if isinstance(res_data, dict) and (res_data.get("truncated") or res_data.get("status") == "PARTIAL"):
                                            e["evidence_status"] = "PARTIAL"
                                            # Ensure LLM uses only the retrieved portion
                                            logger.warning("[EVIDENCE BOUNDARY] README is partial/truncated. Marked PARTIAL.")

                    final_content = message.content or ""

                # Log final token usage
                if response.usage:
                    actual_in = response.usage.prompt_tokens
                    actual_out = response.usage.completion_tokens
                    # Summarize evidence states
                    ev_summary = [e.get("evidence_status", "UNKNOWN") for e in evidence_states]
                    logger.info(
                        "\n[CHAT RESULT]\n"
                        "request_id=%s\n"
                        "step=%d\n"
                        "source_mode=%s\n"
                        "capabilities=%s\n"
                        "actual_input_tokens=%d\n"
                        "output_tokens=%d\n"
                        "tools_called=%d\n"
                        "evidence_states=%s\n",
                        request_id, step, source_mode, capabilities,
                        actual_in, actual_out, len(tool_results), ev_summary
                    )

                # Stream the final answer character by character
                # (simulate streaming since we used non-streaming)
                chunk_size = 4  # emit in small chunks
                for i in range(0, len(final_content), chunk_size):
                    chunk = final_content[i:i + chunk_size]
                    yield _sse({"type": "message_delta", "content": chunk})
                    await asyncio.sleep(0)  # yield control

                # Emit sources if tools were used
                if tool_results:
                    sources = build_sources(tool_results)
                    if sources:
                        yield _sse({"type": "source", "sources": sources})

                yield _sse({"type": "message_completed"})
                return

            # Tool calls present — execute them
            # Append assistant message with tool calls to conversation
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)

            # Execute each tool call
            for tc in tool_calls:
                call_name = tc.function.name
                
                # Parse arguments
                try:
                    call_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    call_args = {}

                # Handle gateway tool unpacking from flat schema
                reduction = None
                if call_name == "github_mcp":
                    tool_name = call_args.get("tool_name", "")
                    args = {k: v for k, v in call_args.items() if not k.startswith("reduction_") and k != "tool_name"}
                    reduction_args = {k.replace("reduction_", ""): v for k, v in call_args.items() if k.startswith("reduction_")}
                    if reduction_args:
                        reduction = reduction_args
                    # CRITICAL FIX: inject active capability into reduction so tool_executor
                    # can log it and apply capability-aware projection.
                    # Without this, capability=None appears in all MCP execution logs.
                    active_cap = capabilities[0] if capabilities else None
                    if active_cap:
                        if reduction is None:
                            reduction = {}
                        reduction.setdefault("capability", active_cap)
                else:
                    tool_name = call_name
                    args = call_args
                    active_cap = capabilities[0] if capabilities else None
                    if active_cap:
                        reduction = {"capability": active_cap}

                tool_def = get_tool(tool_name)
                ui_label = tool_def["ui_label"] if tool_def else f"Consulting GitHub ({tool_name})"

                # 1. Duplicate/Loop Prevention
                signature = f"{tool_name}:{json.dumps(args, sort_keys=True)}:{json.dumps(reduction, sort_keys=True)}"
                if signature in executed_tool_signatures:
                    logger.warning("Duplicate tool call prevented: %s", signature)
                    result = {
                        "success": False,
                        "tool_name": tool_name,
                        "result": None,
                        "error": "DUPLICATE_CALL: You already executed this exact tool call in this request. Please review your previous tool results instead of repeating the call. If you need different data, change the arguments or reduction plan.",
                    }
                else:
                    executed_tool_signatures.add(signature)
                    yield _sse({
                        "type": "tool_started",
                        "tool": tool_name,
                        "label": ui_label,
                    })

                    # Execute via FastAPI tool executor (never direct from LLM)
                    result = await execute_tool(tool_name, args, reduction)
                    tool_results.append(result)

                    # Track evidence state
                    evidence = result.get("evidence", {})
                    if evidence:
                        evidence_states.append(evidence)
                        ev_status = evidence.get("evidence_status", "UNKNOWN")
                        repo_status = evidence.get("error", "")[:80] if ev_status != "SUCCESS" else ""
                        logger.info(
                            "[TOOL EVIDENCE] request_id=%s tool=%s capability=%s evidence_status=%s%s",
                            request_id, tool_name,
                            evidence.get("capability", ""),
                            ev_status,
                            f" error={repo_status}" if repo_status else ""
                        )

                    yield _sse({
                        "type": "tool_completed",
                        "tool": tool_name,
                        "success": result["success"],
                    })

                # Append tool result to messages
                tool_result_content = (
                    json.dumps(result["result"], default=str)
                    if result["success"] and result["result"] is not None
                    else result.get("error", "Tool execution failed.")
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result_content,
                })

            # 2. Tool-Wandering Prevention
            if len(executed_tool_signatures) >= 4:
                messages.append({
                    "role": "system",
                    "content": "WANDERING_PREVENTION: You have made several tool calls. Please synthesize the accumulated data to answer the user now. Do not call additional tools unless absolutely required to fulfill a specific unresolved element of your QueryPlan."
                })

        # If we reach here, we hit MAX_AGENT_STEPS
        logger.warning("Agent reached MAX_AGENT_STEPS (%d)", MAX_AGENT_STEPS)
        yield _sse({
            "type": "message_delta",
            "content": "I've analyzed the available information. Based on what I found, please check your dashboard for the most up-to-date details, or try rephrasing your question for a more focused answer.",
        })
        if tool_results:
            sources = build_sources(tool_results)
            if sources:
                yield _sse({"type": "source", "sources": sources})
        yield _sse({"type": "message_completed"})

    except asyncio.CancelledError:
        logger.info("Agent generator cancelled")
        return
    except Exception as e:
        logger.error("Agent loop unexpected error: %s", str(e), exc_info=True)
        yield _sse({"type": "error", "message": "Something went wrong. Please try again."})
