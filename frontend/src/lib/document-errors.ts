import { es } from "@/lib/i18n/es";

/** Mensaje legible para códigos de error de ingesta del backend. */
export function formatIngestError(code: string, message: string | null): string {
  const msg = (message ?? "").trim();
  if (msg === "antivirus_unavailable") {
    return es.documents.errors.antivirusUnavailable;
  }
  if (msg === "parse_fail" || msg.startsWith("parse_")) {
    return es.documents.errors.parseFailed.replace("{detail}", msg);
  }
  if (code === "malware_detected") {
    return es.documents.errors.malwareDetected;
  }
  if (msg) {
    return `${code}: ${msg}`;
  }
  return code;
}
