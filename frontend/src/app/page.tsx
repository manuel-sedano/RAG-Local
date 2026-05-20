"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { useKnowledgeBases } from "@/lib/kb-context";

export default function Home() {
  const { user, ready, logout } = useAuth();
  const { items, activeKbId, setActiveKbId, loading: kbLoading } = useKnowledgeBases();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">RAG Local</h1>
      <p className="max-w-md text-center text-muted-foreground">
        Frontend Next.js (App Router) — gestión de sesión y bases de conocimiento.
      </p>

      {!ready ? (
        <p className="text-sm text-muted-foreground">Cargando sesión…</p>
      ) : user ? (
        <div className="flex w-full max-w-sm flex-col items-center gap-4">
          <p className="text-center text-sm">
            Sesión como <span className="font-medium">{user.email}</span> ({user.role})
          </p>
          <div className="w-full space-y-1.5">
            <label htmlFor="home-kb-select" className="text-xs font-medium text-muted-foreground">
              Base de conocimiento activa
            </label>
            <select
              id="home-kb-select"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              value={activeKbId ?? ""}
              disabled={kbLoading}
              onChange={(ev) => setActiveKbId(ev.target.value || null)}
            >
              <option value="">— Ninguna —</option>
              {items.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
            {!kbLoading && items.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Aún no hay bases.{" "}
                <Link href="/kbs" className="font-medium text-foreground underline-offset-4 hover:underline">
                  Crear una en «Bases de conocimiento»
                </Link>
                .
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button asChild variant="secondary">
              <Link href="/kbs">Bases de conocimiento</Link>
            </Button>
            {activeKbId ? (
              <>
                <Button asChild>
                  <Link href={`/kbs/${activeKbId}/documents`}>Documentos</Link>
                </Button>
                <Button asChild>
                  <Link href={`/kbs/${activeKbId}/chats`}>Chat</Link>
                </Button>
              </>
            ) : null}
            <Button type="button" variant="outline" onClick={() => void logout()}>
              Cerrar sesión
            </Button>
          </div>
        </div>
      ) : (
        <Button asChild>
          <Link href="/login">Iniciar sesión</Link>
        </Button>
      )}

      <p className="max-w-md text-center text-xs text-muted-foreground">
        El API debe tener CORS con el origen de esta app (p. ej. <code className="rounded bg-muted px-1">http://localhost:3000</code>
        ).
      </p>
    </main>
  );
}
