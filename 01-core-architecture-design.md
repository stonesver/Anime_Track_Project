# 追番系统核心业务层架构设计

## 1. 目标

本系统用于实现一个面向个人或小范围群组使用的追番管理工具，支持：

1. 从 yuc.wiki 同步季度新番信息；
2. 展示当前季度、指定季度的新番表；
3. 按星期生成新番周表；
4. 查询番剧详情；
5. 添加、取消、查看追番；
6. 按番剧更新时间进行 QQ 私聊或群聊提醒；
7. 绑定 B 站观看入口；
8. 集成 qBittorrent RSS，支持自动下载状态管理；
9. 后续允许 OpenClaw / MiniMax 等大模型系统以插件方式接入。

---

## 2. 总体架构

推荐采用分层架构：

```text
┌────────────────────────────┐
│        用户交互层            │
│  QQ Bot / Web UI / API Client│
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│        核心业务 API          │
│        FastAPI Service       │
└──────────────┬─────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────────┐
│ 番剧服务 │ │ 追番服务 │ │ 观看方式服务 │
└────────┘ └────────┘ └────────────┘
     │         │         │
     ▼         ▼         ▼
┌────────────────────────────┐
│         数据库层             │
│ SQLite / PostgreSQL          │
└────────────────────────────┘
               │
               ▼
┌────────────────────────────┐
│        外部系统适配层         │
│ yuc.wiki / qBittorrent / QQ  │
└────────────────────────────┘
```

推荐部署拆分：

```text
anime-api      核心业务 API
anime-worker   定时任务：同步 yuc、发送提醒、检查下载状态
anime-bot      QQ Bot 适配层
qbittorrent    下载器
database       SQLite 或 PostgreSQL
openclaw       可选，大模型外挂层
```

---

## 3. 核心设计原则

### 3.1 核心业务层不依赖大模型

核心业务必须在没有 OpenClaw / MiniMax 的情况下完整可用。

例如：

```text
/新番
/周表
/追番
/我的追番
/绑定b站
/绑定rss
/rss状态
```

这些命令都应该直接由代码实现，而不是依赖 LLM 判断。

---

### 3.2 QQ Bot 只是交互入口

QQ Bot 不直接写数据库、不直接访问 qBittorrent、不直接解析 yuc.wiki。

它只调用核心 API：

```text
QQ Bot → anime-api → database / qBittorrent / yuc cache
```

这样以后可以替换 QQ 框架，不影响核心业务。

---

### 3.3 抓取、提醒、下载状态检查都由 Worker 负责

这些是后台任务，不适合放在请求响应流程里。

```text
anime-worker
├─ 每天同步 yuc.wiki
├─ 每 1~5 分钟扫描提醒
├─ 每 3~5 分钟检查 qBittorrent 下载状态
└─ 定期清理日志
```

---

### 3.4 qBittorrent 只通过受控适配器访问

核心系统不应该在业务代码里到处直接拼 qB API。

应该封装：

```text
QbitService
├─ login()
├─ add_rss_feed()
├─ create_rss_rule()
├─ list_rss_items()
├─ get_torrent_status()
└─ test_connection()
```

---

## 4. 推荐技术栈

### 4.1 后端

```text
Python 3.11+
FastAPI
SQLAlchemy 2.x
Pydantic
APScheduler
httpx
BeautifulSoup4 / lxml
```

### 4.2 QQ Bot

```text
NoneBot2
OneBot v11 Adapter
Lagrange.OneBot / NapCat / 其他 OneBot 实现
```

### 4.3 数据库

MVP 阶段：

```text
SQLite
```

正式使用或后续扩展：

```text
PostgreSQL
```

### 4.4 前端

第一阶段可以不做复杂前端。

可选方案：

```text
FastAPI + Jinja2 简单管理页
```

后续再升级为：

```text
Vue / React / SvelteKit
```

### 4.5 部署

```text
Docker Compose
Nginx 可选
```

---

## 5. 部署架构

### 5.1 Docker Compose 结构

```yaml
services:
  anime-api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    restart: always
    env_file:
      - .env
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"

  anime-worker:
    build: .
    command: python -m app.worker
    restart: always
    env_file:
      - .env
    volumes:
      - ./data:/data

  anime-bot:
    build: .
    command: python -m app.bot
    restart: always
    env_file:
      - .env
    volumes:
      - ./data:/data

  qbittorrent:
    image: lscr.io/linuxserver/qbittorrent
    restart: always
    environment:
      - WEBUI_PORT=8080
    volumes:
      - ./qbit/config:/config
      - ./downloads:/downloads
    ports:
      - "8080:8080"

  openclaw:
    image: your-openclaw-image
    restart: always
    env_file:
      - .env.openclaw
```

如果 qB WebUI 不需要公网访问，建议不要映射端口，而是只让容器内部访问：

```text
http://qbittorrent:8080
```

---

## 6. 环境变量设计

```env
APP_ENV=production
DATABASE_URL=sqlite:////data/anime.db

YUC_BASE_URL=https://yuc.wiki
DEFAULT_TIMEZONE=Asia/Shanghai

QBIT_BASE_URL=http://qbittorrent:8080
QBIT_USERNAME=admin
QBIT_PASSWORD=change-me
QBIT_DEFAULT_SAVE_PATH=/downloads/anime

ONEBOT_WS_URL=ws://onebot:3001
BOT_ADMIN_QQ=123456

OPENCLAW_API_KEY=xxx
```

---

## 7. 项目目录建议

```text
app/
  main.py
  config.py
  db.py

  models/
    anime.py
    user.py
    subscription.py
    watch.py
    rss.py
    remind.py

  schemas/
    anime.py
    subscription.py
    watch.py
    rss.py

  services/
    anime_service.py
    subscription_service.py
    reminder_service.py
    watch_service.py
    rss_service.py
    qbit_service.py

  scraper/
    yuc_scraper.py
    parser.py

  jobs/
    sync_yuc_job.py
    reminder_job.py
    qbit_status_job.py

  bot/
    main.py
    commands/
      anime.py
      subscription.py
      watch.py
      rss.py
    formatter.py

  api/
    routes_anime.py
    routes_subscription.py
    routes_watch.py
    routes_rss.py
    routes_tools.py

  security/
    auth.py
    permissions.py

  utils/
    time.py
    normalize.py
    title_match.py
```
