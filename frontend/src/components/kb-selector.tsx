"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { es } from "@/lib/i18n/es";
import { useKnowledgeBases } from "@/lib/kb-context";

/** Selector de KB activa; al cambiar, actualiza la ruta si estás en /kbs/[id]/… */
export function KbSelector({ id = "kb-selector" }: { id?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const { items, loading, activeKbId, setActiveKbId } = useKnowledgeBases();

  function onChange(nextId: string) {
    const idOrNull = nextId || null;
    setActiveKbId(idOrNull);
    if (!idOrNull) return;

    const kbRoute = pathname.match(/^\/kbs\/([^/]+)(\/.*)?$/);
    if (kbRoute) {
      const rest = kbRoute[2] ?? "";
      if (rest.match(/^\/chats\/[^/]+/)) {
        router.push(`/kbs/${idOrNull}/chats`);
      } else {
        router.push(`/kbs/${idOrNull}${rest || "/documents"}`);
      }
    } else {
      router.push(`/kbs/${idOrNull}/documents`);
    }
  }

  return (
    <KbSelectorField
      id={id}
      loading={loading}
      items={items}
      activeKbId={activeKbId}
      onChange={onChange}
    />
  );
}

function KbSelectorField({
  id,
  loading,
  items,
  activeKbId,
  onChange,
}: {
  id: string;
  loading: boolean;
  items: { id: string; name: string }[];
  activeKbId: string | null;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex min-w-[200px] max-w-xs flex-1 flex-col gap-1 sm:min-w-[240px]">
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {es.nav.kbLabel}
      </label>
      {loading && items.length === 0 ? (
        <div className="flex h-10 items-center gap-2 rounded-md border border-input px-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          {es.states.loading}
        </div>
      ) : items.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          {es.nav.kbEmpty}{" "}
          <Link href="/kbs" className="font-medium text-foreground underline-offset-4 hover:underline">
            {es.nav.kbCreateLink}
          </Link>
        </p>
      ) : (
        <select
          id={id}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          value={activeKbId ?? ""}
          onChange={(ev) => onChange(ev.target.value)}
        >
          <option value="">{es.nav.kbPlaceholder}</option>
          {items.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
