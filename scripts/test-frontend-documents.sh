#!/usr/bin/env bash
# Valida UI de documentos: filtros, detalle, visor PDF (build + archivos).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend"

if [[ ! -d node_modules/pdfjs-dist ]]; then
  echo "== npm install (pdfjs-dist) =="
  npm install
fi

echo "== ESLint =="
npm run lint

echo "== Build =="
npm run build

echo "== Archivos clave =="
for f in \
  src/components/document-filters.tsx \
  src/components/pdf-viewer.tsx \
  src/components/document-ingestion-stages.tsx \
  src/app/kbs/\[kbId\]/documents/\[docId\]/page.tsx \
  src/hooks/use-ingest-progress.ts; do
  [[ -f "$f" ]] || { echo "Falta: $f"; exit ; }
done

echo ""
echo "OK — Prueba manual:"
echo "  . Backend + worker + Postgres + Redis (ingesta real o eager en test)"
echo "  2. python -m scripts.seed_dev_user  (si no hay usuario)"
echo "  3. npm run dev → login → /kbs/{kbId}/documents"
echo "  4. Sube PDF con tags/origen; filtra por estado y tags"
echo "  . Abre detalle → visor PDF ?page=2; reindex; etapas de ingesta"
echo "  6. Swagger: GET /api/kbs/{kb_id}/documents (tags/source en items)"
