# 追番系统核心业务层详细设计

## 1. 领域模型设计

### 1.1 番剧 Anime

表示一部番剧的基础信息。

```sql
CREATE TABLE anime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season TEXT NOT NULL,
    title_cn TEXT,
    title_jp TEXT,
    title_en TEXT,
    title_original TEXT,
    description TEXT,
    weekday INTEGER,
    air_time TEXT,
    start_date DATE,
    end_date DATE,
    status TEXT NOT NULL DEFAULT 'unknown',
    cover_url TEXT,
    official_url TEXT,
    yuc_url TEXT,
    pv_url TEXT,
    source_type TEXT,
    studio TEXT,
    raw_detail_json TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

字段说明：

```text
season          例如 2026-04
weekday         1~7，周一到周日
air_time        例如 22:30
status          upcoming / airing / finished / unknown
source_type     漫画 / 小说 / 游戏 / 原创 / 其他
raw_detail_json 保留 yuc 原始解析详情，方便后续扩展
```

---

### 1.2 番剧别名 AnimeAlias

用于支持模糊搜索、RSS 匹配、B 站搜索。

```sql
CREATE TABLE anime_alias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    alias_type TEXT,
    source TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (anime_id) REFERENCES anime(id)
);
```

字段说明：

```text
alias_type:
- cn
- jp
- en
- short
- rss
- manual
- ai_suggested

