"use client";

import { Download, ExternalLink, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { DocumentFilters, type DocumentFilterState } from "@/components/document-filters";
import { DocumentUploadZone } from "@/components/document-upload-zone";
import { EmptyState, ErrorState, LoadingState } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { mimeShortLabel } from "@/lib/document-mime";
import {
  deleteDocument,
  documentViewerPath,
  downloadDocumentFile,
  listDocuments,
  normalizeDocumentTags,
  type DocumentListItemDto,
} from "@/lib/documents-api";
import { useAuth } from "@/lib/auth-context";
import { es } from "@/lib/i18n/es";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const DEFAULT_FILTERS: DocumentFilterState = {
  status: "",
  mimeType: "",
  tagsQuery: "",
  sourceQuery: "",
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case "READY":
      return "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200";
    case "FAILED":
    case "QUARANTINED":
      return "bg-destructive/15 text-destructive";
    case "PROCESSING":
      return "bg-amber-500/15 text-amber-900 dark:text-amber-100";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function applyClientFilters(
  items: DocumentListItemDto[],
  filters: DocumentFilterState,
): DocumentListItemDto[] {
  const tagQ = filters.tagsQuery.trim().toLowerCase();
  const srcQ = filters.sourceQuery.trim().toLowerCase();
  return items.filter((doc) => {
    if (filters.mimeType && doc.mime_type !== filters.mimeType) return false;
    if (tagQ) {
      const tags = normalizeDocumentTags(doc.tags).map((t) => t.toLowerCase());
      if (!tags.some((t) => t.includes(tagQ))) return false;
    }
    if (srcQ) {
      const src = (doc.source ?? "").toLowerCase();
      if (!src.includes(srcQ)) return false;
    }
    return true;
  });
}

export default function KbDocumentsPage() {
  const params = useParams<{ kbId: string }>();
  const router = useRouter();
  const kbId = params.kbId ?? "";
  const { user, ready } = useAuth();

  const invalidKbIdMessage = React.useMemo(() => {
    if (UUID_RE.test(kbId)) return null;
    return es.states.errorInvalidKbId;
  }, [kbId]);

  const [kbName, setKbName] = React.useState<string | null>(null);
  const [kbError, setKbError] = React.useState<string | null>(null);
  const [items, setItems] = React.useState<DocumentListItemDto[]>([]);
  const [listLoading, setListLoading] = React.useState(true);
  const [autoPoll, setAutoPoll] = React.useState(true);
  const [filters, setFilters] = React.useState<DocumentFilterState>(DEFAULT_FILTERS);

  const validId = UUID_RE.test(kbId);

  const loadList = React.useCallback(async () => {
    if (!validId) return;
    setListLoading(true);
    try {
      const data = await listDocuments(kbId, {
        status: filters.status || undefined,
        limit: 100,
      });
      setItems(data.items);
    } catch (e: unknown) {
      toast.error(formatApiError(e, es.states.errorLoadDocuments));
    } finally {
      setListLoading(false);
    }
  }, [kbId, validId, filters.status]);

  React.useEffect(() => {
    if (!ready || !user) {
      router.replace("/login");
      return;
    }
    if (invalidKbIdMessage) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get<{ name: string }>(`/api/kbs/${kbId}`);
        if (!cancelled) {
          setKbName(data.name);
          setKbError(null);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setKbName(null);
          setKbError(formatApiError(e, es.states.errorKbAccess));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, user, router, kbId, invalidKbIdMessage]);

  React.useEffect(() => {
    if (!ready || !user || invalidKbIdMessage || kbError) return;
    void Promise.resolve().then(() => loadList());
  }, [ready, user, invalidKbIdMessage, kbError, loadList]);

  const filteredItems = React.useMemo(
    () => applyClientFilters(items, filters),
    [items, filters],
  );

  const needsStatusPoll = React.useMemo(
    () => items.some((d) => d.status === "UPLOADED" || d.status === "PROCESSING"),
    [items],
  );

  React.useEffect(() => {
    if (!autoPoll || !needsStatusPoll || invalidKbIdMessage || kbError) return;
    const id = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      void loadList();
    }, 5000);
    return () => window.clearInterval(id);
  }, [autoPoll, needsStatusPoll, loadList, invalidKbIdMessage, kbError]);

  async function onDelete(doc: DocumentListItemDto) {
    const ok = window.confirm(es.documents.deleteConfirm.replace("{name}", doc.filename_original));
    if (!ok) return;
    const tid = toast.loading(es.documents.deleting);
    try {
      await deleteDocument(kbId, doc.id);
      toast.dismiss(tid);
      toast.success(es.documents.deletedOk);
      await loadList();
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, es.documents.deleteError));
    }
  }

  async function onDownload(doc: DocumentListItemDto) {
    const tid = toast.loading(es.documents.downloading);
    try {
      await downloadDocumentFile(kbId, doc.id, doc.filename_original);
      toast.dismiss(tid);
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, es.documents.downloadError));
    }
  }

  if (!ready || !user) {
    return <LoadingState fullPage message={es.states.loadingSession} />;
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-4 pb-12 sm:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{es.documents.title}</h1>
        <p className="text-sm text-muted-foreground">
          {invalidKbIdMessage ? (
            <span className="text-destructive">{invalidKbIdMessage}</span>
          ) : kbName ? (
            <>
              {es.documents.kbPrefix}{" "}
              <span className="font-medium text-foreground">{kbName}</span>
            </>
          ) : kbError ? (
            <span className="text-destructive">{kbError}</span>
          ) : (
            es.states.loadingKb
          )}
        </p>
      </header>

      {invalidKbIdMessage ? (
        <ErrorState message={invalidKbIdMessage} />
      ) : kbError ? (
        <ErrorState message={kbError} onRetry={() => window.location.reload()} />
      ) : validId ? (
        <>
          <DocumentUploadZone kbId={kbId} disabled={!!kbError} onUploaded={() => void loadList()} />

          <Card>
            <CardHeader className="flex flex-col gap-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-lg">{es.documents.listTitle}</CardTitle>
                  <CardDescription>{es.documents.listHint}</CardDescription>
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={autoPoll}
                    onChange={(ev) => setAutoPoll(ev.target.checked)}
                    className="rounded border-input"
                  />
                  {es.documents.autoPoll}
                </label>
              </div>
              <DocumentFilters value={filters} onChange={setFilters} />
            </CardHeader>
            <CardContent>
              {listLoading && items.length === 0 ? (
                <LoadingState message={es.states.loadingDocuments} />
              ) : filteredItems.length === 0 ? (
                <EmptyState
                  title={es.states.emptyDocumentsTitle}
                  description={
                    items.length > 0 ? es.documents.noFilterMatch : es.states.emptyDocumentsDesc
                  }
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] border-collapse text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-2 font-medium">{es.documents.colName}</th>
                        <th className="py-2 pr-2 font-medium">{es.documents.colType}</th>
                        <th className="py-2 pr-2 font-medium">{es.documents.colTags}</th>
                        <th className="py-2 pr-2 font-medium">{es.documents.colSize}</th>
                        <th className="py-2 pr-2 font-medium">{es.documents.colStatus}</th>
                        <th className="py-2 pr-2 font-medium">{es.documents.colActions}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredItems.map((doc) => (
                        <tr key={doc.id} className="border-b border-border/60">
                          <td className="max-w-[200px] py-2 pr-2">
                            <Link
                              href={documentViewerPath(kbId, doc.id)}
                              className="inline-flex items-center gap-1 font-medium hover:underline"
                              title={doc.filename_original}
                            >
                              <span className="truncate">{doc.filename_original}</span>
                              <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-60" />
                            </Link>
                          </td>
                          <td className="whitespace-nowrap py-2 pr-2 text-muted-foreground">
                            {mimeShortLabel(doc.mime_type)}
                          </td>
                          <td className="max-w-[120px] truncate py-2 pr-2 text-xs text-muted-foreground">
                            {normalizeDocumentTags(doc.tags).join(", ") || "—"}
                          </td>
                          <td className="whitespace-nowrap py-2 pr-2">{formatBytes(doc.size_bytes)}</td>
                          <td className="py-2 pr-2">
                            <span
                              className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusBadgeClass(doc.status)}`}
                            >
                              {doc.status}
                            </span>
                          </td>
                          <td className="py-2 pr-2">
                            <div className="flex flex-wrap gap-1">
                              <Button asChild size="sm" variant="ghost" className="h-8 px-2">
                                <Link href={documentViewerPath(kbId, doc.id)}>{es.documents.view}</Link>
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="h-8 gap-1 px-2"
                                onClick={() => void onDownload(doc)}
                                disabled={doc.status === "QUARANTINED"}
                                title={
                                  doc.status === "QUARANTINED"
                                    ? es.documents.quarantined
                                    : es.documents.download
                                }
                              >
                                <Download className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="destructive"
                                className="h-8 gap-1 px-2"
                                onClick={() => void onDelete(doc)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
