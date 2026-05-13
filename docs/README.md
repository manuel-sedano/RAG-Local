# Documentación (`docs/`)

Los archivos numerados reflejan el **orden de lectura recomendado**. Este `README.md` es el índice (sin prefijo numérico).

---

## Orden recomendado (inicialización y arranque)

1. **`01-deployment.md`** — WSL2, Ubuntu, Docker Desktop, integración, ubicación del repo, `docker compose`, verificación básica.
2. **`02-smoke-test.md`** — Comprobaciones mínimas del stack (Traefik, placeholders, Postgres, Redis, perfiles opcionales).
3. **`03-github-workflow.md`** — Ramas (`develop`, features), commits y PRs.
4. **`04-env-example.md`** — Plantilla mental para `.env` cuando exista backend/servicios que lo lean (el `.env` real no se versiona).

---

## Orden recomendado (contexto del producto, antes de implementar)

5. **`05-architecture.md`** — Vista de conjunto del sistema y entorno local.
6. **`06-technologies.md`** — Stack y componentes por capa.
7. **`07-features-roadmap.md`** — Fases y prioridades de entrega.
8. **`08-todo.md`** — Backlog detallado por feature branch (ejecución).

---

## Cuando implementes API, datos o RAG

9. **`09-api-spec.md`** — Contrato HTTP/WebSocket previsto.
10. **`10-database-schema.md`** — Modelo de datos y migraciones.
11. **`11-rag-flow.md`** — Flujo RAG, citas, ingesta y chat.

---

## Seguridad, operación y negocio

12. **`12-security.md`** — Amenazas, uploads, WAF, rate limits, JWT, etc.
13. **`13-troubleshooting.md`** — Fallos frecuentes (WSL2, Docker, memoria, rendimiento).
14. **`14-comercializacion-mvp-precios.md`** — Referencia comercial / pricing (no bloquea técnica).

---

## Producto y colaboración en GitHub

15. **`15-asistente-respuestas.md`** — Estándares de tono y lenguaje del asistente conversacional (español).
16. **`16-github-issues.md`** — Etiquetas sugeridas, títulos y cuándo abrir issue vs PR.

La **plantilla de Pull Request** aplicada por GitHub está en `.github/pull_request_template.md` (rellenar al crear el PR).

---

## Resumen rápido “solo arrancar”

`01-deployment.md` → `02-smoke-test.md` → (opcional) `03-github-workflow.md` + `04-env-example.md`.
