#!/usr/bin/env bash
# Valida el shell de frontend (layout KB, i8n, build).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[]}")/.." && pwd)"
cd "$ROOT/frontend"

if [[ ! -f .env.local ]] && [[ -f .env.example ]]; then
  echo "Aviso: copia frontend/.env.example → frontend/.env.local si aún no existe."
fi

echo "== ESLint =="
npm run lint

echo "== Build producción =="
npm run build

echo "== Archivos del layout =="
for f in \
  src/lib/i8n/es.ts \
  src/components/page-state.tsx \
  src/components/kb-workspace-layout.tsx \
  src/components/kb-sidebar.tsx \
  src/components/chat-quick-panel.tsx \
  src/app/kbs/\[kbId\]/layout.tsx; do
  [[ -f "$f" ]] || { echo "Falta: $f"; exit ; }
done

echo "OK — frontend layout listo. Prueba manual:"
echo "  . Backend: uvicorn en :8 con CORS para http://localhost:3"
echo "  2. npm run dev en frontend/"
echo "  3. Login → selecciona KB → /kbs/{id}/documents (sidebar + panel chat en xl)"
echo "  4. /kbs/{id}/chats → lista en sidebar; abre un chat (panel principal)"
