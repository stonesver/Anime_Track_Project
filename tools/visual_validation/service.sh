#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST="${VISUAL_VALIDATION_HOST:-127.0.0.1}"
PORT="${VISUAL_VALIDATION_PORT:-8765}"
URL="http://${HOST}:${PORT}"
PID_FILE="${ROOT_DIR}/.visual-validation.pid"
LOG_FILE="${ROOT_DIR}/tools/visual_validation/visual_validation.log"

pid_for_port() {
  lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

is_healthy() {
  curl -fsS "${URL}/api/health" >/dev/null 2>&1
}

open_page() {
  if command -v open >/dev/null 2>&1; then
    open "${URL}" >/dev/null 2>&1 || true
  fi
}

start_service() {
  if is_healthy; then
    echo "Visual validation service is already running: ${URL}"
    return 0
  fi

  local port_pid
  port_pid="$(pid_for_port)"
  if [[ -n "${port_pid}" ]]; then
    echo "Port ${PORT} is occupied by PID ${port_pid}, but health check failed."
    echo "Run: tools/visual_validation/service.sh restart"
    return 1
  fi

  nohup python3 "${ROOT_DIR}/tools/visual_validation/server.py" \
    --host "${HOST}" \
    --port "${PORT}" \
    >"${LOG_FILE}" 2>&1 &
  echo "$!" >"${PID_FILE}"

  sleep 1
  if is_healthy; then
    echo "Visual validation service started: ${URL}"
    echo "Log file: ${LOG_FILE}"
    return 0
  fi

  echo "Visual validation service failed to start. Check log: ${LOG_FILE}"
  return 1
}

stop_service() {
  local pid=""
  if [[ -f "${PID_FILE}" ]]; then
    pid="$(cat "${PID_FILE}")"
  fi

  if [[ -z "${pid}" ]]; then
    pid="$(pid_for_port)"
  fi

  if [[ -z "${pid}" ]]; then
    echo "Visual validation service is not running."
    rm -f "${PID_FILE}"
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  for _ in {1..20}; do
    if [[ -z "$(pid_for_port)" ]]; then
      break
    fi
    sleep 0.2
  done
  rm -f "${PID_FILE}"
  echo "Visual validation service stopped: PID ${pid}"
}

status_service() {
  local pid
  pid="$(pid_for_port)"
  if is_healthy; then
    echo "Visual validation service is healthy: ${URL}"
    [[ -n "${pid}" ]] && echo "PID: ${pid}"
    return 0
  fi

  if [[ -n "${pid}" ]]; then
    echo "Port ${PORT} is occupied by PID ${pid}, but health check failed."
    return 1
  fi

  echo "Visual validation service is not running."
  return 1
}

case "${1:-start}" in
  start)
    start_service
    ;;
  start-open)
    start_service
    open_page
    ;;
  stop)
    stop_service
    ;;
  restart)
    stop_service
    start_service
    ;;
  restart-open)
    stop_service
    start_service
    open_page
    ;;
  status)
    status_service
    ;;
  *)
    echo "Usage: $0 {start|start-open|stop|restart|restart-open|status}"
    exit 2
    ;;
esac
