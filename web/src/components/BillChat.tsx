"use client";

import { useState, useRef, useEffect } from "react";
import { Send, MessageCircle, X, Settings } from "lucide-react";
import { loadSettings } from "@/lib/settings";
import { getProviderLabel } from "@/lib/llm";
import SettingsModal from "./SettingsModal";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function BillChat({ billId }: { billId: number }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const settings = loadSettings();
  const hasAiKey = settings.aiApiKey.length > 0;

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const resp = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          billId,
          question,
          provider: settings.aiProvider,
          apiKey: settings.aiApiKey,
          model: settings.aiModel || undefined,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${data.error}` },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.answer },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Network error. Try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 bg-accent text-bg w-14 h-14 rounded-full flex items-center justify-center shadow-lg hover:bg-accent-dim hover:text-white transition-colors z-40"
        title="Ask about this bill"
      >
        <MessageCircle className="w-6 h-6" />
      </button>
    );
  }

  return (
    <>
      <div className="fixed bottom-6 right-6 w-96 max-h-[600px] bg-surface border border-border rounded-lg shadow-xl flex flex-col z-40">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="font-semibold text-sm">Ask about this bill</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(true)}
              className="text-text-dim hover:text-text"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
            <button
              onClick={() => setOpen(false)}
              className="text-text-dim hover:text-text"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[400px]">
          {messages.length === 0 && (
            <div className="text-text-dim text-sm text-center mt-8">
              {hasAiKey ? (
                <>
                  <p>Ask anything about this bill.</p>
                  <p className="text-xs mt-2">
                    Using {getProviderLabel(settings.aiProvider)}
                  </p>
                </>
              ) : (
                <p>
                  Add your AI API key in{" "}
                  <button
                    onClick={() => setShowSettings(true)}
                    className="text-accent hover:underline"
                  >
                    Settings
                  </button>{" "}
                  to start chatting.
                </p>
              )}
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`text-sm ${
                msg.role === "user"
                  ? "text-right"
                  : "text-left"
              }`}
            >
              <div
                className={`inline-block max-w-[85%] rounded-lg px-3 py-2 ${
                  msg.role === "user"
                    ? "bg-accent/20 text-text"
                    : "bg-bg border border-border text-text-dim"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="text-left">
              <div className="inline-block bg-bg border border-border rounded-lg px-3 py-2 text-text-dim text-sm">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form
          onSubmit={handleSend}
          className="border-t border-border p-3 flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              hasAiKey
                ? "Ask a question..."
                : "Configure AI key in Settings first"
            }
            disabled={!hasAiKey || loading}
            className="flex-1 bg-bg border border-border rounded px-3 py-2 text-sm focus:border-accent focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!hasAiKey || loading || !input.trim()}
            className="bg-accent text-bg px-3 py-2 rounded hover:bg-accent-dim hover:text-white transition-colors disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </>
  );
}
