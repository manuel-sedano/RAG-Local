# Scripts operativos

Comandos pensados para **WSL / bash**. En Windows puedes ejecutarlos con `bash scripts/…`.

| Script | Propósito |
|--------|-----------|
| `backup.sh` | Stub: futuro `pg_dump` + copia de uploads. |
| `reindex.sh` | Stub: futura reindexación vía worker/API. |
| `reset-dev.sh` | Stub: futuro `docker compose down -v` documentado. |

Hazlos ejecutables en Linux/WSL:

```bash
chmod +x scripts/*.sh
```
