# Flujo de trabajo en GitHub (branches, commits, PRs, releases)

**Alcance:** flujo de ramas, revisiones, trazabilidad y releases para el desarrollo de la plataforma RAG local.

---

## Objetivos del workflow

- Mantener el repositorio siempre en estado “mergeable”.
- Ramas de larga duración y PRs muy grandes incrementan conflicto y regresiones.
- Estandarizar commits y PRs para facilitar revisión.
- Automatizar calidad (lint, tests, seguridad) desde el inicio.

---

## Estrategia de ramas (branch strategy)

Modelo recomendado: **trunk-based con feature branches cortas**.

- `main`:
  - siempre estable
  - protegido (requiere PR + checks)
- `dev` (opcional):
  - integración si el equipo prefiere un “staging” local
  - si se usa, releases se cortan desde `main`

Ramas por feature:

- `feat/auth-jwt`
- `feat/kb-crud`
- `feat/uploads-ingestion`
- `feat/rag-retrieval`
- `feat/chat-streaming`
- `feat/security-waf`
- `feat/observability`
- `chore/docker-compose`
- `fix/<bug>`
- `docs/<topic>`

---

## Convención de commits

Recomendación: **Conventional Commits**.

Formato:

```text
<type>(<scope>): <subject>

<body opcional>

<footer opcional>
```

Tipos sugeridos:

- `feat`: nueva funcionalidad
- `fix`: corrección de bug
- `docs`: documentación
- `refactor`: refactor sin cambio funcional
- `test`: agregar/ajustar pruebas
- `chore`: tareas de mantenimiento (deps, tooling)
- `perf`: mejoras de performance
- `build`: cambios de build/CI

Scopes sugeridos:

- `backend`, `frontend`, `docker`, `rag`, `security`, `docs`, `infra`

Ejemplos:

- `feat(auth): add JWT access/refresh flow`
- `feat(rag): implement hybrid retrieval with reranking`
- `fix(uploads): block invalid mime types and oversized files`
- `docs(architecture): add RAG pipeline and storage flows`

---

## Flujo de Pull Requests (PR flow)

### Reglas recomendadas para PRs

- Tamaño:
  - ideal: 200–600 líneas netas
  - máximo recomendado: < 1200 líneas (si es posible)
- PR debe incluir:
  - objetivo
  - cambios principales
  - test plan
  - riesgos / rollback (si aplica)
- Checklist mínimo:
  - lint pasa
  - tests pasan
  - seguridad básica (no secretos)

### Plantilla sugerida de PR

```md
## Summary
- 

## Changes
- 

## Test plan
- [ ] Unit tests
- [ ] API smoke test
- [ ] UI happy path

## Notes / Risks
- 
```

### Política de revisión

- 1 aprobación mínima (2 si el cambio toca seguridad/infra).
- Revisar:
  - seguridad (auth, uploads)
  - performance (OCR/embeddings)
  - consistencia de API
  - migraciones DB

---

## Flujo de feature (feature workflow)

1. Crear rama desde `main`:
   - `git checkout -b feat/<feature>`
2. Hacer commits pequeños y coherentes.
3. Mantener rama actualizada:
   - `git fetch origin`
   - `git rebase origin/main` (o merge según política)
4. Abrir PR temprano (Draft) si es grande.
5. Asegurar checks verdes.
6. Merge:
   - “Squash and merge” recomendado para historial limpio
   - “Rebase and merge” si se quiere mantener commits

---

## Releases (release workflow)

### Versionado

Recomendación: **SemVer** (`MAJOR.MINOR.PATCH`).

- `0.x`: etapa temprana (cambios breaking más comunes)
- `1.0`: contrato más estable

### Proceso

- Etiquetar release cuando:
  - MVP estable o features completas
  - docs y deployment verificados
- Crear tag:
  - `v0.1.0`, `v0.2.0`, etc.
- Notas del release incluyen:
  - features
  - breaking changes
  - migraciones
  - instrucciones

---

## CI/CD (recomendación para GitHub Actions)

Aunque el proyecto es local-first, CI ayuda a evitar roturas.

Checks sugeridos:

- Backend:
  - lint/format (ruff/black/isort, si se adopta)
  - type-check (mypy, opcional)
  - tests (pytest)
- Frontend:
  - lint (eslint)
  - tests (vitest/jest)
  - build (next build)
- Security:
  - secret scanning (GitHub)
  - dependency scanning (Dependabot)
  - SAST básico (CodeQL opcional)

---

## Políticas de protección de rama (branch protection)

Para `main`:

- Require PR before merging
- Require status checks to pass
- Require linear history (opcional)
- Require signed commits (opcional)
- Restrict who can push to matching branches

---

## Hygiene (higiene del repo)

- No subir:
  - `.env`
  - `uploads/` (binarios)
  - volúmenes, DB dumps
  - modelos
- Mantener:
  - `.gitignore` estricto
  - `docs/` actualizado
  - `scripts/` para tareas repetibles (backup, reindex)

