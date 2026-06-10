"use client";

import Link from "next/link";

import { LoadingState } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { es } from "@/lib/i18n/es";
import { useKnowledgeBases } from "@/lib/kb-context";

export default function Home() {
  const { user, ready, logout } = useAuth();
  const { items, activeKbId, setActiveKbId, loading: kbLoading } = useKnowledgeBases();

  return (
    <main className="flex min-h-[calc(100dvh-3.5rem)] flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">{es.app.name}</h1>
      <p className="max-w-md text-center text-muted-foreground">{es.app.tagline}</p>

      {!ready ? (
        <LoadingState message={es.states.loadingSession} />
      ) : user ? (
        <div className="flex w-full max-w-sm flex-col items-center gap-4">
          <p className="text-center text-sm">
            {es.home.sessionAs}{" "}
            <span className="font-medium">{user.email}</span> ({user.role})
          </p>
          <div className="w-full space-y-1.5">
            <label htmlFor="home-kb-select" className="text-xs font-medium text-muted-foreground">
              {es.home.activeKb}
            </label>
            <select
              id="home-kb-select"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              value={activeKbId ?? ""}
              disabled={kbLoading}
              onChange={(ev) => setActiveKbId(ev.target.value || null)}
            >
              <option value="">{es.home.none}</option>
              {items.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
            {!kbLoading && items.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                {es.home.noKbsHint}{" "}
                <Link href="/kbs" className="font-medium text-foreground underline-offset-4 hover:underline">
                  {es.home.noKbsLink}
                </Link>
                .
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button asChild variant="secondary">
              <Link href="/kbs">{es.nav.manageKbs}</Link>
            </Button>
            {activeKbId ? (
              <>
                <Button asChild>
                  <Link href={`/kbs/${activeKbId}/documents`}>{es.nav.documents}</Link>
                </Button>
                <Button asChild>
                  <Link href={`/kbs/${activeKbId}/chats`}>{es.nav.chat}</Link>
                </Button>
              </>
            ) : null}
            <Button type="button" variant="outline" onClick={() => void logout()}>
              {es.nav.logout}
            </Button>
          </div>
        </div>
      ) : (
        <Button asChild>
          <Link href="/login">{es.nav.login}</Link>
        </Button>
      )}

      <p className="max-w-md text-center text-xs text-muted-foreground">
        {es.home.corsHint}
      </p>
    </main>
  );
}
