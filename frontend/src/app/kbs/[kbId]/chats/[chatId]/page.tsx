"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { connectChatSocket, joinChatRoom } from "@/lib/socket-client";

type Citation = {
  document_id: string;
  chunk_id: string;
  filename_original: string;
  page_start?: number | null;
  viewer_path?: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

export default function ChatPage() {
  const params = useParams<{ kbId: string; chatId: string }>();
  const kbId = params.kbId;
  const chatId = params.chatId;
  const { user, ready } = useAuth();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const assistantBuf = useRef("");
  const streamingMessageId = useRef<string | null>(null);

  const loadHistory = useCallback(async () => {
    const r = await api.get(`/api/kbs/${kbId}/chats/${chatId}/messages`);
    const items = r.data.items as Array<{
      role: string;
      content: string;
      citations?: Citation[];
    }>;
    setMessages(
      items.map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
        citations: m.citations,
      })),
    );
  }, [kbId, chatId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (!ready || !user) return;

    let active = true;
    const socketRef = { current: null as Awaited<ReturnType<typeof connectChatSocket>> | null };

    const onToken = (payload: {
      chat_id: string;
      message_id: string;
      token: string;
    }) => {
      if (!active || payload.chat_id !== chatId) return;
      if (
        streamingMessageId.current &&
        payload.message_id !== streamingMessageId.current
      ) {
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

    const onCitation = (payload: {
      chat_id?: string;
      citations: Citation[];
    }) => {
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

    const onDone = (payload: {
      chat_id: string;
      status: string;
      error?: string;
    }) => {
      if (!active || payload.chat_id !== chatId) return;
      setStreaming(false);
      streamingMessageId.current = null;
      if (payload.status === "ERROR") {
        assistantBuf.current = "";
        setError(
          payload.error ??
            "No se pudo generar la respuesta. Revisa el backend (Ollama, Qdrant).",
        );
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
        setError("Inicia sesión para usar el chat.");
        setStreaming(false);
        return;
      }
      await joinChatRoom(chatId);
      const res = await api.post(
        `/api/kbs/${kbId}/chats/${chatId}/messages`,
        { content: text, stream: true },
      );
      const messageId = res.data?.message_id as string | undefined;
      if (messageId) {
        streamingMessageId.current = messageId;
      }
    } catch (e) {
      setStreaming(false);
      streamingMessageId.current = null;
      setError(e instanceof Error ? e.message : "Error al enviar mensaje.");
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 p-6 pb-16">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-semibold">Chat</h1>
        <Link
          href={`/kbs/${kbId}/chats`}
          className="text-sm text-muted-foreground underline-offset-4 hover:underline"
        >
          ← Todos los chats
        </Link>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <MessageList messages={messages} streaming={streaming} />
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2 text-sm"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void sendMessage();
            }
          }}
          placeholder="Escribe tu pregunta…"
          disabled={streaming}
        />
        <button
          type="button"
          className="rounded bg-black px-4 py-2 text-sm text-white disabled:opacity-50"
          onClick={() => void sendMessage()}
          disabled={streaming || !input.trim()}
        >
          Enviar
        </button>
      </div>
    </main>
  );
}

function MessageList({
  messages,
  streaming,
}: {
  messages: Message[];
  streaming: boolean;
}) {
  return (
    <div className="flex min-h-[320px] flex-col gap-3 rounded border p-4">
      {messages.map((m, i) => {
        const isLastAssistant =
          streaming && i === messages.length - 1 && m.role === "assistant";
        const showPlaceholder =
          m.role === "assistant" && !m.content.trim() && isLastAssistant;
        return (
          <div
            key={`${m.role}-${i}`}
            className={
              m.role === "user"
                ? "self-end rounded bg-slate-100 px-3 py-2 text-sm"
                : "self-start rounded border px-3 py-2 text-sm"
            }
          >
            <p className="whitespace-pre-wrap">
              {showPlaceholder ? "…" : m.content}
            </p>
            {m.citations && m.citations.length > 0 && (
              <ul className="mt-2 text-xs text-slate-600">
                {m.citations.map((c) => (
                  <li key={c.chunk_id}>
                    {c.filename_original}
                    {c.page_start != null ? ` (pág. ${c.page_start})` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
