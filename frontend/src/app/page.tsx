"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, ready, logout } = useAuth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">RAG Local</h1>
      <p className="max-w-md text-center text-muted-foreground">
        Frontend Next.js (App Router) — rama <code className="rounded bg-muted px-1 py-0.5">feat/auth-jwt</code>
      </p>

      {!ready ? (
        <p className="text-sm text-muted-foreground">Cargando sesión…</p>
      ) : user ? (
        <div className="flex flex-col items-center gap-3">
          <p className="text-sm">
            Sesión como <span className="font-medium">{user.email}</span> ({user.role})
          </p>
          <Button type="button" variant="outline" onClick={() => void logout()}>
            Cerrar sesión
          </Button>
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
