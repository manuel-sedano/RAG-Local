"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { KbSelector } from "@/components/kb-selector";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { useKnowledgeBases } from "@/lib/kb-context";

export function AppHeader() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { activeKbId } = useKnowledgeBases();

  if (!user) return null;

  const onKbRoute = pathname.match(/^\/kbs\/([^/]+)/);
  const routeKbId = onKbRoute?.[1] ?? null;
  const kbId = activeKbId ?? routeKbId;

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex max-w-5xl flex-wrap items-end gap-3 px-4 py-3 sm:gap-4">
        <Link href="/" className="shrink-0 text-sm font-semibold tracking-tight hover:opacity-80">
          RAG Local
        </Link>
        <KbSelector id="app-header-kb" />
        <nav className="flex flex-1 flex-wrap items-center justify-end gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/kbs">Gestionar KBs</Link>
          </Button>
          {kbId ? (
            <>
              <Button asChild variant="secondary" size="sm">
                <Link href={`/kbs/${kbId}/documents`}>Documentos</Link>
              </Button>
              <Button asChild variant="secondary" size="sm">
                <Link href={`/kbs/${kbId}/chats`}>Chat</Link>
              </Button>
            </>
          ) : null}
          <Button type="button" variant="outline" size="sm" onClick={() => void logout()}>
            Salir
          </Button>
        </nav>
      </div>
    </header>
  );
}