source:
- yuc
- user
- llm
- system
```

---

### 1.3 季度 Season

用于管理季度抓取状态。

```sql
CREATE TABLE season (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season TEXT NOT NULL UNIQUE,
    title TEXT,
    yuc_url TEXT,
    last_sync_at DATETIME,
    sync_status TEXT,
    sync_error TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

示例：

```text
season: 2026-04
title: 2026年4月新番
yuc_url: https://yuc.wiki/202604
```

---

### 1.4 播出平台 AnimePlatformLink

保存 yuc 页面解析到的平台链接。

```sql
CREATE TABLE anime_platform_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anime_id INTEGER NOT NULL,
    platform TEXT,
    region TEXT,
    url TEXT NOT NULL,
    note TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (anime_id) REFERENCES anime(id)
);
```

---

### 1.5 用户 BotUser

用于映射 QQ 用户。

```sql
CREATE TABLE bot_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    platform_user_id TEXT NOT NULL,
    display_name TEXT,
    timezone TEXT DEFAULT 'Asia/Shanghai',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE(platform, platform_user_id)
);
```

---

### 1.6 追番订阅 Subscription

```sql
CREATE TABLE subscription (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    anime_id INTEGER NOT NULL,
    remind_enabled BOOLEAN NOT NULL DEFAULT 1,
    remind_before_minutes INTEGER NOT NULL DEFAULT 0,
    remind_channel TEXT NOT NULL DEFAULT 'private',
    qq_group_id TEXT,
    watch_mode TEXT NOT NULL DEFAULT 'manual',
    status TEXT NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES bot_user(id),
    FOREIGN KEY (anime_id) REFERENCES anime(id),
    UNIQUE(user_id, anime_id)
);
```

字段说明：

```text
remind_channel:
- private
- group

watch_mode:
- manual
- bilibili
- rss
- mixed

status:
- active
- paused
- dropped
```

---

### 1.7 观看绑定 WatchBinding

一部番可以有多个观看方式。

```sql
CREATE TABLE watch_binding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    binding_type TEXT NOT NULL,
    title TEXT,
    url TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    extra_json TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (subscription_id) REFERENCES subscription(id)
);
```

字段说明：

```text
binding_type:
- bilibili_search
- bilibili_manual
- rss
- local_path
- manual_note
```

---

### 1.8 RSS 规则 RssRule

```sql
CREATE TABLE rss_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    rule_name TEXT NOT NULL,
    feed_url TEXT,
    must_contain TEXT,
    must_not_contain TEXT,
    use_regex BOOLEAN NOT NULL DEFAULT 1,
    smart_filter BOOLEAN NOT NULL DEFAULT 1,
    episode_filter TEXT,
    save_path TEXT,
    qbit_rule_name TEXT,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (subscription_id) REFERENCES subscription(id)
);
```

字段说明：

```text
status:
- draft
- active
- disabled
- error
```

---

### 1.9 RSS 匹配记录 RssMatch

```sql
CREATE TABLE rss_match (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rss_rule_id INTEGER,
    anime_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    feed_url TEXT,
    torrent_url TEXT,
    episode_no INTEGER,
    qbit_hash TEXT,
    download_status TEXT,
    progress REAL,
    save_path TEXT,
    matched_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (rss_rule_id) REFERENCES rss_rule(id),
    FOREIGN KEY (anime_id) REFERENCES anime(id)
);
```

字段说明：

```text
download_status:
- matched
- downloading
- completed
- failed
- unknown
```

---

### 1.10 提醒记录 RemindLog

用于防止重复提醒。

```sql
CREATE TABLE remind_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    anime_id INTEGER NOT NULL,
    remind_key TEXT NOT NULL,
    scheduled_at DATETIME NOT NULL,
    sent_at DATETIME,
    channel TEXT,
    status TEXT NOT NULL,
    error TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (subscription_id) REFERENCES subscription(id),
    FOREIGN KEY (anime_id) REFERENCES anime(id),
    UNIQUE(subscription_id, remind_key)
);
```

`remind_key` 建议格式：

```text
anime_id:YYYY-MM-DD:HH:mm
```

---

## 2. 核心模块设计

### 2.1 YucScraper：新番数据抓取模块

#### 职责

```text
1. 抓取 yuc.wiki 首页
2. 解析季度列表
3. 抓取指定季度页面
4. 解析番剧基础信息
5. 解析周表
6. 解析番剧详情
7. 生成标准 Anime 数据结构
```

#### 接口设计

```python
class YucScraper:
    async def fetch_season_index(self) -> list[SeasonInfo]:
        ...

    async def fetch_season_page(self, season: str) -> str:
        ...

    def parse_season_page(self, html: str, season: str) -> list[AnimeParsed]:
        ...

    async def sync_season(self, season: str) -> SyncResult:
        ...
```

#### 解析结果结构

```python
class AnimeParsed(BaseModel):
    season: str
    title_cn: str | None
    title_jp: str | None
    title_en: str | None
    aliases: list[str]
    weekday: int | None
    air_time: str | None
    start_date: date | None
    cover_url: str | None
    official_url: str | None
    yuc_url: str | None
    platform_links: list[PlatformLinkParsed]
    detail: dict
```

#### 同步策略

```text
每天凌晨 3 点自动同步当前季度和下个季度
手动命令 /同步新番 可触发同步
每次同步保留原始 HTML 快照
解析失败时写 sync_error
```

#### 数据合并策略

根据以下字段判断同一番剧：

```text
优先：season + title_cn
其次：season + title_jp
再次：season + normalized_title
```

不建议只按标题匹配跨季度数据，因为续作和重播容易冲突。

---

### 2.2 AnimeService：番剧查询服务

#### 职责

```text
1. 查询当前季度
2. 查询指定季度番剧
3. 生成周表
4. 搜索番剧
5. 查询番剧详情
6. 管理别名
```

#### 主要接口

```python
class AnimeService:
    async def get_current_season(self) -> str:
        ...

    async def list_anime_by_season(self, season: str) -> list[AnimeDTO]:
        ...

    async def get_weekly_schedule(
        self,
        season: str,
        weekday: int | None = None
    ) -> WeeklyScheduleDTO:
        ...

    async def search_anime(self, query: str, season: str | None = None) -> list[AnimeSearchResult]:
        ...

    async def get_anime_detail(self, anime_id: int) -> AnimeDetailDTO:
        ...

    async def add_alias(self, anime_id: int, alias: str, source: str) -> None:
        ...
```

#### 搜索策略

第一版可以不用向量库，直接用：

```text
1. title_cn 精确匹配
2. title_jp 精确匹配
3. alias 精确匹配
4. title_cn LIKE
5. title_jp LIKE
6. alias LIKE
7. 简单归一化后匹配
```

归一化规则：

```text
去空格
转小写
全角转半角
去标点
去“第X季”“Season X”等可选后缀
```

---

### 2.3 SubscriptionService：追番订阅服务

#### 职责

```text
1. 添加追番
2. 取消追番
3. 暂停追番
4. 恢复追番
5. 查看我的追番
6. 修改提醒配置
```

#### 主要接口

```python
class SubscriptionService:
    async def subscribe(
        self,
        user_id: int,
        anime_id: int,
        remind_before_minutes: int = 0,
        channel: str = "private",
        group_id: str | None = None
    ) -> SubscriptionDTO:
        ...

    async def unsubscribe(self, user_id: int, anime_id: int) -> None:
        ...

    async def pause(self, user_id: int, anime_id: int) -> None:
        ...

    async def resume(self, user_id: int, anime_id: int) -> None:
        ...

    async def list_user_subscriptions(self, user_id: int) -> list[SubscriptionDTO]:
        ...

    async def update_remind_config(
        self,
        subscription_id: int,
        remind_enabled: bool,
        remind_before_minutes: int
    ) -> None:
        ...
```

#### 订阅规则

```text
同一个用户对同一番剧只能有一个 active 订阅
取消追番可以软删除：status = dropped
再次追番时恢复 status = active
```

---

### 2.4 ReminderService：提醒服务

#### 职责

```text
1. 根据番剧播出时间计算下一次提醒时间
2. 扫描即将提醒的订阅
3. 生成提醒消息
4. 调用 QQ 消息发送适配器
5. 写提醒日志，防止重复发送
```

#### 播出时间计算

输入：

```text
anime.weekday
anime.air_time
subscription.remind_before_minutes
user.timezone
```

输出：

```text
next_air_datetime
remind_datetime
remind_key
```

#### 扫描逻辑

```python
async def scan_and_send_reminders(now: datetime):
    subscriptions = find_active_subscriptions()

    for sub in subscriptions:
        next_air = calc_next_air_time(sub.anime, sub.user.timezone)
        remind_at = next_air - timedelta(minutes=sub.remind_before_minutes)

        if now <= remind_at < now + scan_window:
            remind_key = build_remind_key(sub, next_air)

            if not remind_log_exists(sub.id, remind_key):
                message = build_remind_message(sub, next_air)
                send_result = await qq_sender.send(...)
                write_remind_log(...)
```

#### 提醒内容

示例：

```text
《葬送的芙莉莲》即将更新

时间：今天 23:00
观看方式：
1. B站：已绑定链接
2. RSS：下载中 42%
3. 详情：/番 葬送的芙莉莲
```

---

### 2.5 WatchService：观看方式服务

#### 职责

```text
1. 生成 B 站搜索链接
2. 绑定 B 站手动链接
3. 绑定本地观看路径
4. 绑定 RSS 规则
5. 获取某个订阅的观看入口
```

#### 接口设计

```python
class WatchService:
    async def get_watch_options(self, subscription_id: int) -> WatchOptionsDTO:
        ...

    async def bind_bilibili_url(
        self,
        subscription_id: int,
        url: str,
        title: str | None = None
    ) -> WatchBindingDTO:
        ...

    async def create_bilibili_search_binding(
        self,
        subscription_id: int
    ) -> WatchBindingDTO:
        ...

    async def bind_manual_note(
        self,
        subscription_id: int,
        note: str
    ) -> WatchBindingDTO:
        ...
```

#### B 站策略

默认不自动判断哪个视频是正片。

系统只提供：

```text
1. B 站搜索链接
2. 用户手动绑定链接
3. 用户手动更新链接
```

---

### 2.6 RssService：RSS 规则服务

#### 职责

```text
1. 创建 RSS 规则草稿
2. 校验 RSS 规则
3. 提交 qBittorrent 自动下载规则
4. 查询 RSS 匹配记录
5. 查询下载状态
```

#### 接口设计

```python
class RssService:
    async def create_rule_draft(
        self,
        subscription_id: int,
        feed_url: str,
        must_contain: str,
        must_not_contain: str | None,
        save_path: str | None
    ) -> RssRuleDTO:
        ...

    async def activate_rule(self, rss_rule_id: int) -> RssRuleDTO:
        ...

    async def disable_rule(self, rss_rule_id: int) -> None:
        ...

    async def get_rule_status(self, rss_rule_id: int) -> RssRuleStatusDTO:
        ...

    async def list_matches(self, anime_id: int) -> list[RssMatchDTO]:
        ...
```

#### RSS 规则创建流程

```text
用户输入 /绑定rss 番名 RSS链接 关键词
        ↓
后端搜索番剧
        ↓
创建 rss_rule 草稿
        ↓
测试 qB 连接
        ↓
调用 qB 创建 feed/rule
        ↓
status = active
        ↓
创建 watch_binding
```

#### 默认排除词

```text
合集
Batch
BDRip
NCOP
NCED
SP
特典
Preview
PV
CM
```

---

### 2.7 QbitService：qBittorrent 适配器

#### 职责

```text
1. 登录 qB Web API
2. 管理 RSS Feed
3. 管理 RSS 自动下载规则
4. 查询 torrent 状态
5. 查询下载进度
```

#### 接口设计

```python
class QbitService:
    async def test_connection(self) -> bool:
        ...

    async def login(self) -> None:
        ...

    async def add_rss_feed(self, url: str, path: str) -> None:
        ...

    async def set_rss_rule(self, rule_name: str, rule_def: dict) -> None:
        ...

    async def list_torrents(self, category: str | None = None) -> list[QbitTorrentDTO]:
        ...

    async def get_torrent_by_hash(self, hash: str) -> QbitTorrentDTO | None:
        ...
```

#### 配置

```env
QBIT_BASE_URL=http://qbittorrent:8080
QBIT_USERNAME=admin
QBIT_PASSWORD=xxxx
QBIT_DEFAULT_SAVE_PATH=/downloads/anime
```

#### 安全要求

```text
qB WebUI 不暴露公网
只允许 anime-api 内网访问
qB 密码不写死在代码中
所有规则创建都走 RssService 校验
```

---

### 2.8 BotAdapter：QQ Bot 适配层

#### 职责

```text
1. 接收 QQ 消息
2. 解析明确命令
3. 调用 anime-api
4. 格式化回复
5. 发送私聊或群聊消息
```

#### 命令设计

```text
/新番
/新番 2026-04
/周表
/周表 周三
/番 番名
/追番 番名
/弃番 番名
/我的追番
/绑定b站 番名 链接
/绑定rss 番名 RSS链接 关键词
/rss状态 番名
/同步新番
```

#### 权限设计

```text
普通用户：
- 查询新番
- 查询周表
- 查询番剧详情
- 添加自己的追番
- 删除自己的追番
- 绑定自己的观看方式

管理员：
- 手动同步 yuc
- 修改全局 RSS 源
- 查看系统状态
- 触发 qB 连接测试
```

---

## 3. API 设计

### 3.1 获取当前季度

```http
GET /api/seasons/current
```

响应：

```json
{
  "season": "2026-04",
  "title": "2026年4月新番"
}
```

---

### 3.2 获取季度新番

```http
GET /api/seasons/{season}/anime
```

响应：

```json
{
  "season": "2026-04",
  "items": [
    {
      "id": 1,
      "title_cn": "xxx",
      "title_jp": "xxx",
      "weekday": 3,
      "air_time": "22:00",
      "status": "airing"
    }
  ]
}
```

---

### 3.3 获取周表

```http
GET /api/schedule/weekly?season=2026-04
```

响应：

```json
{
  "season": "2026-04",
  "days": [
    {
      "weekday": 1,
      "label": "周一",
      "items": [
        {
          "anime_id": 1,
          "title": "xxx",
          "air_time": "22:00"
        }
      ]
    }
  ]
}
```

---

### 3.4 搜索番剧

```http
GET /api/anime/search?q=芙莉莲&season=2026-04
```

响应：

```json
{
  "query": "芙莉莲",
  "items": [
    {
      "anime_id": 1,
      "title_cn": "葬送的芙莉莲",
      "title_jp": "葬送のフリーレン",
      "score": 0.98
    }
  ]
}
```

---

### 3.5 获取番剧详情

```http
GET /api/anime/{anime_id}
```

---

### 3.6 添加追番

```http
POST /api/subscriptions
```

请求：

```json
{
  "platform": "qq",
  "platform_user_id": "123456",
  "anime_id": 1,
  "remind_before_minutes": 0,
  "remind_channel": "private"
}
```

响应：

```json
{
  "subscription_id": 10,
  "anime_id": 1,
  "status": "active"
}
```

---

### 3.7 取消追番

```http
DELETE /api/subscriptions/{subscription_id}
```

---

### 3.8 查看我的追番

```http
GET /api/users/{user_id}/subscriptions
```

---

### 3.9 绑定 B 站链接

```http
POST /api/watch/bilibili
```

请求：

```json
{
  "subscription_id": 10,
  "url": "https://www.bilibili.com/video/xxx",
  "title": "B站合集"
}
```

---

### 3.10 创建 B 站搜索入口

```http
POST /api/watch/bilibili-search
```

请求：

```json
{
  "subscription_id": 10
}
```

---

### 3.11 创建 RSS 规则草稿

```http
POST /api/rss/rules/draft
```

请求：

```json
{
  "subscription_id": 10,
  "feed_url": "https://example.com/rss.xml",
  "must_contain": "(番名|日文名).*(1080p|1080)",
  "must_not_contain": "(合集|Batch|BDRip|NCOP|NCED)",
  "save_path": "/downloads/anime/番名"
}
```

---

### 3.12 激活 RSS 规则

```http
POST /api/rss/rules/{rule_id}/activate
```

---

### 3.13 查看 RSS 状态

```http
GET /api/rss/status?anime_id=1
```

响应：

```json
{
  "anime_id": 1,
  "rules": [
    {
      "rule_id": 3,
      "status": "active",
      "qbit_rule_name": "anime-1-xxx"
    }
  ],
  "matches": [
    {
      "title": "[字幕组] xxx - 04 [1080p]",
      "episode_no": 4,
      "download_status": "downloading",
      "progress": 0.42
    }
  ]
}
```

---

## 4. 定时任务设计

### 4.1 yuc 同步任务

```text
任务名：sync_yuc_seasons
频率：每天 03:00
逻辑：
1. 获取当前季度
2. 获取下一季度
3. 同步这两个季度
4. 写入同步日志
```

手动触发：

```text
/同步新番
```

---

### 4.2 追番提醒任务

```text
任务名：send_anime_reminders
频率：每 1 分钟或 5 分钟
逻辑：
1. 查询 active subscription
2. 计算提醒时间
3. 判断是否落在当前扫描窗口
4. 检查 remind_log 去重
5. 发送 QQ 消息
6. 写 remind_log
```

---

### 4.3 qB 下载状态任务

```text
任务名：sync_qbit_status
频率：每 3~5 分钟
逻辑：
1. 查询 qB torrent 列表
2. 根据 hash / save_path / title 匹配 rss_match
3. 更新 progress / status
4. 已完成时标记 completed
```

---

## 5. 消息格式设计

### 5.1 /新番

```text
2026年4月新番

周一
22:00 xxx
23:30 yyy

周二
21:00 aaa
22:30 bbb

输入 /番 番名 查看详情
输入 /追番 番名 添加追番
```

---

### 5.2 /番 番名

```text
《xxx》

季度：2026年4月
更新：周三 22:00
状态：连载中
制作：xxx
类型：漫画改 / 奇幻

简介：
......

观看：
B站搜索：https://search.bilibili.com/all?keyword=xxx

操作：
/追番 xxx
/绑定b站 xxx 链接
/绑定rss xxx RSS链接 关键词
```

---

### 5.3 /我的追番

```text
我的追番

1. xxx
   更新：周三 22:00
   观看：B站已绑定

2. yyy
   更新：周五 23:30
   观看：RSS 下载

3. zzz
   更新：周日 21:00
   观看：仅提醒
```

---

### 5.4 更新提醒

```text
《xxx》要更新了

时间：今天 22:00
观看方式：
- B站：已绑定链接
- RSS：下载中 42%

查看详情：/番 xxx
```
