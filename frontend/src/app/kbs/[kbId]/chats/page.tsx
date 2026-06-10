"use client";

import { Loader2, Plus } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { EmptyState, LoadingState } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { es } from "@/lib/i18n/es";
import { useKnowledgeBases } from "@/lib/kb-context";

export default function KbChatsPage() {
  const params = useParams<{ kbId: string }>();
  const kbId = params.kbId ?? "";
  const router = useRouter();
  const { user, ready } = useAuth();
  const { activeKb } = useKnowledgeBases();

  const [loading, setLoading] = useState(true);
  const [hasChats, setHasChats] = useState(false);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  const checkChats = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get<{ items: unknown[] }>(`/api/kbs/${kbId}/chats`);
      setHasChats(r.data.items.length > 0);
    } catch (e: unknown) {
      toast.error(formatApiError(e, es.states.errorLoadChats));
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  /* eslint-disable react-hooks/set-state-in-effect -- comprobar si hay chats al entrar */
  useEffect(() => {
    if (user && kbId) void checkChats();
  }, [user, kbId, checkChats]);
  /* eslint-enable react-hooks/set-state-in-effect */

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
    return <LoadingState fullPage message={es.states.loadingSession} />;
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-4 pb-12 sm:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{es.chat.title}</h1>
        <p className="text-sm text-muted-foreground">
          {activeKb ? (
            <>
              {es.documents.kbPrefix}{" "}
              <span className="font-medium text-foreground">{activeKb.name}</span>
            </>
          ) : (
            es.chat.subtitle
          )}
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{es.chat.newChat}</CardTitle>
          <CardDescription>{es.chat.newChatDesc}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={createChat}>
            <div className="grid flex-1 gap-2">
              <Label htmlFor="chat-title">{es.chat.titleLabel}</Label>
              <Input
                id="chat-title"
                value={title}
                onChange={(ev) => setTitle(ev.target.value)}
                placeholder={es.chat.titlePlaceholder}
                disabled={creating}
              />
            </div>
            <Button type="submit" disabled={creating} className="gap-2 sm:mb-0">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {es.chat.createAndOpen}
            </Button>
          </form>
        </CardContent>
      </Card>

      {loading ? (
        <LoadingState message={es.states.loadingChats} />
      ) : !hasChats ? (
        <EmptyState
          title={es.states.emptyChatsTitle}
          description={es.states.emptyChatsDesc}
        />
      ) : (
        <p className="text-sm text-muted-foreground">
          Elige una conversación en la barra lateral o crea un chat nuevo arriba.
        </p>
      )}
    </div>
  );
}
