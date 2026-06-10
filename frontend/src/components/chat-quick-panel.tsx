"use client";

import { Loader2, MessageSquare, Plus } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { es } from "@/lib/i18n/es";
import { cn } from "@/lib/utils";

type ChatListItem = {
  chat_id: string;
  title: string | null;
  updated_at: string;
};

/** Panel lateral de chats recientes (visible en pantallas xl en la vista de documentos). */
export function ChatQuickPanel() {
  const params = useParams<{ kbId: string }>();
  const pathname = usePathname();
  const kbId = params.kbId ?? "";

  const show = pathname.includes(`/kbs/${kbId}/documents`);
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!kbId || !show) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get<{ items: ChatListItem[] }>(`/api/kbs/${kbId}/chats`);
      setChats(r.data.items.slice(0, 5));
    } catch (e: unknown) {
      setError(formatApiError(e, es.states.errorLoadChats));
    } finally {
      setLoading(false);
    }
  }, [kbId, show]);

  /* eslint-disable react-hooks/set-state-in-effect -- panel lateral: fetch al montar */
  useEffect(() => {
    void load();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (!show) return null;

  return (
    <aside
      className="hidden min-h-0 w-56 shrink-0 flex-col border-l bg-muted/10 xl:flex"
      aria-label={es.chat.panelTitle}
    >
      <div className="flex shrink-0 items-center justify-between border-b px-3 py-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {es.chat.panelTitle}
        </span>
        <Button asChild variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
          <Link href={`/kbs/${kbId}/chats`}>
            <Plus className="h-3.5 w-3.5" />
            {es.chat.panelNew}
          </Link>
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {loading && chats.length === 0 ? (
          <p className="flex items-center gap-2 px-1 py-4 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            {es.states.loadingChats}
          </p>
        ) : error ? (
          <p className="px-1 py-2 text-xs text-destructive">{error}</p>
        ) : chats.length === 0 ? (
          <p className="px-1 py-4 text-xs text-muted-foreground">{es.chat.panelEmpty}</p>
        ) : (
          <ul className="space-y-0.5">
            {chats.map((c) => (
              <li key={c.chat_id}>
                <Link
                  href={`/kbs/${kbId}/chats/${c.chat_id}`}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-2 py-2 text-xs text-muted-foreground",
                    "transition-colors hover:bg-muted/60 hover:text-foreground",
                  )}
                >
                  <MessageSquare className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  <span className="min-w-0 flex-1 truncate">{c.title || es.chat.untitled}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="shrink-0 border-t p-2">
        <Button asChild variant="secondary" size="sm" className="w-full text-xs">
          <Link href={`/kbs/${kbId}/chats`}>{es.nav.chat}</Link>
        </Button>
      </div>
    </aside>
  );
}
