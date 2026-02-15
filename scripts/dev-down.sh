#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

stop_by_pid_file() {
  local name="$1"
  local file="$RUN_DIR/$name.pid"
  if [ ! -f "$file" ]; then
    echo "$name 未检测到 PID 文件，跳过。"
    return 0
  fi

  local pid
  pid="$(cat "$file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 0.5
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    echo "$name 已停止（PID: $pid）"
  else
    echo "$name 进程不存在，清理 PID 文件。"
  fi
  rm -f "$file"
}

stop_by_port() {
  local name="$1"
  local port="$2"
  local pids
  pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null || true)"
  if [ -z "$pids" ]; then
    return 0
  fi
  echo "$name 检测到端口 $port 仍被占用，执行兜底停止。"
  # shellcheck disable=SC2086
  kill $pids >/dev/null 2>&1 || true
  sleep 0.5
  pids="$(lsof -t -iTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    # shellcheck disable=SC2086
    kill -9 $pids >/dev/null 2>&1 || true
  fi
}

stop_by_pid_file "backend"
stop_by_pid_file "frontend"
stop_by_port "backend" "8000"
stop_by_port "frontend" "5174"

echo "服务停止完成。"
