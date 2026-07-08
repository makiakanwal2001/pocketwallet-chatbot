"use client";

import { useState, useRef, useEffect } from "react";
import { sendMessage } from "@/lib/api";

interface Props {
  token:    string;
  onLogout: () => void;
}

interface ChatMessage {
  role:      "user" | "assistant";
  content:   string;
  intent?:   string;
  sentiment?:string;
  citations?:string[];
  escalated?:boolean;
  tool?:     string;
}

const SUGGESTED = [
  "What is my current balance?",
  "What are the IBFT transfer fees?",
  "How do I freeze my card?",
  "What documents do I need for KYC?",
];

export default function ChatPage({ token, onLogout }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role:    "assistant",
      content: "Hello! I am PocketWallet AI Support. How can I help you today?",
    },
  ]);
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(text?: string) {
    const msg = text || input.trim();
    if (!msg || loading) return;

    setInput("");
    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const resp = await sendMessage(token, msg);
      setMessages(prev => [...prev, {
        role:      "assistant",
        content:   resp.answer,
        intent:    resp.intent,
        sentiment: resp.sentiment,
        citations: resp.citations,
        escalated: resp.escalated,
        tool:      resp.tool_called !== "none" ? resp.tool_called : undefined,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role:    "assistant",
        content: "Sorry, something went wrong. Please try again.",
      }]);
    } finally {
      setLoading(false);
    }
  }

  const sentimentColor = (s?: string) => {
    if (s === "angry")     return "text-red-400";
    if (s === "frustrated")return "text-orange-400";
    if (s === "positive")  return "text-emerald-400";
    return "text-gray-400";
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">

      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">PW</span>
          </div>
          <div>
            <p className="text-white font-semibold text-sm">PocketWallet Support</p>
            <p className="text-emerald-400 text-xs">● Online</p>
          </div>
        </div>
        <button onClick={onLogout} className="text-gray-400 hover:text-white text-sm">
          Sign out
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] ${msg.role === "user" ? "order-2" : ""}`}>

              {/* Bubble */}
              <div className={`rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-emerald-500 text-white rounded-br-sm"
                  : "bg-gray-800 text-gray-100 rounded-bl-sm"
              }`}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>

              {/* Metadata (assistant only) */}
              {msg.role === "assistant" && (msg.intent || msg.citations?.length) && (
                <div className="mt-1 px-1 space-y-1">
                  {msg.intent && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded-full">
                        {msg.intent}
                      </span>
                      {msg.sentiment && (
                        <span className={`text-xs ${sentimentColor(msg.sentiment)}`}>
                          {msg.sentiment}
                        </span>
                      )}
                      {msg.tool && (
                        <span className="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full">
                          ⚡ {msg.tool}
                        </span>
                      )}
                      {msg.escalated && (
                        <span className="text-xs bg-red-900 text-red-300 px-2 py-0.5 rounded-full">
                          ⚠ escalated
                        </span>
                      )}
                    </div>
                  )}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="text-xs text-gray-500">
                      📎 {msg.citations[0]}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:"0ms"}}/>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:"150ms"}}/>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:"300ms"}}/>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested actions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex gap-2 flex-wrap">
          {SUGGESTED.map(s => (
            <button
              key={s}
              onClick={() => handleSend(s)}
              className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-2 rounded-full border border-gray-700 transition"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="bg-gray-900 border-t border-gray-800 px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSend()}
            placeholder="Type your message..."
            className="flex-1 bg-gray-800 text-white rounded-xl px-4 py-3 border border-gray-700 focus:border-emerald-500 focus:outline-none text-sm"
            disabled={loading}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl px-4 py-3 transition disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
