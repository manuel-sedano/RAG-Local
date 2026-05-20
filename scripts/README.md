# Scripts operativos

Comandos pensados para **WSL / bash**. En Windows puedes ejecutarlos con `bash scripts/…`.

| Script | Propósito |
|--------|-----------|
| `run-celery-worker.sh` | **Worker de ingesta** (PDF → chunk → embed → Qdrant). Obligatorio en dev local si no usas `CELERY_TASK_ALWAYS_EAGER=true`. |
| `reset-qdrant-collection.sh` | Borra `rag_chunks_v1` tras `qdrant_dimension_mismatch`; luego reindexar documentos. |
| `backup.sh` | Stub: futuro `pg_dump` + copia de uploads. |
| `reindex.sh` | Stub: futura reindexación vía worker/API. |
| `reset-dev.sh` | Stub: futuro `docker compose down -v` documentado. |

Hazlos ejecutables en Linux/WSL:

```bash
chmod +x scripts/*.sh
```
