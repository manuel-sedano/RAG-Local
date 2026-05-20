# Convenciones Docker (Compose)

## Identificadores en `docker-compose.yml`

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| **Red** | `rag_net` | Una sola red bridge interna para tráfico entre servicios. |
| **Volúmenes** | `rag_vol_<propósito>` | `rag_vol_postgres`, `rag_vol_qdrant`, `rag_vol_ollama`, `rag_vol_uploads` |
| **Nombre de contenedor** | `rag_<servicio>` | `rag_traefik`, `rag_postgres` (opcional; mejora trazabilidad en logs) |

## Servicios (nombres Compose)

Usar **snake_case** corto, alineado al rol: `traefik`, `frontend`, `backend`, `worker`, `postgres`, `redis`, `qdrant`, `ollama`, `clamav`, `prometheus`, `grafana`, `loki`.

- **Traefik** es el único servicio con puertos publicados al host (`80` / `443`).
- El resto se descubre por **DNS interno** (`http://backend:80`, `http://postgres:5432`, etc.).

## Perfiles opcionales

| Perfil | Servicios |
|--------|-----------|
| `clamav` | Antivirus para escaneo de subidas (arranque lento). |
| `waf` | ModSecurity CRS entre Traefik y backend (`docker-compose.waf.yml`). |
| `observability` | Prometheus, Grafana, Loki, Promtail (scrape contenedores con label `logging.promtail=true`). |

Ejemplo:

```bash
docker compose -f docker-compose.yml -f docker-compose.waf.yml --profile waf --profile observability up -d
```
