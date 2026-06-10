"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/page-state";
import { fetchDocumentBlob } from "@/lib/documents-api";
import { es } from "@/lib/i18n/es";

type Props = {
  kbId: string;
  docId: string;
};

export function TextDocumentViewer({ kbId, docId }: Props) {
  const [text, setText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* eslint-disable react-hooks/set-state-in-effect -- fetch texto al montar */
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const blob = await fetchDocumentBlob(kbId, docId);
        const content = await blob.text();
        if (!cancelled) setText(content);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : es.documents.viewerTextError);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [kbId, docId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  if (loading) {
    return (
      <p className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
        {es.documents.loadingViewer}
      </p>
    );
  }

  if (error) return <ErrorState message={error} />;

  return (
    <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-md border bg-muted/20 p-4 text-sm">
      {text}
    </pre>
  );
}
