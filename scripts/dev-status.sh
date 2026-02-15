#!/usr/bin/env bash
set -euo pipefail

echo "=== 端口监听 ==="
lsof -nP -iTCP:5174 -sTCP:LISTEN || echo "前端未监听 5174"
lsof -nP -iTCP:8000 -sTCP:LISTEN || echo "后端未监听 8000"

echo ""
echo "=== 连通性 ==="
if curl -sS -I http://127.0.0.1:5174 >/dev/null; then
  echo "前端可访问: http://127.0.0.1:5174"
else
  echo "前端不可访问: http://127.0.0.1:5174"
fi

if curl -sS http://127.0.0.1:8000/healthz >/dev/null; then
  echo "后端可访问: http://127.0.0.1:8000/healthz"
else
  echo "后端不可访问: http://127.0.0.1:8000/healthz"
fi
