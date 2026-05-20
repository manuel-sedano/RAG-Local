"use client";

import { Loader2, MessageSquare, Plus } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type ChatListItem = {
  chat_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export default function KbChatsPage() {
  const params = useParams<{ kbId: string }>();
  const kbId = params.kbId ?? "";
  const router = useRouter();
  const { user, ready } = useAuth();

  const [items, setItems] = useState<ChatListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  const loadChats = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get<{ items: ChatListItem[] }>(`/api/kbs/${kbId}/chats`);
      setItems(r.data.items);
    } catch (e: unknown) {
      toast.error(formatApiError(e, "No se pudo cargar los chats."));
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  useEffect(() => {
    if (user && kbId) void loadChats();
  }, [user, kbId, loadChats]);

  async function createChat(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const r = await api.post<{ chat_id: string }>(`/api/kbs/${kbId}/chats`, {
        title: title.trim() || null,
      });
      toast.success("Chat creado.");
      setTitle("");
      router.push(`/kbs/${kbId}/chats/${r.data.chat_id}`);
    } catch (err: unknown) {
      toast.error(formatApiError(err, "No se pudo crear el chat."));
    } finally {
      setCreating(false);
    }
  }

  if (!ready || !user) {
    return (
      <main className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6 pb-16">
      <ChatsPageHeader kbId={kbId} />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Nuevo chat</CardTitle>
          <CardDescription>Título opcional. Podrás hacer preguntas con RAG y streaming.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={createChat}>
            <div className="grid flex-1 gap-2">
              <Label htmlFor="chat-title">Título</Label>
              <Input
                id="chat-title"
                value={title}
                onChange={(ev) => setTitle(ev.target.value)}
                placeholder="p. ej. Consulta de viáticos"
                disabled={creating}
              />
            </div>
            <Button type="submit" disabled={creating} className="gap-2 sm:mb-0">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Crear y abrir
            </Button>
          </form>
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Conversaciones</h2>
        {loading ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando…
          </p>
        ) : items.length === 0 ? (
          <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
            No hay chats en esta KB. Crea uno arriba para empezar.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {items.map((c) => (
              <li key={c.chat_id}>
                <Link
                  href={`/kbs/${kbId}/chats/${c.chat_id}`}
                  className="flex items-center justify-between rounded-lg border px-4 py-3 transition-colors hover:bg-muted/50"
                >
                  <span className="flex items-center gap-2 font-medium">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    {c.title || "Chat sin título"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(c.updated_at).toLocaleString("es")}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function ChatsPageHeader({ kbId }: { kbId: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Chat RAG</h1>
      <p className="text-sm text-muted-foreground">
        Pregunta sobre los documentos de esta base. Usa el selector de KB en la barra superior para cambiar de
        base.
      </p>
      <p className="mt-2 text-xs text-muted-foreground">KB: {kbId}</p>
    </div>
  );
}
