"use client";

import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Bot, Compass } from "lucide-react";
import {
  useSendMessage,
  useSession,
  useSessions,
} from "@/hooks/use-assistant";

const SUGGESTED_QUERIES = [
  "What is my portfolio summary?",
  "How much BTC and USDT do I have?",
  "What is the current BTC price and 24h change?",
  "Show me ETH daily candlestick trends",
  "Is my exchange currently connected?",
];

function FormattedMessage({ content }) {
  // Simple, safe formatter for assistant responses preserving paragraphs and bullet points
  const lines = content.split("\n");
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }
        if (trimmed.startsWith("•") || trimmed.startsWith("-") || trimmed.startsWith("*")) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="text-primary font-bold">•</span>
              <span>{trimmed.replace(/^[•\-*]\s*/, "")}</span>
            </div>
          );
        }
        if (trimmed.startsWith("##") || trimmed.startsWith("#")) {
          return (
            <h4 key={idx} className="font-semibold text-foreground mt-2 mb-1">
              {trimmed.replace(/^#+\s*/, "")}
            </h4>
          );
        }
        return <p key={idx}>{line}</p>;
      })}
    </div>
  );
}

export default function AssistantPageClient() {
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [inputMessage, setInputMessage] = useState("");
  const [localMessages, setLocalMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const messageIdRef = useRef(0);

  const { data: sessions, isLoading: sessionsLoading } = useSessions();
  const { data: sessionDetail, isLoading: sessionLoading } = useSession(activeSessionId);
  const { mutate: sendMessage, isPending: isSending, error: sendError } = useSendMessage();

  // Synchronize active session history into local view
  useEffect(() => {
    if (sessionDetail?.messages) {
      // The local copy also contains optimistic messages while a request is pending.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLocalMessages(sessionDetail.messages);
    } else if (!activeSessionId) {
      setLocalMessages([]);
    }
  }, [sessionDetail, activeSessionId]);

  // Scroll to bottom whenever messages or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages, isSending]);

  const handleSend = (textToSend) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isSending) return;

    // Optimistically append user message
    const tempUserMsg = {
      id: "temp-" + ++messageIdRef.current,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    setLocalMessages((prev) => [...prev, tempUserMsg]);
    setInputMessage("");

    sendMessage(
      { message: text, sessionId: activeSessionId },
      {
        onSuccess: (data) => {
          if (!activeSessionId && data.session_id) {
            setActiveSessionId(data.session_id);
          }
          const assistantMsg = {
            id: "resp-" + ++messageIdRef.current,
            role: data.role || "assistant",
            content: data.message,
            created_at: data.created_at,
          };
          setLocalMessages((prev) => [...prev, assistantMsg]);
        },
        onError: (err) => {
          const detail =
            err.response?.data?.detail ||
            "Unable to get a response from the assistant. Please try again.";
          const errorMsg = {
            id: "err-" + ++messageIdRef.current,
            role: "assistant",
            content: `⚠️ ${detail}`,
            created_at: new Date().toISOString(),
            isError: true,
          };
          setLocalMessages((prev) => [...prev, errorMsg]);
        },
      }
    );
  };

  const handleStartNewChat = () => {
    setActiveSessionId(null);
    setLocalMessages([]);
    setInputMessage("");
  };

  return (
    <div className="prism-page max-w-7xl h-[calc(100vh-6.5rem)] flex flex-col md:flex-row gap-4">
      {/* Sidebar / Session History */}
      <aside className="prism-surface w-full md:w-72 flex-shrink-0 flex flex-col gap-3 p-3 h-48 md:h-full overflow-hidden">
        <div className="flex items-center justify-between px-1">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground"><Compass className="size-4 text-primary" /> Conversations</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={handleStartNewChat}
            id="new-chat-btn"
            className="text-xs h-7 px-2"
          >
            + New
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          {sessionsLoading && (
            <div className="space-y-2 py-2">
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-full rounded-lg" />
              <Skeleton className="h-8 w-full rounded-lg" />
            </div>
          )}

          {!sessionsLoading && (!sessions || sessions.length === 0) && (
            <p className="text-xs text-muted-foreground p-3 text-center">
              No previous chats yet.
            </p>
          )}

          {!sessionsLoading &&
            sessions?.map((s) => {
              const isActive = activeSessionId === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSessionId(s.id)}
                  className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition-colors flex flex-col gap-0.5 ${
                    isActive
                      ? "bg-primary text-primary-foreground font-medium"
                      : "hover:bg-accent text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="truncate">{s.title || "Untitled Conversation"}</span>
                  <span className={`text-[10px] ${isActive ? "text-primary-foreground/70" : "text-muted-foreground/60"}`}>
                    {new Date(s.updated_at).toLocaleDateString()}
                  </span>
                </button>
              );
            })}
        </div>

        <div className="border-t pt-2 px-1">
          <p className="text-[11px] text-muted-foreground leading-tight">
            🔒 Read-only intelligence powered by LangGraph + Groq.
          </p>
        </div>
      </aside>

      {/* Main Chat Area */}
      <section className="prism-surface flex-1 flex flex-col overflow-hidden">
        {/* Chat Header */}
        <div className="px-5 py-3 border-b flex items-center justify-between bg-card/80 backdrop-blur">
          <div>
            <h1 className="text-base font-semibold tracking-tight flex items-center gap-2">
              <span className="grid size-7 place-items-center rounded-lg bg-primary/15 text-primary"><Bot className="size-4" /></span> PrismAI Assistant
              <Badge variant="secondary" className="text-[10px] font-normal">
                Read-Only
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground">
              Natural-language portfolio intelligence and real-time market queries
            </p>
          </div>
          {activeSessionId && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleStartNewChat}
              className="text-xs hidden md:inline-flex"
            >
              Start New Chat
            </Button>
          )}
        </div>

        {/* Message Feed */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {sessionLoading && activeSessionId && (
            <div className="space-y-3 py-6">
              <Skeleton className="h-16 w-3/4 rounded-xl" />
              <Skeleton className="h-20 w-3/4 ml-auto rounded-xl" />
              <Skeleton className="h-16 w-3/4 rounded-xl" />
            </div>
          )}

          {/* Empty State */}
          {!sessionLoading && localMessages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-6">
              <div className="space-y-2 max-w-md">
                <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto text-xl font-bold">
                  ✨
                </div>
                <h3 className="text-lg font-medium tracking-tight">
                  How can I help you today?
                </h3>
                <p className="text-xs text-muted-foreground">
                  Ask about your holdings, current crypto prices, 24h trends, or
                  candlestick ranges across your connected exchange.
                </p>
              </div>

              <div className="w-full max-w-lg space-y-2">
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Suggested Questions
                </p>
                <div className="flex flex-col gap-2">
                  {SUGGESTED_QUERIES.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(q)}
                      className="text-left text-xs px-3.5 py-2.5 rounded-lg border bg-background hover:bg-accent hover:text-accent-foreground transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Message List */}
          {localMessages.map((msg, index) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id || index}
                className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 ${
                    isUser
                      ? "bg-primary text-primary-foreground rounded-br-none"
                      : "bg-muted/70 text-foreground border rounded-bl-none"
                  }`}
                >
                  {isUser ? (
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <FormattedMessage content={msg.content} />
                  )}
                </div>
                <span className="text-[10px] text-muted-foreground/60 px-1 mt-1">
                  {msg.created_at
                    ? new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : ""}
                </span>
              </div>
            );
          })}

          {/* Sending / Thinking Indicator */}
          {isSending && (
            <div className="flex items-start gap-2">
              <div className="bg-muted/70 border rounded-2xl rounded-bl-none px-4 py-3 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Message Input Box */}
        <div className="p-3 md:p-4 border-t bg-card">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex gap-2"
          >
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about your crypto portfolio, market prices, trends..."
              disabled={isSending}
              className="flex-1 bg-background"
              maxLength={2000}
              id="assistant-chat-input"
              autoComplete="off"
            />
            <Button
              type="submit"
              disabled={isSending || !inputMessage.trim()}
              id="assistant-send-btn"
            >
              {isSending ? "Thinking…" : "Send"}
            </Button>
          </form>
          <div className="flex justify-between items-center px-1 mt-2 text-[10px] text-muted-foreground">
            <span>Press Enter to send</span>
            <span>Does not execute trades or provide financial advice</span>
          </div>
        </div>
      </section>
    </div>
  );
}
