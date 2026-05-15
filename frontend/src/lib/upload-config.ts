/** Límites de upload solo UX (el backend valida de verdad). */

const DEFAULT_MAX_MB = 50;
const DEFAULT_MIMES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
] as const;

function parseMb(): number {
  const raw = process.env.NEXT_PUBLIC_MAX_UPLOAD_MB?.trim();
  if (!raw) return DEFAULT_MAX_MB;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_MAX_MB;
}

function parseMimes(): string[] {
  const raw = process.env.NEXT_PUBLIC_ALLOWED_MIME_TYPES?.trim();
  if (!raw) return [...DEFAULT_MIMES];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export const clientMaxUploadBytes = () => parseMb() * 1024 * 1024;

export const clientAllowedMimeTypes = () => parseMimes();

export const clientAcceptFileTypes = ".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain";
