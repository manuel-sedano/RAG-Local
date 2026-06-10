"use client";

import { Loader2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { ErrorState, LoadingState } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { es } from "@/lib/i18n/es";
import { connectChatSocket, joinChatRoom } from "@/lib/socket-client";
import { cn } from "@/lib/utils";

type Citation = {
  document_id: string;
  chunk_id: string;
  filename_original: string;
  page_start?: number | null;
  viewer_path?: string;
};

type SafetyFlags = {
  user_notice?: string | null;
  ignored_chunks?: number | null;
  user_query_blocked?: boolean | null;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  safety_flags?: SafetyFlags | null;
};

export default function ChatPage() {
  const params = useParams<{ kbId: string; chatId: string }>();
  const kbId = params.kbId;
  const chatId = params.chatId;
  const { user, ready } = useAuth();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const assistantBuf = useRef("");
  const streamingMessageId = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const r = await api.get(`/api/kbs/${kbId}/chats/${chatId}/messages`);
      const items = r.data.items as Array<{
        role: string;
        content: string;
        citations?: Citation[];
        safety_flags?: SafetyFlags | null;
      }>;
      setMessages(
        items.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          citations: m.citations,
          safety_flags: m.safety_flags,
        })),
      );
    } finally {
      setHistoryLoading(false);
    }
  }, [kbId, chatId]);

  /* eslint-disable react-hooks/set-state-in-effect -- historial al abrir chat */
  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  useEffect(() => {
    if (!ready || !user) return;

    let active = true;
    const socketRef = { current: null as Awaited<ReturnType<typeof connectChatSocket>> | null };

    const onToken = (payload: { chat_id: string; message_id: string; token: string }) => {
      if (!active || payload.chat_id !== chatId) return;
      if (streamingMessageId.current && payload.message_id !== streamingMessageId.current) {
        return;
      }
      assistantBuf.current += payload.token;
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last?.role === "assistant") {
          copy[copy.length - 1] = { ...last, content: assistantBuf.current };
          return copy;
        }
        return [...copy, { role: "assistant", content: assistantBuf.current }];
      });
    };

    const onCitation = (payload: { chat_id?: string; citations: Citation[] }) => {
      if (!active) return;
      if (payload.chat_id && payload.chat_id !== chatId) return;
      setMessages((prev) => {
        const copy = [...prev];
        for (let i = copy.length - 1; i >= 0; i -= 1) {
          if (copy[i].role === "assistant") {
            copy[i] = { ...copy[i], citations: payload.citations };
            break;
          }
        }
        return copy;
      });
    };

    const onDone = (payload: { chat_id: string; status: string; error?: string }) => {
      if (!active || payload.chat_id !== chatId) return;
      setStreaming(false);
      streamingMessageId.current = null;
      if (payload.status === "ERROR") {
        assistantBuf.current = "";
        setError(payload.error ?? es.chat.errorGeneration);
        void loadHistory();
        return;
      }
      const streamed = assistantBuf.current;
      assistantBuf.current = "";
      if (streamed.trim()) {
        setMessages((prev) => {
          const copy = [...prev];
          for (let i = copy.length - 1; i >= 0; i -= 1) {
            if (copy[i].role === "assistant") {
              copy[i] = { ...copy[i], content: streamed };
              break;
            }
          }
          return copy;
        });
        return;
      }
      void loadHistory();
    };

    void (async () => {
      try {
        const s = await connectChatSocket();
        socketRef.current = s;
        if (!active) return;
        s.on("chat:token", onToken);
        s.on("chat:citation", onCitation);
        s.on("chat:done", onDone);
        await joinChatRoom(chatId);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : String(e));
      }
    })();

    return () => {
      active = false;
      const s = socketRef.current;
      if (s) {
        s.off("chat:token", onToken);
        s.off("chat:citation", onCitation);
        s.off("chat:done", onDone);
      }
    };
  }, [chatId, loadHistory, ready, user]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || streaming) return;
    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    assistantBuf.current = "";
    streamingMessageId.current = null;
    setStreaming(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      if (!ready || !user) {
        setError(es.chat.errorAuth);
        setStreaming(false);
        return;
      }
      await joinChatRoom(chatId);
      const res = await api.post(`/api/kbs/${kbId}/chats/${chatId}/messages`, {
        content: text,
        stream: true,
      });
      const messageId = res.data?.message_id as string | undefined;
      if (messageId) {
        streamingMessageId.current = messageId;
      }
    } catch (e) {
      setStreaming(false);
      streamingMessageId.current = null;
      setError(e instanceof Error ? e.message : es.chat.errorSend);
    }
  }

  if (!ready || !user) {
    return <LoadingState fullPage message={es.states.loadingSession} />;
  }

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] max-h-[calc(100dvh-3.5rem)] flex-col md:h-[calc(100dvh-3.5rem-2.5rem)]">
      <header className="shrink-0 border-b px-4 py-3 sm:px-6">
        <h1 className="text-lg font-semibold">{es.chat.title}</h1>
        <p className="text-xs text-muted-foreground">
          {streaming ? es.chat.streaming : es.chat.subtitle}
        </p>
      </header>

      {error ? (
        <div className="shrink-0 px-4 pt-3 sm:px-6">
          <ErrorState message={error} onRetry={() => setError(null)} />
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        {historyLoading && messages.length === 0 ? (
          <LoadingState message={es.states.loading} />
        ) : (
          <MessageList messages={messages} streaming={streaming} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 border-t bg-background px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
            placeholder={es.chat.inputPlaceholder}
            disabled={streaming}
            aria-label={es.chat.inputPlaceholder}
          />
          <Button
            type="button"
            onClick={() => void sendMessage()}
            disabled={streaming || !input.trim()}
          >
            {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : es.chat.send}
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageList({
  messages,
  streaming,
}: {
  messages: Message[];
  streaming: boolean;
}) {
  if (messages.length === 0) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        Escribe una pregunta sobre los documentos de esta base.
      </p>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-3">
      {messages.map((m, i) => {
        const isLastAssistant = streaming && i === messages.length - 1 && m.role === "assistant";
        const showPlaceholder = m.role === "assistant" && !m.content.trim() && isLastAssistant;
        return (
          <div
            key={`${m.role}-${i}`}
            className={cn(
              "max-w-[90%] rounded-lg px-3 py-2 text-sm",
              m.role === "user"
                ? "ml-auto bg-primary text-primary-foreground"
                : "mr-auto border bg-card",
            )}
          >
            <p className="whitespace-pre-wrap">{showPlaceholder ? "…" : m.content}</p>
            {m.role === "assistant" && m.safety_flags?.user_notice ? (
              <p className="mt-2 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                {m.safety_flags.user_notice}
              </p>
            ) : null}
            {m.citations && m.citations.length > 0 ? (
              <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
                {m.citations.map((c) => (
                  <li key={c.chunk_id}>
                    {c.filename_original}
                    {c.page_start != null ? ` (pág. ${c.page_start})` : ""}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
