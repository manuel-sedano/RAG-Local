#!/usr/bin/env bash
# Elimina contenedores rag_* huérfanos (p. ej. proyecto antiguo rag-local vs rag).
set -euo pipefail

NAMES=(
  rag_traefik
  rag_frontend
  rag_backend
  rag_worker
  rag_postgres
  rag_redis
  rag_qdrant
  rag_ollama
  rag_clamav
  rag_waf
  rag_prometheus
  rag_grafana
  rag_loki
  rag_promtail
)

echo "== Deteniendo contenedores RAG por nombre fijo =="
for name in "${NAMES[@]}"; do
  if docker rm -f "${name}" 2>/dev/null; then
    echo "  removed ${name}"
  fi
done

echo "== Asegurando red rag_net =="
if ! docker network inspect rag_net >/dev/null 2>&1; then
  docker network create rag_net
  echo "  creada rag_net"
else
  echo "  rag_net ya existe"
fi

echo "OK: docker-rag-clean.sh"
