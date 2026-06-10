# RAG Local — frontend

## Decisiones

- **App Router** (`src/app/`), TypeScript, Tailwind, ESLint (`eslint-config-next`).
- **shadcn/ui** en `src/components/ui/`.
- **Auth (sesión en navegador):** tokens en `localStorage`, cliente Axios en `src/lib/api-client.ts` con reintento tras `401` vía `POST /api/auth/refresh`. Contexto en `src/lib/auth-context.tsx` (`useAuth`).

El `docker-compose` del bootstrap sigue sirviendo el **placeholder nginx**; sustituir por imagen Next en fases de despliegue.

## Variables de entorno

Copia `frontend/.env.example` a `frontend/.env.local` y define la URL del API:

- `NEXT_PUBLIC_API_BASE_URL` — origen del FastAPI (`http://127.0.0.1:8000`), **sin** `/api` al final (las peticiones ya usan `/api/auth/...`). Si pones `.../api` por error, el cliente quita el sufijo para evitar `/api/api/...`.

El backend debe permitir el origen del front en `CORS_ALLOW_ORIGINS` (p. ej. `http://localhost:3000`).

## Layout (shell de la app)

Rutas bajo `/kbs/[kbId]/` usan un **workspace layout**:

- **Cabecera:** selector de KB (`KbSelector`) + gestión de sesión.
- **Sidebar (md+):** pestañas Documentos / Chat y lista contextual (docs o conversaciones).
- **Panel chat (xl, en documentos):** acceso rápido a chats recientes.
- **Estados reutilizables:** `LoadingState`, `EmptyState`, `ErrorState` en `src/components/page-state.tsx`.
- **i18n mínimo:** cadenas en español en `src/lib/i18n/es.ts`.

Prueba automática del layout: desde la raíz del repo, `bash scripts/test-frontend-layout.sh`.

## Documentos (filtros, detalle, visor PDF)

Rutas:

- Lista: `/kbs/{kbId}/documents` — filtros estado/tipo/tags/origen, enlace al detalle.
- Detalle: `/kbs/{kbId}/documents/{docId}?page=N` — metadatos, etapas, reindex, visor PDF.js (auth Bearer) o texto TXT.

Dependencia: `pdfjs-dist`. Progreso de ingesta vía Socket.IO (`ingest:progress`) y polling.

Prueba: `bash scripts/test-frontend-documents.sh` (lint + build).

## Desarrollo

```bash
npm install
npm run dev
```

Abre `http://localhost:3000`. Ruta de login: `/login`. Con sesión y KB activa: `/kbs/{kbId}/documents`.

## Probar login

1. Backend con uvicorn, migraciones aplicadas y usuario de prueba (p. ej. `python -m scripts.seed_dev_user` desde `backend/`).
2. `npm run dev` en esta carpeta.
3. Ir a `/login` con un email válido para `EmailStr` (p. ej. `dev@example.com`).

## Herramientas

- Lint: `npm run lint`
- Build: `npm run build`

## Referencias Next.js

- [Documentación Next.js](https://nextjs.org/docs)
- [Despliegue](https://nextjs.org/docs/app/building-your-application/deploying)
