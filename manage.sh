#!/bin/bash

# CF Problem List 服务管理脚本
# 用法: ./manage.sh {start|stop|restart|status|build|logs}
# 本地开发: 直接运行，使用 nohup 后台运行
# 服务器: 通过 systemd 管理服务

set -e

# 配置
APP_NAME="cfProblemList"
SERVICE_NAME="cfproblemlist"
BINARY_NAME="cfProblemList"
PID_FILE="./${APP_NAME}.pid"
LOG_DIR="./logs"
LOG_FILE="${LOG_DIR}/server.log"
PORT=8080

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检测是否使用 systemd
use_systemd() {
    # 如果是 root 且 systemd 服务存在，使用 systemd
    [ "$EUID" -eq 0 ] && systemctl list-unit-files "${SERVICE_NAME}.service" &>/dev/null
}

# 检查服务是否运行（本地模式）
is_running_local() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        ps -p "$PID" > /dev/null 2>&1
        return $?
    fi
    return 1
}

# 获取端口占用的 PID
get_port_pid() {
    lsof -ti:$PORT 2>/dev/null || echo ""
}

# 构建项目
build() {
    log_info "Building ${APP_NAME}..."
    go build -o "${BINARY_NAME}" .
    log_info "Build completed: ${BINARY_NAME}"
}

# ========== Systemd 模式 ==========

start_systemd() {
    log_info "Starting ${APP_NAME} via systemd..."
    systemctl start ${SERVICE_NAME}
    sleep 1
    status_systemd
}

stop_systemd() {
    log_info "Stopping ${APP_NAME} via systemd..."
    systemctl stop ${SERVICE_NAME}
    log_info "${APP_NAME} stopped"
}

restart_systemd() {
    log_info "Restarting ${APP_NAME} via systemd..."
    systemctl restart ${SERVICE_NAME}
    sleep 1
    status_systemd
}

status_systemd() {
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log_info "${APP_NAME} is running"
        systemctl status ${SERVICE_NAME} --no-pager
    else
        log_warn "${APP_NAME} is not running"
    fi
}

logs_systemd() {
    journalctl -u ${SERVICE_NAME} -f
}

build_systemd() {
    build
    log_info "Restarting service to apply changes..."
    systemctl restart ${SERVICE_NAME}
}

# ========== 本地模式 ==========

start_local() {
    if is_running_local; then
        log_warn "${APP_NAME} is already running (PID: $(cat $PID_FILE))"
        return 1
    fi

    PORT_PID=$(get_port_pid)
    if [ -n "$PORT_PID" ]; then
        log_error "Port $PORT is already in use by PID $PORT_PID"
        return 1
    fi

    mkdir -p "$LOG_DIR"
    build

    log_info "Starting ${APP_NAME}..."
    nohup ./"${BINARY_NAME}" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 1
    
    if is_running_local; then
        log_info "${APP_NAME} started (PID: $(cat $PID_FILE))"
        log_info "Server: http://localhost:${PORT}"
    else
        log_error "Failed to start. Check logs: ${LOG_FILE}"
        return 1
    fi
}

stop_local() {
    if ! is_running_local; then
        log_warn "${APP_NAME} is not running"
        PORT_PID=$(get_port_pid)
        [ -n "$PORT_PID" ] && kill "$PORT_PID" 2>/dev/null || true
        [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
        return 0
    fi

    PID=$(cat "$PID_FILE")
    log_info "Stopping ${APP_NAME} (PID: $PID)..."
    
    kill "$PID" 2>/dev/null || true
    
    for i in {1..10}; do
        ps -p "$PID" > /dev/null 2>&1 || break
        sleep 1
    done
    
    ps -p "$PID" > /dev/null 2>&1 && kill -9 "$PID" 2>/dev/null || true
    
    rm -f "$PID_FILE"
    log_info "${APP_NAME} stopped"
}

restart_local() {
    log_info "Restarting ${APP_NAME}..."
    stop_local
    sleep 1
    start_local
}

status_local() {
    if is_running_local; then
        PID=$(cat "$PID_FILE")
        log_info "${APP_NAME} is running (PID: $PID)"
        log_info "Port: ${PORT}"
        log_info "Log: ${LOG_FILE}"
        MEM=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
        log_info "Memory: ${MEM}"
    else
        log_warn "${APP_NAME} is not running"
        PORT_PID=$(get_port_pid)
        [ -n "$PORT_PID" ] && log_warn "Port $PORT in use by PID $PORT_PID"
    fi
}

logs_local() {
    [ -f "$LOG_FILE" ] && tail -f "$LOG_FILE" || log_error "Log file not found"
}

# ========== 主入口 ==========

usage() {
    echo "Usage: $0 {start|stop|restart|status|build|logs}"
    echo ""
    echo "Commands:"
    echo "  start   - Start the service"
    echo "  stop    - Stop the service"
    echo "  restart - Restart the service"
    echo "  status  - Check service status"
    echo "  build   - Build the binary"
    echo "  logs    - Tail the log file"
    echo ""
    if use_systemd; then
        echo "Mode: systemd (${SERVICE_NAME}.service)"
    else
        echo "Mode: local (nohup background)"
    fi
}

case "$1" in
    start)
        if use_systemd; then start_systemd; else start_local; fi
        ;;
    stop)
        if use_systemd; then stop_systemd; else stop_local; fi
        ;;
    restart)
        if use_systemd; then restart_systemd; else restart_local; fi
        ;;
    status)
        if use_systemd; then status_systemd; else status_local; fi
        ;;
    build)
        if use_systemd; then build_systemd; else build; fi
        ;;
    logs)
        if use_systemd; then logs_systemd; else logs_local; fi
        ;;
    *)
        usage
        exit 1
        ;;
esac