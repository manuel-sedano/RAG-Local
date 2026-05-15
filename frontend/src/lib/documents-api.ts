import { api, postFormData } from "@/lib/api-client";

export type DocumentListItemDto = {
  id: string;
  kb_id: string;
  filename_original: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  page_count: number | null;
  chunk_count: number | null;
  created_at: string;
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

export async function listDocuments(
  kbId: string,
  opts?: { cursor?: string; limit?: number; status?: string },
): Promise<{ items: DocumentListItemDto[]; next_cursor: string | null }> {
  const { data } = await api.get<{ items: DocumentListItemDto[]; next_cursor: string | null }>(
    `/api/kbs/${kbId}/documents`,
    { params: { cursor: opts?.cursor, limit: opts?.limit ?? 50, status: opts?.status } },
  );
  return data;
}

export async function getDocumentStatus(kbId: string, docId: string): Promise<DocumentStatusDto> {
  const { data } = await api.get<DocumentStatusDto>(`/api/kbs/${kbId}/documents/${docId}/status`);
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

export async function downloadDocumentFile(kbId: string, docId: string, filename: string): Promise<void> {
  const { data } = await api.get<Blob>(`/api/kbs/${kbId}/documents/${docId}/file`, {
    responseType: "blob",
  });
  const blob = data instanceof Blob ? data : new Blob([data]);
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
