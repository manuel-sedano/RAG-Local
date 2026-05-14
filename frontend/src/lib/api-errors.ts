import axios from "axios";

/** Extrae un mensaje legible de respuestas FastAPI / Axios. */
export function formatApiError(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error)) {
    return fallback;
  }
  const status = error.response?.status;
  if (status === 404) {
    return "No se encontró el recurso en el servidor. Comprueba NEXT_PUBLIC_API_BASE_URL (origen del API, sin /api al final; p. ej. http://127.0.0.1:8000).";
  }
  const detail = error.response?.data as { detail?: unknown } | undefined;
  const d = detail?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && "message" in d && typeof (d as { message: string }).message === "string") {
    return (d as { message: string }).message;
  }
  if (Array.isArray(d)) {
    const parts = d.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : ""));
    const joined = parts.filter(Boolean).join(" ");
    if (joined) return joined;
  }
  return fallback;
}
