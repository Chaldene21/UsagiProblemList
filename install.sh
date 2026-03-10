#!/bin/bash

# 服务器端一键安装脚本
# 在服务器上运行: curl -fsSL https://your-server/install.sh | bash
# 或者: ./install.sh

set -e

APP_NAME="cfProblemList"
INSTALL_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root: sudo $0"
    exit 1
fi

# 创建目录
log_info "Creating directories..."
mkdir -p "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}/logs"
mkdir -p "${INSTALL_DIR}/data"

# 复制文件（假设已经在项目目录）
if [ -f "./cfProblemList" ]; then
    cp ./cfProblemList "${INSTALL_DIR}/"
    log_info "Binary copied"
fi

# 复制静态文件和数据库
if [ -d "./static" ]; then
    cp -r ./static "${INSTALL_DIR}/"
    log_info "Static files copied"
fi

if [ -d "./data" ]; then
    cp -r ./data "${INSTALL_DIR}/"
    log_info "Data directory copied"
fi

# 复制管理脚本
if [ -f "./manage.sh" ]; then
    cp ./manage.sh "${INSTALL_DIR}/"
    chmod +x "${INSTALL_DIR}/manage.sh"
fi

# 设置权限
log_info "Setting permissions..."
chown -R www-data:www-data "${INSTALL_DIR}"
chmod -R 755 "${INSTALL_DIR}"

# 安装 systemd 服务
log_info "Installing systemd service..."
if [ -f "./cfproblemlist.service" ]; then
    cp ./cfproblemlist.service /etc/systemd/system/${SERVICE_NAME}.service
else
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=CF Problem List Web Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/cfProblemList
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5s
StandardOutput=append:${INSTALL_DIR}/logs/server.log
StandardError=append:${INSTALL_DIR}/logs/error.log

[Install]
WantedBy=multi-user.target
EOF
fi

# 重载 systemd
systemctl daemon-reload

# 启用并启动服务
log_info "Enabling service..."
systemctl enable ${SERVICE_NAME}

log_info "Starting service..."
systemctl start ${SERVICE_NAME}

# 检查状态
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "Service is running!"
    log_info "Service commands:"
    echo "  sudo systemctl status ${SERVICE_NAME}   # 查看状态"
    echo "  sudo systemctl restart ${SERVICE_NAME}  # 重启服务"
    echo "  sudo systemctl stop ${SERVICE_NAME}     # 停止服务"
    echo "  sudo journalctl -u ${SERVICE_NAME} -f   # 查看日志"
else
    log_error "Service failed to start. Check logs:"
    echo "  sudo journalctl -u ${SERVICE_NAME} -n 50"
fi