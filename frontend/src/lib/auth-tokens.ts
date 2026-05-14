/** Persistencia mínima de sesión (navegador). Los tokens viven en `localStorage`. */

const ACCESS = "rag_local_access_token";
const REFRESH = "rag_local_refresh_token";
export const AUTH_USER_STORAGE_KEY = "rag_local_user";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH);
}

export function setTokens(access: string, refresh: string): void {
  window.localStorage.setItem(ACCESS, access);
  window.localStorage.setItem(REFRESH, refresh);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS);
  window.localStorage.removeItem(REFRESH);
  window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent("rag:session-reset"));
}
