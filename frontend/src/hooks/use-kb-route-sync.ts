"use client";

import { useParams, usePathname } from "next/navigation";
import { useEffect } from "react";

import { useKnowledgeBases } from "@/lib/kb-context";

/** Sincroniza KB activa con el `kbId` de la URL en rutas /kbs/[kbId]/… */
export function useKbRouteSync() {
  const pathname = usePathname();
  const params = useParams<{ kbId?: string }>();
  const { setActiveKbId, activeKbId } = useKnowledgeBases();

  useEffect(() => {
    const fromParams = params.kbId;
    const fromPath = pathname.match(/^\/kbs\/([^/]+)/)?.[1];
    const kbId = fromParams ?? fromPath;
    if (kbId && kbId !== activeKbId) {
      setActiveKbId(kbId);
    }
  }, [pathname, params.kbId, activeKbId, setActiveKbId]);
}
