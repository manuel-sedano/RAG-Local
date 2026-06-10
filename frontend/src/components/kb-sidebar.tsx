"use client";

import { FileText, Loader2, MessageSquare, Plus } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/page-state";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { listDocuments, type DocumentListItemDto } from "@/lib/documents-api";
import { es } from "@/lib/i18n/es";
import { cn } from "@/lib/utils";

type ChatListItem = {
  chat_id: string;
  title: string | null;
  updated_at: string;
};

function statusDotClass(status: string): string {
  switch (status) {
    case "READY":
      return "bg-emerald-500";
    case "FAILED":
    case "QUARANTINED":
      return "bg-destructive";
    case "PROCESSING":
    case "UPLOADED":
      return "bg-amber-500";
    default:
      return "bg-muted-foreground";
  }
}

export function KbSidebar() {
  const params = useParams<{ kbId: string }>();
  const pathname = usePathname();
  const kbId = params.kbId ?? "";

  const onDocuments = pathname.includes(`/kbs/${kbId}/documents`);
  const onChats = pathname.includes(`/kbs/${kbId}/chats`);
  const activeChatId = pathname.match(/\/chats\/([^/]+)/)?.[1] ?? null;

  const [docs, setDocs] = useState<DocumentListItemDto[]>([]);
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [chatsLoading, setChatsLoading] = useState(false);
  const [sidebarError, setSidebarError] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    if (!kbId) return;
    setDocsLoading(true);
    setSidebarError(null);
    try {
      const data = await listDocuments(kbId, { limit: 20 });
      setDocs(data.items);
    } catch (e: unknown) {
      setSidebarError(formatApiError(e, es.states.errorLoadDocuments));
    } finally {
      setDocsLoading(false);
    }
  }, [kbId]);

  const loadChats = useCallback(async () => {
    if (!kbId) return;
    setChatsLoading(true);
    setSidebarError(null);
    try {
      const r = await api.get<{ items: ChatListItem[] }>(`/api/kbs/${kbId}/chats`);
      setChats(r.data.items);
    } catch (e: unknown) {
      setSidebarError(formatApiError(e, es.states.errorLoadChats));
    } finally {
      setChatsLoading(false);
    }
  }, [kbId]);

  /* eslint-disable react-hooks/set-state-in-effect -- carga inicial del sidebar */
  useEffect(() => {
    void loadDocs();
    void loadChats();
  }, [loadDocs, loadChats]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      void loadDocs();
      void loadChats();
    };
    window.addEventListener("focus", onVisible);
    return () => window.removeEventListener("focus", onVisible);
  }, [loadDocs, loadChats]);

  return (
    <aside className="flex h-full min-h-0 flex-col border-r bg-muted/20">
      <nav className="flex shrink-0 gap-1 border-b p-2" aria-label="Secciones de la KB">
        <SidebarNavLink
          href={`/kbs/${kbId}/documents`}
          active={onDocuments}
          icon={<FileText className="h-4 w-4" />}
          label={es.nav.documents}
        />
        <SidebarNavLink
          href={`/kbs/${kbId}/chats`}
          active={onChats}
          icon={<MessageSquare className="h-4 w-4" />}
          label={es.nav.chat}
        />
      </nav>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {onDocuments ? (
          <SidebarDocumentsList docs={docs} loading={docsLoading} kbId={kbId} />
        ) : onChats ? (
          <SidebarChatsList
            chats={chats}
            loading={chatsLoading}
            kbId={kbId}
            activeChatId={activeChatId}
          />
        ) : (
          <p className="p-4 text-xs text-muted-foreground">Selecciona una sección arriba.</p>
        )}
      </div>

      {sidebarError ? (
        <p className="shrink-0 border-t px-3 py-2 text-xs text-destructive" role="alert">
          {sidebarError}
        </p>
      ) : null}
    </aside>
  );
}

function SidebarNavLink({
  href,
  active,
  icon,
  label,
}: {
  href: string;
  active: boolean;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2 text-xs font-medium transition-colors",
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:bg-background/60 hover:text-foreground",
      )}
      aria-current={active ? "page" : undefined}
    >
      {icon}
      <span>{label}</span>
    </Link>
  );
}

function SidebarDocumentsList({
  docs,
  loading,
  kbId,
}: {
  docs: DocumentListItemDto[];
  loading: boolean;
  kbId: string;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between px-3 py-2">
        <span className="text-xs font-medium text-muted-foreground">{es.documents.sidebarTitle}</span>
        <Button asChild variant="ghost" size="sm" className="h-7 px-2 text-xs">
          <Link href={`/kbs/${kbId}/documents`}>Ver todo</Link>
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {loading && docs.length === 0 ? (
          <p className="flex items-center gap-2 px-1 py-4 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            {es.states.loadingDocuments}
          </p>
        ) : docs.length === 0 ? (
          <p className="px-1 py-4 text-xs text-muted-foreground">{es.documents.sidebarEmpty}</p>
        ) : (
          <ul className="space-y-0.5">
            {docs.map((doc) => (
              <li key={doc.id}>
                <div
                  className="flex items-start gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-muted/60"
                  title={doc.filename_original}
                >
                  <span
                    className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", statusDotClass(doc.status))}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1 truncate font-medium">{doc.filename_original}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SidebarChatsList({
  chats,
  loading,
  kbId,
  activeChatId,
}: {
  chats: ChatListItem[];
  loading: boolean;
  kbId: string;
  activeChatId: string | null;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between px-3 py-2">
        <span className="text-xs font-medium text-muted-foreground">{es.chat.sidebarTitle}</span>
        <Button asChild variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
          <Link href={`/kbs/${kbId}/chats`}>
            <Plus className="h-3.5 w-3.5" />
            {es.chat.panelNew}
          </Link>
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        {loading && chats.length === 0 ? (
          <p className="flex items-center gap-2 px-1 py-4 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
            {es.states.loadingChats}
          </p>
        ) : chats.length === 0 ? (
          <EmptyState
            className="border-none bg-transparent py-6"
            title={es.states.emptyChatsTitle}
            description={es.chat.panelEmpty}
            action={
              <Button asChild size="sm" variant="secondary">
                <Link href={`/kbs/${kbId}/chats`}>{es.chat.createAndOpen}</Link>
              </Button>
            }
          />
        ) : (
          <ul className="space-y-0.5">
            {chats.map((c) => {
              const active = activeChatId === c.chat_id;
              return (
                <li key={c.chat_id}>
                  <Link
                    href={`/kbs/${kbId}/chats/${c.chat_id}`}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-2 text-xs transition-colors",
                      active
                        ? "bg-background font-medium text-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                    )}
                    aria-current={active ? "true" : undefined}
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    <span className="min-w-0 flex-1 truncate">
                      {c.title || es.chat.untitled}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
