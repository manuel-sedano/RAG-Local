"use client";

import { ChevronDown, ChevronRight, Download, Loader2, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { DocumentUploadZone } from "@/components/document-upload-zone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatApiError } from "@/lib/api-errors";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  deleteDocument,
  downloadDocumentFile,
  getDocumentStatus,
  listDocuments,
  type DocumentListItemDto,
  type DocumentStatusDto,
} from "@/lib/documents-api";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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

export default function KbDocumentsPage() {
  const params = useParams<{ kbId: string }>();
  const router = useRouter();
  const kbId = params.kbId ?? "";
  const { user, ready } = useAuth();

  const [kbName, setKbName] = React.useState<string | null>(null);
  const [kbError, setKbError] = React.useState<string | null>(null);
  const [items, setItems] = React.useState<DocumentListItemDto[]>([]);
  const [listLoading, setListLoading] = React.useState(true);
  const [autoPoll, setAutoPoll] = React.useState(true);
  const [stagesOpenId, setStagesOpenId] = React.useState<string | null>(null);
  const [stagesById, setStagesById] = React.useState<Record<string, DocumentStatusDto | "loading">>({});

  const validId = UUID_RE.test(kbId);

  const loadList = React.useCallback(async () => {
    if (!validId) return;
    setListLoading(true);
    try {
      const data = await listDocuments(kbId);
      setItems(data.items);
    } catch (e: unknown) {
      toast.error(formatApiError(e, "No se pudo cargar la lista de documentos."));
    } finally {
      setListLoading(false);
    }
  }, [kbId, validId]);

  React.useEffect(() => {
    if (!ready || !user) {
      router.replace("/login");
      return;
    }
    if (!validId) {
      setKbError("Identificador de base de conocimiento no válido.");
      setListLoading(false);
      return;
    }
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
          setKbError(formatApiError(e, "No tienes acceso a esta base o no existe."));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, user, router, kbId, validId]);

  React.useEffect(() => {
    if (!ready || !user || !validId || kbError) return;
    void loadList();
  }, [ready, user, validId, kbError, loadList]);

  const needsStatusPoll = React.useMemo(
    () => items.some((d) => d.status === "UPLOADED" || d.status === "PROCESSING"),
    [items],
  );

  React.useEffect(() => {
    if (!autoPoll || !needsStatusPoll || !validId || kbError) return;
    const id = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      void loadList();
    }, 5000);
    return () => window.clearInterval(id);
  }, [autoPoll, needsStatusPoll, loadList, validId, kbError]);

  async function onDelete(doc: DocumentListItemDto) {
    const ok = window.confirm(`¿Eliminar «${doc.filename_original}»?`);
    if (!ok) return;
    const tid = toast.loading("Eliminando…");
    try {
      await deleteDocument(kbId, doc.id);
      toast.dismiss(tid);
      toast.success("Documento eliminado.");
      await loadList();
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, "No se pudo eliminar."));
    }
  }

  async function onDownload(doc: DocumentListItemDto) {
    const tid = toast.loading("Descargando…");
    try {
      await downloadDocumentFile(kbId, doc.id, doc.filename_original);
      toast.dismiss(tid);
    } catch (e: unknown) {
      toast.dismiss(tid);
      toast.error(formatApiError(e, "No se pudo descargar."));
    }
  }

  async function toggleStages(docId: string) {
    if (stagesOpenId === docId) {
      setStagesOpenId(null);
      return;
    }
    setStagesOpenId(docId);
    if (stagesById[docId] && stagesById[docId] !== "loading") {
      return;
    }
    setStagesById((prev) => ({ ...prev, [docId]: "loading" }));
    try {
      const st = await getDocumentStatus(kbId, docId);
      setStagesById((prev) => ({ ...prev, [docId]: st }));
    } catch (e: unknown) {
      setStagesById((prev) => {
        const next = { ...prev };
        delete next[docId];
        return next;
      });
      setStagesOpenId(null);
      toast.error(formatApiError(e, "No se pudo cargar el estado detallado."));
    }
  }

  if (!ready || !user) {
    return (
      <main className="flex min-h-[100dvh] items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-[100dvh] max-w-4xl flex-col gap-8 p-6 pb-16">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documentos</h1>
          <p className="text-sm text-muted-foreground">
            {kbName ? (
              <>
                Base: <span className="font-medium text-foreground">{kbName}</span>
              </>
            ) : kbError ? (
              <span className="text-destructive">{kbError}</span>
            ) : (
              "Cargando…"
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <Link href="/kbs">Volver a bases</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/">Inicio</Link>
          </Button>
        </div>
      </div>

      {kbError ? null : validId ? (
        <>
          <DocumentUploadZone kbId={kbId} disabled={!!kbError} onUploaded={() => void loadList()} />

          <Card>
            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-lg">Archivos en esta KB</CardTitle>
                <CardDescription>
                  La lista se refresca al subir o borrar. Con documentos en proceso, la actualización automática
                  consulta el servidor cada 5 s.
                </CardDescription>
              </div>
              <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={autoPoll}
                  onChange={(ev) => setAutoPoll(ev.target.checked)}
                  className="rounded border-input"
                />
                Auto-actualizar si hay ingesta en curso
              </label>
            </CardHeader>
            <CardContent>
              {listLoading && items.length === 0 ? (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Cargando documentos…
                </p>
              ) : items.length === 0 ? (
                <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                  Aún no hay documentos. Sube un PDF, DOCX o TXT arriba.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] border-collapse text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-2 font-medium">Nombre</th>
                        <th className="py-2 pr-2 font-medium">Tipo</th>
                        <th className="py-2 pr-2 font-medium">Tamaño</th>
                        <th className="py-2 pr-2 font-medium">Estado</th>
                        <th className="py-2 pr-2 font-medium">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((doc) => {
                        const ex = stagesOpenId === doc.id ? stagesById[doc.id] : undefined;
                        return (
                          <React.Fragment key={doc.id}>
                            <tr className="border-b border-border/60">
                              <td className="max-w-[220px] truncate py-2 pr-2 font-medium" title={doc.filename_original}>
                                {doc.filename_original}
                              </td>
                              <td className="whitespace-nowrap py-2 pr-2 text-muted-foreground">{doc.mime_type}</td>
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
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    className="h-8 gap-1 px-2"
                                    onClick={() => void toggleStages(doc.id)}
                                  >
                                    {stagesOpenId === doc.id ? (
                                      <ChevronDown className="h-3.5 w-3.5" />
                                    ) : (
                                      <ChevronRight className="h-3.5 w-3.5" />
                                    )}
                                    Etapas
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    className="h-8 gap-1 px-2"
                                    onClick={() => void onDownload(doc)}
                                    disabled={doc.status === "QUARANTINED"}
                                    title={doc.status === "QUARANTINED" ? "En cuarentena" : "Descargar"}
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
                            {ex ? (
                              <tr className="border-b border-border/40 bg-muted/30">
                                <td colSpan={5} className="px-2 py-3">
                                  {ex === "loading" ? (
                                    <span className="flex items-center gap-2 text-muted-foreground">
                                      <Loader2 className="h-4 w-4 animate-spin" />
                                      Cargando etapas…
                                    </span>
                                  ) : (
                                    <ul className="grid gap-1 text-xs sm:grid-cols-2">
                                      {Object.entries(ex.stages).map(([k, v]) => (
                                        <li key={k}>
                                          <span className="font-medium">{k}</span>: {v.status}
                                          {v.duration_ms ? ` (${v.duration_ms} ms)` : ""}
                                        </li>
                                      ))}
                                    </ul>
                                  )}
                                  {ex !== "loading" && ex.error ? (
                                    <p className="mt-2 text-destructive">
                                      {ex.error.code}: {ex.error.message ?? "—"}
                                    </p>
                                  ) : null}
                                </td>
                              </tr>
                            ) : null}
                          </React.Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </main>
  );
}
