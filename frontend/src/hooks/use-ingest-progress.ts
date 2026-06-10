"use client";

import { useEffect, useState } from "react";

import { connectChatSocket, joinIngestRoom } from "@/lib/socket-client";

export type IngestProgress = {
  stage: string;
  percent: number;
};

/** Escucha `ingest:progress` vía Socket.IO para un documento. */
export function useIngestProgress(documentId: string | null): IngestProgress | null {
  const [progress, setProgress] = useState<IngestProgress | null>(null);

  /* eslint-disable react-hooks/set-state-in-effect -- progreso socket por documento */
  useEffect(() => {
    if (!documentId) {
      setProgress(null);
      return;
    }

    let active = true;
    const socketRef = { current: null as Awaited<ReturnType<typeof connectChatSocket>> | null };

    const onProgress = (payload: {
      document_id: string;
      stage: string;
      percent: number;
    }) => {
      if (!active || payload.document_id !== documentId) return;
      setProgress({ stage: payload.stage, percent: payload.percent });
    };

    void (async () => {
      try {
        const s = await connectChatSocket();
        socketRef.current = s;
        if (!active) return;
        s.on("ingest:progress", onProgress);
        await joinIngestRoom(documentId);
      } catch {
        /* socket opcional; la lista sigue con polling */
      }
    })();

    return () => {
      active = false;
      const s = socketRef.current;
      if (s) s.off("ingest:progress", onProgress);
    };
  }, [documentId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  return progress;
}
