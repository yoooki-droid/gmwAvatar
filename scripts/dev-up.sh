#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"

BACKEND_PORT="8000"
FRONTEND_PORT="5174"

mkdir -p "$RUN_DIR" "$LOG_DIR"

check_port() {
  local port="$1"
  if lsof -iTCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

wait_port_ready() {
  local port="$1"
  local max_retry="${2:-20}"
  local i
  for ((i=1; i<=max_retry; i++)); do
    if lsof -iTCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_detached() {
  local log_file="$1"
  shift

  # 统一使用 nohup，避免终端/任务结束后子进程被回收。
  nohup "$@" >"$log_file" 2>&1 < /dev/null &
  STARTED_PID="$!"
}

start_backend() {
  echo "[1/2] 启动后端服务..."
  if check_port "$BACKEND_PORT"; then
    echo "后端已在运行: http://127.0.0.1:$BACKEND_PORT"
    return 0
  fi

  cd "$BACKEND_DIR"
  if [ ! -d ".venv" ]; then
    python3 -m venv .venv
  fi

  source .venv/bin/activate
  pip install -r requirements.txt >/dev/null

  local backend_pid
  start_detached "$LOG_DIR/backend.log" .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
  backend_pid="$STARTED_PID"
  sleep 1
  if ! kill -0 "$backend_pid" >/dev/null 2>&1; then
    echo "后端进程启动后立即退出，请查看日志：$LOG_DIR/backend.log"
    rm -f "$RUN_DIR/backend.pid"
    return 1
  fi

  if ! wait_port_ready "$BACKEND_PORT" 20; then
    echo "后端启动失败，请查看日志：$LOG_DIR/backend.log"
    tail -n 40 "$LOG_DIR/backend.log" || true
    rm -f "$RUN_DIR/backend.pid"
    return 1
  fi
  echo "$backend_pid" >"$RUN_DIR/backend.pid"
  echo "后端启动成功: http://127.0.0.1:$BACKEND_PORT"
}

start_frontend() {
  echo "[2/2] 启动前端服务..."
  if check_port "$FRONTEND_PORT"; then
    echo "前端已在运行: http://127.0.0.1:$FRONTEND_PORT"
    return 0
  fi

  cd "$FRONTEND_DIR"
  npm install >/dev/null

  local frontend_pid
  start_detached "$LOG_DIR/frontend.log" ./node_modules/.bin/vite --host 0.0.0.0 --port "$FRONTEND_PORT"
  frontend_pid="$STARTED_PID"
  sleep 1
  if ! kill -0 "$frontend_pid" >/dev/null 2>&1; then
    echo "前端进程启动后立即退出，请查看日志：$LOG_DIR/frontend.log"
    rm -f "$RUN_DIR/frontend.pid"
    return 1
  fi

  if ! wait_port_ready "$FRONTEND_PORT" 20; then
    echo "前端启动失败，请查看日志：$LOG_DIR/frontend.log"
    tail -n 40 "$LOG_DIR/frontend.log" || true
    rm -f "$RUN_DIR/frontend.pid"
    return 1
  fi
  echo "$frontend_pid" >"$RUN_DIR/frontend.pid"
  echo "前端启动成功: http://127.0.0.1:$FRONTEND_PORT"
}

start_backend
start_frontend

echo ""
echo "一键启动完成"
echo "前端: http://127.0.0.1:$FRONTEND_PORT"
echo "后端: http://127.0.0.1:$BACKEND_PORT"
echo "日志: $LOG_DIR/backend.log, $LOG_DIR/frontend.log"
echo "停止服务: ./scripts/dev-down.sh"
