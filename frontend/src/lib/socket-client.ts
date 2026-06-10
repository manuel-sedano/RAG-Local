/**
 * Cliente Socket.IO para namespace /chat (streaming y progreso de ingesta).
 */

import { Manager, type Socket } from "socket.io-client";

import { getApiBaseUrl } from "@/lib/api-client";
import { ensureAccessToken, refreshAccessToken } from "@/lib/auth-session";

let manager: Manager | null = null;
let chatSocket: Socket | null = null;
let refreshOnReject = false;

export function getSocketBaseUrl(): string {
  return getApiBaseUrl();
}

type SocketAuth = { token: string };

function applyAuth(token: string): void {
  if (chatSocket) {
    chatSocket.auth = { token };
  }
}

function resetSocketClient(): void {
  if (chatSocket) {
    chatSocket.removeAllListeners();
    chatSocket.disconnect();
    chatSocket = null;
  }
  if (manager) {
    manager.removeAllListeners();
    manager = null;
  }
  refreshOnReject = false;
}

function isLikelyAuthConnectError(message: string): boolean {
  return (
    message === "Connection rejected by server" ||
    message.includes("rejected") ||
    message === "websocket error" ||
    message.includes("Unauthorized")
  );
}

async function createManager(): Promise<Manager> {
  manager = new Manager(getSocketBaseUrl(), {
    path: "/socket.io",
    transports: ["polling", "websocket"],
    upgrade: true,
    reconnection: true,
    reconnectionAttempts: 8,
    reconnectionDelay: 1000,
    autoConnect: false,
  });
  return manager;
}

function socketOptions(token: string) {
  return {
    auth: { token } satisfies SocketAuth,
    query: { token },
    extraHeaders: { Authorization: `Bearer ${token}` },
  };
}

async function reconnectWithFreshToken(): Promise<boolean> {
  if (refreshOnReject) return false;
  refreshOnReject = true;
  try {
    await refreshAccessToken();
    resetSocketClient();
    await connectChatSocket();
    return true;
  } catch {
    return false;
  } finally {
    refreshOnReject = false;
  }
}

function attachConnectErrorHandler(socket: Socket): void {
  socket.off("connect_error");
  socket.on("connect_error", async (err: Error) => {
    if (isLikelyAuthConnectError(err.message)) {
      const ok = await reconnectWithFreshToken();
      if (ok) return;
    }
    const hint =
      err.message === "xhr poll error" || err.message === "websocket error"
        ? " ¿Arrancaste uvicorn con app.main:asgi_application (p. ej. bash scripts/run-api-dev.sh)?"
        : "";
    console.warn(`Socket.IO connect_error: ${err.message}.${hint}`);
  });
}

/** Conecta al namespace /chat con JWT actualizado. */
export async function connectChatSocket(): Promise<Socket> {
  const token = await ensureAccessToken();

  if (!manager) {
    await createManager();
  }

  if (!chatSocket) {
    chatSocket = manager!.socket("/chat", socketOptions(token));
    attachConnectErrorHandler(chatSocket);
  } else {
    applyAuth(token);
    attachConnectErrorHandler(chatSocket);
  }

  if (!chatSocket.connected) {
    chatSocket.connect();
  }
  return chatSocket;
}

export function disconnectChatSocket(): void {
  resetSocketClient();
}

async function waitForSocketConnect(s: Socket): Promise<void> {
  if (s.connected) return;
  await new Promise<void>((resolve, reject) => {
    const onConnect = () => {
      s.off("connect_error", onError);
      resolve();
    };
    const onError = async (err: Error) => {
      s.off("connect", onConnect);
      if (isLikelyAuthConnectError(err.message)) {
        const ok = await reconnectWithFreshToken();
        if (ok && s.connected) {
          resolve();
          return;
        }
      }
      reject(err);
    };
    s.once("connect", onConnect);
    s.once("connect_error", onError);
  });
}

export async function joinChatRoom(chatId: string): Promise<void> {
  const s = await connectChatSocket();
  await waitForSocketConnect(s);
  const res = await s.emitWithAck("chat:join", { chat_id: chatId });
  if (!res?.ok) {
    throw new Error(res?.error ?? "No se pudo unir a la sala del chat.");
  }
}

export async function joinIngestRoom(documentId: string): Promise<void> {
  const s = await connectChatSocket();
  await waitForSocketConnect(s);
  const res = await s.emitWithAck("ingest:join", { document_id: documentId });
  if (!res?.ok) {
    throw new Error(res?.error ?? "No se pudo unir a la sala de ingesta.");
  }
}
