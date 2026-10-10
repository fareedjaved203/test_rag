import { useState, useRef, useEffect, FormEvent } from "react";

interface SystemEvent {
  type: "system";
  node: string;
  title: string;
  content: string;
}

interface ToolStartEvent {
  type: "tool_start";
  tool_call_id: string;
  tool_name: string;
}

interface ToolResultEvent {
  type: "tool_result";
  tool_call_id: string;
  tool_name: string;
  content: string;
}

interface TokenEvent {
  type: "token";
  content: string;
}

interface ClarificationEvent {
  type: "clarification";
  content: string;
}

type StreamEvent =
  | SystemEvent
  | ToolStartEvent
  | ToolResultEvent
  | TokenEvent
  | ClarificationEvent
  | { type: "done" }
  | { type: "error"; content: string };

interface Message {
  role: "user" | "assistant";
  content: string;
  events?: StreamEvent[];
}

interface ToolCall {
  id: string;
  name: string;
  result?: string;
}

// Collapsible detail block
function Details({ summary, children }: { summary: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1"
      >
        <span>{open ? "▾" : "▸"}</span>
        {summary}
      </button>
      {open && (
        <div className="mt-2 pl-3 border-l border-gray-700 text-gray-400 whitespace-pre-wrap">
          {children}
        </div>
      )}
    </div>
  );
}

function AssistantBubble({ msg }: { msg: Message }) {
  const systemMap: Record<string, string> = {};
  const toolCalls: Record<string, ToolCall> = {};

  for (const ev of msg.events ?? []) {
    if (ev.type === "system") systemMap[ev.node] = ev.content;
    if (ev.type === "tool_start")
      toolCalls[ev.tool_call_id] = { id: ev.tool_call_id, name: ev.tool_name };
    if (ev.type === "tool_result" && toolCalls[ev.tool_call_id])
      toolCalls[ev.tool_call_id].result = ev.content;
  }

  return (
    <div className="flex flex-col gap-1 max-w-[85%]">
      {/* System node details */}
      {Object.entries(systemMap).map(([node, content]) => (
        <Details key={node} summary={node === "rewrite_query" ? "Query analysis" : "History summary"}>
          {content}
        </Details>
      ))}

      {/* Tool calls */}
      {Object.values(toolCalls).map((tc) => (
        <Details key={tc.id} summary={`Tool: ${tc.name}`}>
          {tc.result ?? "Running..."}
        </Details>
      ))}

      {/* Answer */}
      {msg.content && (
        <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed">
          {msg.content}
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const token = localStorage.getItem("token");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    setInput("");
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);

    const assistantMsg: Message = { role: "assistant", content: "", events: [] };
    setMessages((prev) => [...prev, assistantMsg]);
    setStreaming(true);

    try {
      const response = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });

      const reader = response.body!.getReader();
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
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const event: StreamEvent = JSON.parse(raw);
            setMessages((prev) => {
              const updated = [...prev];
              const last = { ...updated[updated.length - 1] };
              if (event.type === "token") {
                last.content = (last.content ?? "") + event.content;
              } else if (event.type === "clarification") {
                last.content = event.content;
              } else if (event.type !== "done" && event.type !== "error") {
                last.events = [...(last.events ?? []), event];
              } else if (event.type === "error") {
                last.content = `Error: ${event.content}`;
              }
              updated[updated.length - 1] = last;
              return updated;
            });
          } catch {
            // malformed JSON line, skip
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Connection error. Is the server running?",
        };
        return updated;
      });
    } finally {
      setStreaming(false);
    }
  };

  const clearChat = async () => {
    try {
      await fetch("http://localhost:8000/chat/clear", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // ignore
    }
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800">
        <span className="text-sm font-medium">Chat</span>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-600 text-sm mt-16">
            Ask anything about your uploaded documents
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "user" ? (
              <div className="bg-indigo-600 rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[75%] whitespace-pre-wrap">
                {msg.content}
              </div>
            ) : (
              <AssistantBubble msg={msg} />
            )}
          </div>
        ))}
        {streaming && messages[messages.length - 1]?.content === "" && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl px-4 py-3">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={sendMessage}
        className="px-6 py-4 border-t border-gray-800 flex gap-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
          placeholder="Ask a question..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors"
        >
          Send
        </button>
      </form>
    </div>
  );
}
