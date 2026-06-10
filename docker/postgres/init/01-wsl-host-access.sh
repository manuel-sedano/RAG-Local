#!/usr/bin/env bash
# Permite conexiones TCP desde el bridge de Docker (WSL / Docker Desktop → puerto publicado).
set -euo pipefail
{
  echo ""
  echo "# rag-local: acceso desde host vía puerto publicado (IP del bridge, p. ej. 172.18.0.1)"
  echo "host all all 172.16.0.0/12 scram-sha-256"
  echo "host all all 10.0.0.0/8 scram-sha-256"
  echo "host all all 192.168.0.0/16 scram-sha-256"
} >> "${PGDATA}/pg_hba.conf"
