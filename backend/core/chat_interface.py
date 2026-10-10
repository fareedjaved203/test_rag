import json
import re
from langchain_core.messages import HumanMessage, AIMessageChunk, ToolMessage
from core.execution_logger import log_chat_end, log_chat_start, log_error

SYSTEM_NODES = {"summarize_history", "rewrite_query"}
FINAL_RESPONSE_NODES = {"aggregate_answers"}

SYSTEM_NODE_CONFIG = {
    "rewrite_query": {"title": "Query Analysis & Rewriting"},
    "summarize_history": {"title": "Chat History Summary"},
}


def _parse_rewrite_json(buffer: str) -> dict | None:
    match = re.search(r"\{.*\}", buffer, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except Exception:
        return None


def _format_rewrite_content(buffer: str) -> str:
    data = _parse_rewrite_json(buffer)
    if not data:
        return "Analyzing query..."
    if data.get("is_clear"):
        lines = ["Query is clear"]
        if data.get("questions"):
            lines += ["Rewritten queries:"] + [f"- {q}" for q in data["questions"]]
    else:
        lines = ["Query is unclear"]
        clarification = data.get("clarification_needed", "")
        if clarification and clarification.strip().lower() != "no":
            lines.append(f"Clarification needed: {clarification}")
    return "\n".join(lines)


class ChatInterface:

    def __init__(self, rag_system):
        self.rag_system = rag_system

    def stream(self, message: str):
        """
        Generator yielding SSE-compatible JSON strings.
        Each yielded value is a dict serialised to JSON:
          { "type": "system"|"tool_start"|"tool_result"|"token"|"clarification"|"error"|"done" }
        """
        if not self.rag_system.agent_graph:
            yield json.dumps({"type": "error", "content": "System not initialized"})
            return

        cfg = self.rag_system.get_config()
        current_state = self.rag_system.agent_graph.get_state(cfg)
        log_chat_start(message.strip(), self.rag_system.thread_id, bool(current_state.next))

        try:
            if current_state.next:
                self.rag_system.agent_graph.update_state(
                    cfg, {"messages": [HumanMessage(content=message.strip())]}
                )
                stream_input = None
            else:
                stream_input = {"messages": [HumanMessage(content=message.strip())]}

            system_node_buffer: dict[str, str] = {}
            active_tool_calls: dict[str, str] = {}  # tool_call_id -> tool_name

            for chunk, metadata in self.rag_system.agent_graph.stream(
                stream_input, config=cfg, stream_mode="messages"
            ):
                node = metadata.get("langgraph_node", "")

                # --- System nodes (query rewrite / history summary) ---
                if node in SYSTEM_NODES and isinstance(chunk, AIMessageChunk) and chunk.content:
                    system_node_buffer[node] = system_node_buffer.get(node, "") + chunk.content
                    buf = system_node_buffer[node]
                    content = _format_rewrite_content(buf) if node == "rewrite_query" else buf
                    yield json.dumps({
                        "type": "system",
                        "node": node,
                        "title": SYSTEM_NODE_CONFIG[node]["title"],
                        "content": content,
                    })

                    # Surface clarification question if query is unclear
                    if node == "rewrite_query":
                        data = _parse_rewrite_json(buf) or {}
                        clarification = data.get("clarification_needed", "")
                        if not data.get("is_clear") and clarification.strip().lower() not in ("", "no"):
                            yield json.dumps({"type": "clarification", "content": clarification})

                # --- Tool calls starting ---
                elif hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        if tc.get("id") and tc["id"] not in active_tool_calls:
                            active_tool_calls[tc["id"]] = tc["name"]
                            yield json.dumps({
                                "type": "tool_start",
                                "tool_call_id": tc["id"],
                                "tool_name": tc["name"],
                            })

                # --- Tool results ---
                elif isinstance(chunk, ToolMessage):
                    preview = str(chunk.content)[:300]
                    suffix = "..." if len(str(chunk.content)) > 300 else ""
                    yield json.dumps({
                        "type": "tool_result",
                        "tool_call_id": chunk.tool_call_id,
                        "tool_name": active_tool_calls.get(chunk.tool_call_id, "tool"),
                        "content": preview + suffix,
                    })

                # --- Final answer tokens ---
                elif (
                    isinstance(chunk, AIMessageChunk)
                    and chunk.content
                    and node in FINAL_RESPONSE_NODES
                ):
                    yield json.dumps({"type": "token", "content": chunk.content})

            final_state = self.rag_system.agent_graph.get_state(cfg)
            log_chat_end(getattr(final_state, "values", final_state))
            yield json.dumps({"type": "done"})

        except Exception as e:
            log_error("chat", e)
            yield json.dumps({"type": "error", "content": str(e)})

    def clear_session(self):
        self.rag_system.reset_thread()
        self.rag_system.observability.flush()
