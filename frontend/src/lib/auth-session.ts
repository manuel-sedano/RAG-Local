/**
 * Refresco de access token (compartido por HTTP y Socket.IO).
 */

import axios from "axios";

import { getApiBaseUrl } from "@/lib/api-client";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/auth-tokens";

const plain = axios.create({
  baseURL: getApiBaseUrl(),
  headers: { "Content-Type": "application/json" },
});

/** Margen antes de exp para refrescar (evita rechazos de Socket.IO). */
const EXPIRY_SKEW_MS = 60_000;

export class AuthSessionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthSessionError";
  }
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(base64);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** `true` si el access token existe y no expira en el margen indicado. */
export function isAccessTokenValid(skewMs: number = EXPIRY_SKEW_MS): boolean {
  const token = getAccessToken();
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  const exp = payload?.exp;
  if (typeof exp !== "number") return true;
  return Date.now() < exp * 1000 - skewMs;
}

/** Devuelve un access token válido; refresca si está expirado o próximo a expirar. */
export async function ensureAccessToken(): Promise<string> {
  const existing = getAccessToken();
  if (existing && isAccessTokenValid()) {
    return existing;
  }
  if (existing) {
    return refreshAccessToken();
  }

  const refresh = getRefreshToken();
  if (!refresh) {
    throw new AuthSessionError("No hay sesión activa. Inicia sesión de nuevo.");
  }
  return refreshAccessToken();
}

export async function refreshAccessToken(): Promise<string> {
  const refresh = getRefreshToken();
  if (!refresh) {
    clearTokens();
    throw new AuthSessionError("No hay sesión activa. Inicia sesión de nuevo.");
  }
  try {
    const { data } = await plain.post<{
      access_token: string;
      refresh_token: string;
    }>("/api/auth/refresh", { refresh_token: refresh });
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    clearTokens();
    throw new AuthSessionError(
      "La sesión expiró. Vuelve a iniciar sesión.",
    );
  }
}
