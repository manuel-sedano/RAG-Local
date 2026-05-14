# Convención de issues en GitHub

**Alcance:** cuándo crear un issue, cómo titularlo y qué etiquetas usar en este repositorio.

---

## Issue vs pull request

- **Issue:** hueco de trabajo, bug reportado, deuda técnica o pregunta de diseño **antes** de tener rama lista.
- **Pull request:** implementación concreta enlazada a una rama (`feat/*`, `fix/*`, `docs/*`, `chore/*`, …). Referencia el issue con `Closes #123` o `Refs #123` en la descripción si aplica.

---

## Títulos sugeridos

```text
[<área>] <verbo en imperativo> <objeto corto>
```

**Áreas (ejemplos):** `backend`, `frontend`, `docker`, `rag`, `docs`, `security`, `ci`.

**Ejemplos:**

- `[backend] Exponer health check con dependencias`
- `[docs] Aclarar smoke test con perfil observability`
- `[frontend] Corregir contraste del visor PDF`

---

## Etiquetas sugeridas (crear en el repo si no existen)

| Etiqueta        | Uso breve                                      |
|-----------------|------------------------------------------------|
| `bug`           | Comportamiento incorrecto reproducible       |
| `enhancement`   | Mejora de producto o UX                       |
| `tech-debt`     | Refactor o limpieza sin cambio visible       |
| `docs`          | Solo documentación                           |
| `security`      | Vulnerabilidad o endurecimiento              |
| `blocked`       | Espera externa o dependencia                  |
| `good first issue` | Tarea acotada para nuevos colaboradores   |

Prioridad opcional: `priority:high`, `priority:low` (solo si el equipo las adopta).

---

## Plantilla de PR

Los PR deben seguir la checklist del archivo **`.github/pull_request_template.md`**. Resumen del flujo de ramas: `03-github-workflow.md`.
