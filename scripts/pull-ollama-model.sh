#!/usr/bin/env bash
# Descarga un modelo en el contenedor Ollama del stack Docker (no requiere CLI en el host).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${1:-${LLM_MODEL:-qwen2.5:7b-instruct}}"
CONTAINER="${OLLAMA_CONTAINER:-rag_ollama}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Contenedor $CONTAINER no está en ejecución. Levantando ollama..."
  docker compose up -d ollama
fi

echo "== Pull $MODEL en $CONTAINER =="
docker exec "$CONTAINER" ollama pull "$MODEL"

echo "== Modelos disponibles =="
docker exec "$CONTAINER" ollama list

echo
echo "Asegúrate de que backend/.env tenga LLM_MODEL=$MODEL"
