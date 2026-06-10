"use client";

import { Suspense } from "react";
import { ArrowLeft, Download, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { DocumentIngestionStages } from "@/components/document-ingestion-stages";
import { PdfViewer } from "@/components/pdf-viewer";
import { ErrorState, LoadingState } from "@/components/page-state";
import { TextDocumentViewer } from "@/components/text-document-viewer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useIngestProgress } from "@/hooks/use-ingest-progress";
import { formatApiError } from "@/lib/api-errors";
import { isDocxMime, isPdfMime, isTextMime, mimeShortLabel } from "@/lib/document-mime";
import {
  downloadDocumentFile,
  fetchDocumentArrayBuffer,
  getDocument,
  getDocumentStatus,
  normalizeDocumentTags,
  reindexDocument,
  type DocumentDetailDto,
  type DocumentStatusDto,
} from "@/lib/documents-api";
import { useAuth } from "@/lib/auth-context";
import { es } from "@/lib/i18n/es";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentDetailPage() {
  return (
    <Suspense fallback={<LoadingState fullPage message={es.documents.loadingDetail} />}>
      <DocumentDetailContent />
    </Suspense>
  );
}

function DocumentDetailContent() {
  const params = useParams<{ kbId: string; docId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const kbId = params.kbId ?? "";
  const docId = params.docId ?? "";
  const { user, ready } = useAuth();

  const initialPage = Math.max(1, Number(searchParams.get("page") || "1") || 1);

  const [doc, setDoc] = useState<DocumentDetailDto | null>(null);
  const [stages, setStages] = useState<DocumentStatusDto | "loading" | null>(null);
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [page, setPage] = useState(initialPage);
  const [reindexing, setReindexing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const ingestProgress = useIngestProgress(
    doc?.status === "UPLOADED" || doc?.status === "PROCESSING" ? docId : null,
  );

  const loadDoc = useCallback(async () => {
    try {
      const d = await getDocument(kbId, docId);
      setDoc(d);
      setLoadError(null);
      return d;
    } catch (e: unknown) {
      setLoadError(formatApiError(e, es.documents.errorLoadDetail));
      return null;
    }
  }, [kbId, docId]);

  const loadStages = useCallback(async () => {
    setStages("loading");
    try {
      const st = await getDocumentStatus(kbId, docId);
      setStages(st);
      return st;
    } catch (e: unknown) {
      setStages(null);
      toast.error(formatApiError(e, es.documents.errorLoadStages));
      return null;
    }
  }, [kbId, docId]);

  /* eslint-disable react-hooks/set-state-in-effect -- carga inicial detalle */
  useEffect(() => {
    if (!ready || !user) {
      router.replace("/login");
      return;
    }
    void loadDoc();
    void loadStages();
  }, [ready, user, router, loadDoc, loadStages]);
  /* eslint-enable react-hooks/set-state-in-effect */

  /* eslint-disable react-hooks/set-state-in-effect -- sincronizar ?page= de la URL */
  useEffect(() => {
    setPage(initialPage);
  }, [initialPage]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const needsPoll = doc?.status === "UPLOADED" || doc?.status === "PROCESSING";

  useEffect(() => {
    if (!needsPoll) return;
    const id = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      void (async () => {
        const d = await loadDoc();
        await loadStages();
        if (d?.status === "READY" || d?.status === "FAILED" || d?.status === "QUARANTINED") {
          window.clearInterval(id);
        }
      })();
    }, 5000);
    return () => window.clearInterval(id);
  }, [needsPoll, loadDoc, loadStages]);

  /* eslint-disable react-hooks/set-state-in-effect -- cargar PDF autenticado al abrir detalle */
  useEffect(() => {
    if (!doc || !isPdfMime(doc.mime_type) || doc.status === "QUARANTINED") {
      setPdfData(null);
      return;
    }
    let cancelled = false;
    setPdfLoading(true);
    void (async () => {
      try {
        const buf = await fetchDocumentArrayBuffer(kbId, docId);
        if (!cancelled) setPdfData(buf);
      } catch (e) {
        if (!cancelled) toast.error(formatApiError(e, es.documents.viewerPdfError));
      } finally {
        if (!cancelled) setPdfLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [doc, kbId, docId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  function onPageChange(next: number) {
    setPage(next);
    const url = `/kbs/${kbId}/documents/${docId}?page=${next}`;
    router.replace(url, { scroll: false });
  }

  async function onReindex() {
    if (!doc) return;
    setReindexing(true);
    const tid = toast.loading(es.documents.reindexing);
    try {
      await reindexDocument(kbId, docId);
      toast.dismiss(tid);
      toast.success(es.documents.reindexOk);
      await loadDoc();
      await loadStages();
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, es.documents.reindexError));
    } finally {
      setReindexing(false);
    }
  }

  async function onDownload() {
    if (!doc) return;
    const tid = toast.loading(es.documents.downloading);
    try {
      await downloadDocumentFile(kbId, docId, doc.filename_original);
      toast.dismiss(tid);
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, es.documents.downloadError));
    }
  }

  if (!ready || !user) {
    return <LoadingState fullPage message={es.states.loadingSession} />;
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <ErrorState message={loadError} />
        <Button asChild variant="link" className="mt-4">
          <Link href={`/kbs/${kbId}/documents`}>{es.documents.backToList}</Link>
        </Button>
      </div>
    );
  }

  if (!doc) {
    return <LoadingState fullPage message={es.documents.loadingDetail} />;
  }

  const tags = normalizeDocumentTags(doc.tags);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-4 pb-12 sm:p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <Button asChild variant="ghost" size="sm" className="-ml-2 h-8 gap-1 px-2">
            <Link href={`/kbs/${kbId}/documents`}>
              <ArrowLeft className="h-4 w-4" />
              {es.documents.backToList}
            </Link>
          </Button>
          <h1 className="text-xl font-semibold tracking-tight">{doc.filename_original}</h1>
          <p className="text-sm text-muted-foreground">
            {mimeShortLabel(doc.mime_type)} · {formatBytes(doc.size_bytes)} · {doc.status}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1"
            onClick={() => void onDownload()}
            disabled={doc.status === "QUARANTINED"}
          >
            <Download className="h-4 w-4" />
            {es.documents.download}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="gap-1"
            onClick={() => void onReindex()}
            disabled={reindexing || doc.status === "QUARANTINED"}
          >
            {reindexing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {es.documents.reindex}
          </Button>
        </div>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{es.documents.metadataTitle}</CardTitle>
          <CardDescription>{es.documents.metadataDesc}</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <MetaRow label={es.documents.metaLanguage} value={doc.language ?? "—"} />
            <MetaRow label={es.documents.metaSource} value={doc.source ?? "—"} />
            <MetaRow label={es.documents.metaPages} value={doc.page_count?.toString() ?? "—"} />
            <MetaRow label={es.documents.metaChunks} value={doc.chunk_count?.toString() ?? "—"} />
            <MetaRow label={es.documents.metaTags} value={tags.length ? tags.join(", ") : "—"} />
            <MetaRow label={es.documents.metaCreated} value={new Date(doc.created_at).toLocaleString("es")} />
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{es.documents.stagesTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentIngestionStages status={stages} ingestProgress={ingestProgress} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{es.documents.viewerTitle}</CardTitle>
          <CardDescription>
            {isPdfMime(doc.mime_type)
              ? es.documents.viewerPdfHint
              : isTextMime(doc.mime_type)
                ? es.documents.viewerTextHint
                : es.documents.viewerDocxHint}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {doc.status === "QUARANTINED" ? (
            <p className="text-sm text-destructive">{es.documents.quarantinedViewer}</p>
          ) : isPdfMime(doc.mime_type) ? (
            pdfLoading || !pdfData ? (
              <LoadingState message={es.documents.loadingViewer} />
            ) : (
              <PdfViewer data={pdfData} page={page} onPageChange={onPageChange} />
            )
          ) : isTextMime(doc.mime_type) ? (
            <TextDocumentViewer kbId={kbId} docId={docId} />
          ) : isDocxMime(doc.mime_type) ? (
            <p className="text-sm text-muted-foreground">{es.documents.viewerDocxHint}</p>
          ) : (
            <p className="text-sm text-muted-foreground">{es.documents.viewerUnsupported}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="w-28 shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words font-medium">{value}</dd>
    </div>
  );
}
