"use client";

import * as React from "react";

import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export const ACTIVE_KB_STORAGE_KEY = "rag-local:active-kb-id";

export type KnowledgeBaseDto = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

type Ctx = {
  items: KnowledgeBaseDto[];
  loading: boolean;
  reload: () => Promise<void>;
  activeKbId: string | null;
  setActiveKbId: (id: string | null) => void;
  activeKb: KnowledgeBaseDto | null;
};

const KnowledgeBasesContext = React.createContext<Ctx | null>(null);

function readStoredKbId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_KB_STORAGE_KEY);
}

export function KnowledgeBasesProvider({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();
  const [items, setItems] = React.useState<KnowledgeBaseDto[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [activeKbId, setActiveKbIdState] = React.useState<string | null>(null);

  const setActiveKbId = React.useCallback((id: string | null) => {
    setActiveKbIdState(id);
    if (typeof window === "undefined") return;
    if (id) window.localStorage.setItem(ACTIVE_KB_STORAGE_KEY, id);
    else window.localStorage.removeItem(ACTIVE_KB_STORAGE_KEY);
  }, []);

  const reload = React.useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const { data } = await api.get<{ items: KnowledgeBaseDto[] }>("/api/kbs");
      setItems(data.items);
      const ids = new Set(data.items.map((k) => k.id));
      setActiveKbIdState((current) => {
        let next: string | null = null;
        if (current && ids.has(current)) {
          next = current;
        } else {
          const stored = readStoredKbId();
          if (stored && ids.has(stored)) next = stored;
          else next = null;
        }
        if (typeof window !== "undefined") {
          if (next) window.localStorage.setItem(ACTIVE_KB_STORAGE_KEY, next);
          else window.localStorage.removeItem(ACTIVE_KB_STORAGE_KEY);
        }
        return next;
      });
    } finally {
      setLoading(false);
    }
  }, [user]);

  /* eslint-disable react-hooks/set-state-in-effect -- estado ligado a sesión (login/logout/carga KB) */
  React.useEffect(() => {
    if (!ready) return;
    if (!user) {
      setItems([]);
      setActiveKbIdState(null);
      if (typeof window !== "undefined") window.localStorage.removeItem(ACTIVE_KB_STORAGE_KEY);
      return;
    }
    setActiveKbIdState(readStoredKbId());
  }, [user, ready]);

  React.useEffect(() => {
    if (!ready || !user) return;
    void reload();
  }, [user, ready, reload]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const activeKb = React.useMemo(
    () => items.find((k) => k.id === activeKbId) ?? null,
    [items, activeKbId],
  );

  const value = React.useMemo<Ctx>(
    () => ({
      items,
      loading,
      reload,
      activeKbId,
      setActiveKbId,
      activeKb,
    }),
    [items, loading, reload, activeKbId, setActiveKbId, activeKb],
  );

  return <KnowledgeBasesContext.Provider value={value}>{children}</KnowledgeBasesContext.Provider>;
}

export function useKnowledgeBases(): Ctx {
  const ctx = React.useContext(KnowledgeBasesContext);
  if (!ctx) {
    throw new Error("useKnowledgeBases debe usarse dentro de KnowledgeBasesProvider");
  }
  return ctx;
}
