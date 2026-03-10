# CF Problem List

Codeforces 题单管理系统

## 本地开发

### 环境要求

- Go 1.25+
- SQLite3

### 启动服务

```bash
# 启动（自动构建并运行）
./manage.sh start

# 其他命令
./manage.sh stop      # 停止
./manage.sh restart   # 重启（代码修改后使用）
./manage.sh status     # 查看状态
./manage.sh logs       # 查看日志
./manage.sh build      # 仅构建
```

服务启动后访问: http://localhost:8080

## 服务器部署

### 方式一：自动部署（推荐）

```bash
# 从本地部署到服务器
./manage.sh deploy user@your-server /opt/cfProblemList
```

### 方式二：手动部署

```bash
# 1. 在本地构建
./manage.sh build

# 2. 上传到服务器
scp cfProblemList user@your-server:/opt/cfProblemList/
scp -r static user@your-server:/opt/cfProblemList/
scp -r data user@your-server:/opt/cfProblemList/
```

### 安装为系统服务

首次部署后，在服务器上执行：

```bash
ssh user@your-server
cd /opt/cfProblemList
sudo ./install.sh
```

安装脚本会：
- 创建必要的目录结构
- 设置文件权限
- 安装 systemd 服务
- 启动服务

### 服务管理

安装完成后，使用统一的管理脚本：

```bash
# 启动服务
sudo ./manage.sh start

# 停止服务
sudo ./manage.sh stop

# 重启服务（代码更新后）
sudo ./manage.sh restart

# 查看状态
sudo ./manage.sh status

# 查看日志
sudo ./manage.sh logs
```

> `manage.sh` 会自动检测环境：本地开发使用 nohup 后台运行，服务器上以 root 运行时自动使用 systemd 管理。

### 代码更新流程

```bash
# 1. 本地修改代码后，重新部署
./manage.sh deploy user@your-server /opt/cfProblemList

# 2. 在服务器上重启
ssh user@your-server
cd /opt/cfProblemList
sudo ./manage.sh restart
```

或者一步完成：

```bash
./manage.sh deploy user@your-server /opt/cfProblemList && \
ssh user@your-server "cd /opt/cfProblemList && sudo ./manage.sh restart"
```

## 目录结构

```
.
├── main.go              # 程序入口
├── manage.sh            # 管理脚本
├── install.sh           # 服务器安装脚本
├── cfproblemlist.service # systemd 服务配置
├── api/                 # API 处理器
├── crawler/             # 爬虫模块
├── service/             # 业务逻辑
├── models/              # 数据模型
├── static/              # 静态文件
├── data/                # 数据存储
└── logs/                # 日志文件
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/problemsets | 获取题单列表 |
| GET | /api/problemsets/:id | 获取题单详情 |
| POST | /api/register | 用户注册 |
| POST | /api/login | 用户登录 |
| GET | /api/user | 获取当前用户（需认证） |
| POST | /api/progress | 更新进度（需认证） |
| GET | /api/progress | 获取进度（需认证） |