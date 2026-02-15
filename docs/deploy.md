# gmwAvatar 部署文档

## 1. 部署概览
- **部署时间**：2026-02-15
- **服务器**：阿里云轻量应用服务器 (`yoki-aliyun`)
- **IP 地址**：`47.100.20.107`
- **域名**：`adty.octaveliving.com`
- **前端**：Nginx 托管静态文件 (Vue 3 built artifacts)
- **后端**：Systemd 服务 (`gmwavatar`) + Uvicorn (Port 8000)
- **数据库**：SQLite (`backend/gmwavatar.db`)
- **HTTPS**：Let's Encrypt (Certbot 自动续期)

## 2. 目录结构 (服务器端)
部署根目录：`/var/www/gmwAvatar`

```
/var/www/gmwAvatar/
├── frontend/       # 前端构建产物 (dist目录内容)
└── backend/        # 后端 Python 代码
    ├── .env        # 环境变量配置
    ├── gmwavatar.db # SQLite 数据库
    └── venv/       # Python 虚拟环境
```

## 3. 服务管理

### 后端服务
后端通过 systemd 进行管理，服务名为 `gmwavatar`。

```bash
# 查看状态
systemctl status gmwavatar

# 重启服务
sudo systemctl restart gmwavatar

# 查看日志
journalctl -u gmwavatar -f
```

### Nginx 服务
Nginx 负责托管前端静态资源和反向代理 API 请求。

```bash
# 查看状态
systemctl status nginx

# 重启 Nginx
sudo systemctl restart nginx

# 配置文件位置
# /etc/nginx/sites-available/gmwavatar
```

## 4. 部署流程记录

### 4.1 环境准备
1. 安装系统依赖：`nginx`, `python3-pip`, `python3-venv`。
2. 创建部署目录 `/var/www/gmwAvatar` 并设置权限。

### 4.2 代码同步
使用 `rsync` 将本地代码同步至服务器：
```bash
# 同步后端
rsync -avz --exclude '__pycache__' --exclude 'venv' --exclude '.git' backend/ yoki-aliyun:/var/www/gmwAvatar/backend/

# 同步前端 (需先在本地运行 npm run build)
rsync -avz frontend/dist/ yoki-aliyun:/var/www/gmwAvatar/frontend/
```

### 4.3 后端配置
1. 在服务器创建虚拟环境：
   ```bash
   cd /var/www/gmwAvatar/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. 配置 Systemd 服务文件 `/etc/systemd/system/gmwavatar.service`。

### 4.4 Nginx 与 HTTPS
1. 配置 Nginx 站点 `/etc/nginx/sites-available/gmwavatar`：
   - 根目录指向 `/var/www/gmwAvatar/frontend`
   - `/api` 转发至 `http://127.0.0.1:8000`
2. 使用 Certbot 启用 HTTPS：
   ```bash
   sudo certbot --nginx -d adty.octaveliving.com
   ```
   - 证书自动续期已配置。
   - HTTP 强制重定向至 HTTPS。

## 5. 维护指南
- **更新前端**：本地 `npm run build` 后，重新执行前端 rsync 同步。
- **更新后端**：执行后端 rsync 同步后，重启后端服务 `sudo systemctl restart gmwavatar`。
- **查看日志**：使用 `journalctl` 查看后端报错，Nginx 日志位于 `/var/log/nginx/`。
