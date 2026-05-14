/**
 * Cliente HTTP hacia el backend FastAPI con:
 * - Bearer automático desde `localStorage`
 * - En 401: intenta `POST /api/auth/refresh` una vez y reintenta la petición original
 */

import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/auth-tokens";

function redirectToLoginIfNeeded(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.startsWith("/login")) return;
  window.location.replace("/login?expired=1");
}

/**
 * Origen del backend (sin `/api` final). Las rutas del cliente incluyen ya `/api/...`.
 * Si `NEXT_PUBLIC_API_BASE_URL` termina en `/api`, se quita para evitar `/api/api/...`.
 */
export function getApiBaseUrl(): string {
  let base = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").trim();
  base = base.replace(/\/+$/, "");
  base = base.replace(/\/api\/?$/i, "");
  return base;
}

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: { "Content-Type": "application/json" },
});

/** Cliente sin interceptores (evita bucles al refrescar). */
const plain = axios.create({
  baseURL: getApiBaseUrl(),
  headers: { "Content-Type": "application/json" },
});

type RetryConfig = InternalAxiosRequestConfig & { _authRetry?: boolean };

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    if (!original || original._authRetry) {
      return Promise.reject(error);
    }
    if (error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const url = original.url ?? "";
    if (url.includes("/api/auth/login")) {
      return Promise.reject(error);
    }
    if (url.includes("/api/auth/refresh")) {
      clearTokens();
      redirectToLoginIfNeeded();
      return Promise.reject(error);
    }

    const refresh = getRefreshToken();
    if (!refresh) {
      clearTokens();
      redirectToLoginIfNeeded();
      return Promise.reject(error);
    }

    original._authRetry = true;
    try {
      const { data } = await plain.post<{
        access_token: string;
        refresh_token: string;
      }>("/api/auth/refresh", { refresh_token: refresh });
      setTokens(data.access_token, data.refresh_token);
      original.headers.Authorization = `Bearer ${data.access_token}`;
      return api(original);
    } catch {
      clearTokens();
      redirectToLoginIfNeeded();
      return Promise.reject(error);
    }
  },
);
