"use client";

import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { ChatQuickPanel } from "@/components/chat-quick-panel";
import { KbMobileNav } from "@/components/kb-mobile-nav";
import { KbSidebar } from "@/components/kb-sidebar";
import { ErrorState } from "@/components/page-state";
import { es } from "@/lib/i18n/es";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function KbWorkspaceLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ kbId: string }>();
  const kbId = params.kbId ?? "";
  const validId = UUID_RE.test(kbId);

  if (!validId) {
    return (
      <div className="mx-auto max-w-lg p-6">
        <ErrorState message={es.states.errorInvalidKbId} />
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100dvh-3.5rem)] w-full flex-col">
      <KbMobileNav />
      <div className="flex min-h-0 flex-1">
        <div className="hidden w-56 shrink-0 md:block lg:w-60">
          <KbSidebar />
        </div>
        <div className="flex min-w-0 flex-1">
          <main className="min-w-0 flex-1 overflow-x-hidden">{children}</main>
          <ChatQuickPanel />
        </div>
      </div>
    </div>
  );
}
