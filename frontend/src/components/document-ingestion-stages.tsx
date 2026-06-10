"use client";

import { Loader2 } from "lucide-react";

import { LoadingState } from "@/components/page-state";
import type { DocumentStatusDto } from "@/lib/documents-api";
import { formatIngestError } from "@/lib/document-errors";
import { es } from "@/lib/i18n/es";

type Props = {
  status: DocumentStatusDto | "loading" | null;
  ingestProgress?: { stage: string; percent: number } | null;
};

export function DocumentIngestionStages({ status, ingestProgress }: Props) {
  if (status === "loading" || status === null) {
    return <LoadingState message={es.documents.loadingStages} />;
  }

  return (
    <div className="space-y-3">
      {ingestProgress ? (
        <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
          <div className="mb-1 flex justify-between text-xs text-muted-foreground">
            <span>
              {es.documents.ingestLive}: <strong>{ingestProgress.stage}</strong>
            </span>
            <span>{ingestProgress.percent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${Math.min(100, ingestProgress.percent)}%` }}
            />
          </div>
        </div>
      ) : null}
      <ul className="grid gap-1 text-sm sm:grid-cols-2">
        {Object.entries(status.stages).map(([k, v]) => (
          <li key={k} className="flex items-center gap-2 rounded border px-2 py-1.5">
            <StageDot stageStatus={v.status} />
            <span>
              <span className="font-medium">{k}</span>: {v.status}
              {v.duration_ms ? ` (${v.duration_ms} ms)` : ""}
            </span>
          </li>
        ))}
      </ul>
      {status.error ? (
        <p className="text-sm text-destructive">
          {formatIngestError(status.error.code, status.error.message)}
        </p>
      ) : null}
      {status.status === "PROCESSING" || status.status === "UPLOADED" ? (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
          {es.documents.ingestPolling}
        </p>
      ) : null}
    </div>
  );
}

function StageDot({ stageStatus }: { stageStatus: string }) {
  const s = stageStatus.toLowerCase();
  const cls =
    s === "done" || s === "ok" || s === "skipped"
      ? "bg-emerald-500"
      : s === "failed" || s === "error"
        ? "bg-destructive"
        : s === "running" || s === "active" || s === "processing"
          ? "bg-amber-500"
          : "bg-muted-foreground";
  return <span className={`h-2 w-2 shrink-0 rounded-full ${cls}`} aria-hidden />;
}
