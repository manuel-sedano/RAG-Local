import { api, getApiBaseUrl, postFormData } from "@/lib/api-client";
import { getAccessToken } from "@/lib/auth-tokens";

export type DocumentListItemDto = {
  id: string;
  kb_id: string;
  filename_original: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  page_count: number | null;
  chunk_count: number | null;
  tags?: string[] | Record<string, unknown> | null;
  source?: string | null;
  created_at: string;
};

export type DocumentDetailDto = {
  id: string;
  kb_id: string;
  filename_original: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  page_count: number | null;
  chunk_count: number | null;
  language: string | null;
  source: string | null;
  tags: string[] | Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type DocumentStatusDto = {
  document_id: string;
  status: string;
  stages: Record<string, { status: string; duration_ms: number }>;
  error: { code: string; message: string | null } | null;
};

export type DocumentUploadResponseDto = {
  document_id: string;
  status: string;
  ingestion_job_id: string;
};

export type DocumentReindexResponseDto = {
  document_id: string;
  status: string;
  ingestion_job_id: string;
};

export type DocumentListFilters = {
  cursor?: string;
  limit?: number;
  status?: string;
};

export async function listDocuments(
  kbId: string,
  opts?: DocumentListFilters,
): Promise<{ items: DocumentListItemDto[]; next_cursor: string | null }> {
  const { data } = await api.get<{ items: DocumentListItemDto[]; next_cursor: string | null }>(
    `/api/kbs/${kbId}/documents`,
    { params: { cursor: opts?.cursor, limit: opts?.limit ?? 100, status: opts?.status } },
  );
  return data;
}

export async function getDocument(kbId: string, docId: string): Promise<DocumentDetailDto> {
  const { data } = await api.get<DocumentDetailDto>(`/api/kbs/${kbId}/documents/${docId}`);
  return data;
}

export async function getDocumentStatus(kbId: string, docId: string): Promise<DocumentStatusDto> {
  const { data } = await api.get<DocumentStatusDto>(`/api/kbs/${kbId}/documents/${docId}/status`);
  return data;
}

export async function reindexDocument(
  kbId: string,
  docId: string,
): Promise<DocumentReindexResponseDto> {
  const { data } = await api.post<DocumentReindexResponseDto>(
    `/api/kbs/${kbId}/documents/${docId}/reindex`,
  );
  return data;
}

export async function uploadDocument(
  kbId: string,
  file: File,
  meta: { tags?: string; source?: string; language?: string },
): Promise<DocumentUploadResponseDto> {
  const form = new FormData();
  form.append("file", file);
  if (meta.tags?.trim()) form.append("tags", meta.tags.trim());
  if (meta.source?.trim()) form.append("source", meta.source.trim());
  if (meta.language?.trim()) form.append("language", meta.language.trim());
  const { data } = await postFormData<DocumentUploadResponseDto>(
    `/api/kbs/${kbId}/documents/upload`,
    form,
  );
  return data;
}

export async function deleteDocument(kbId: string, docId: string): Promise<void> {
  await api.delete(`/api/kbs/${kbId}/documents/${docId}`);
}

/** Descarga autenticada del binario (para visor PDF/TXT o guardar en disco). */
export async function fetchDocumentBlob(kbId: string, docId: string): Promise<Blob> {
  const { data } = await api.get<Blob>(`/api/kbs/${kbId}/documents/${docId}/file`, {
    responseType: "blob",
  });
  return data instanceof Blob ? data : new Blob([data]);
}

/** Fetch con Authorization explícito (útil para PDF.js worker). */
export async function fetchDocumentArrayBuffer(kbId: string, docId: string): Promise<ArrayBuffer> {
  const token = getAccessToken();
  const url = `${getApiBaseUrl()}/api/kbs/${kbId}/documents/${docId}/file`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new Error(`No se pudo cargar el archivo (${res.status}).`);
  }
  return res.arrayBuffer();
}

export async function downloadDocumentFile(kbId: string, docId: string, filename: string): Promise<void> {
  const blob = await fetchDocumentBlob(kbId, docId);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "documento";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function documentViewerPath(kbId: string, docId: string, page?: number): string {
  const base = `/kbs/${kbId}/documents/${docId}`;
  if (page != null && page > 0) return `${base}?page=${page}`;
  return base;
}

export function normalizeDocumentTags(tags: DocumentListItemDto["tags"]): string[] {
  if (!tags) return [];
  if (Array.isArray(tags)) return tags.map(String);
  if (typeof tags === "object") return Object.values(tags).map(String);
  return [];
}
