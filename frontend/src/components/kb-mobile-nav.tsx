"use client";

import { FileText, MessageSquare } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";

import { es } from "@/lib/i18n/es";
import { cn } from "@/lib/utils";

/** Pestañas de sección en móvil (sidebar oculto en pantallas pequeñas). */
export function KbMobileNav() {
  const params = useParams<{ kbId: string }>();
  const pathname = usePathname();
  const kbId = params.kbId ?? "";

  const onDocuments = pathname.includes(`/kbs/${kbId}/documents`);
  const onChats = pathname.includes(`/kbs/${kbId}/chats`);

  return (
    <nav
      className="flex gap-1 border-b bg-muted/30 p-2 md:hidden"
      aria-label="Secciones de la KB"
    >
      <MobileTab
        href={`/kbs/${kbId}/documents`}
        active={onDocuments}
        icon={<FileText className="h-4 w-4" />}
        label={es.nav.documents}
      />
      <MobileTab
        href={`/kbs/${kbId}/chats`}
        active={onChats}
        icon={<MessageSquare className="h-4 w-4" />}
        label={es.nav.chat}
      />
    </nav>
  );
}

function MobileTab({
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
        "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium",
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:bg-background/70",
      )}
      aria-current={active ? "page" : undefined}
    >
      {icon}
      {label}
    </Link>
  );
}
