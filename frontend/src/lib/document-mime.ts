/** Etiquetas cortas para MIME en filtros y tablas. */
export const MIME_FILTER_OPTIONS = [
  { value: "", label: "Todos los tipos" },
  { value: "application/pdf", label: "PDF" },
  {
    value: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    label: "DOCX",
  },
  { value: "text/plain", label: "TXT" },
] as const;

export const STATUS_FILTER_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "UPLOADED", label: "UPLOADED" },
  { value: "PROCESSING", label: "PROCESSING" },
  { value: "READY", label: "READY" },
  { value: "FAILED", label: "FAILED" },
  { value: "QUARANTINED", label: "QUARANTINED" },
] as const;

export function mimeShortLabel(mime: string): string {
  const found = MIME_FILTER_OPTIONS.find((o) => o.value === mime);
  if (found && found.value) return found.label;
  if (mime.includes("pdf")) return "PDF";
  if (mime.includes("word")) return "DOCX";
  if (mime.startsWith("text/")) return "TXT";
  return mime.split("/").pop() ?? mime;
}

export function isPdfMime(mime: string): boolean {
  return mime === "application/pdf";
}

export function isTextMime(mime: string): boolean {
  return mime === "text/plain" || mime.startsWith("text/");
}

export function isDocxMime(mime: string): boolean {
  return (
    mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    mime.includes("wordprocessingml")
  );
}
