"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { KbSelector } from "@/components/kb-selector";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { es } from "@/lib/i18n/es";

export function AppHeader() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  if (!user) return null;

  const inKbWorkspace = /^\/kbs\/[^/]+(\/|$)/.test(pathname);

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-end gap-3 px-4 py-3 sm:gap-4">
        <Link href="/" className="shrink-0 text-sm font-semibold tracking-tight hover:opacity-80">
          {es.app.name}
        </Link>
        <KbSelector id="app-header-kb" />
        <nav className="flex flex-1 flex-wrap items-center justify-end gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/kbs">{es.nav.manageKbs}</Link>
          </Button>
          {!inKbWorkspace ? (
            <>
              <Button asChild variant="secondary" size="sm">
                <Link href="/">{es.nav.home}</Link>
              </Button>
            </>
          ) : null}
          <Button type="button" variant="outline" size="sm" onClick={() => void logout()}>
            {es.nav.logout}
          </Button>
        </nav>
      </div>
    </header>
  );
}
