# OpenClaw / MiniMax 大模型插件化概要设计

## 1. 设计定位

大模型部分可以像插件一样外挂。

推荐关系：

```text
OpenClaw + MiniMax
      ↓
受控 Skill API
      ↓
anime-api
      ↓
核心业务系统
```

OpenClaw 不需要知道数据库结构，也不应该直连数据库。

核心系统只需要提供一组稳定、受控、权限明确的 Skill / Tool API，让 OpenClaw 调用。

---

## 2. 大模型层职责

大模型层负责：

```text
1. 自然语言理解
2. 模糊找番
3. 生成 RSS 规则草稿
4. 生成别名建议
5. 推荐番剧
6. 总结今晚有什么番
7. 将复杂用户意图拆解成多个 API 调用
```

不负责：

```text
1. 定时提醒
2. 数据库写入
3. qBittorrent 直接操作
4. yuc.wiki 抓取
5. QQ 消息发送
6. 权限判断
7. 删除/批量操作的最终决策
```

---

## 3. Skill API 设计原则

给 OpenClaw 暴露单独的 `/api/tools/*` 接口。

这些接口和普通业务 API 的区别是：

```text
1. 权限更严格
2. 返回结构更适合 LLM 理解
3. 对危险动作采用草稿/确认机制
4. 所有调用记录审计日志
```

---

## 4. 推荐 Skill 列表

### 4.1 search_anime

用途：搜索番剧。

```http
POST /api/tools/search_anime
```

请求：

```json
{
  "query": "自动贩卖机",
  "season": "current",
  "limit": 5
}
```

响应：

```json
{
  "items": [
    {
      "anime_id": 1,
      "title_cn": "转生成自动贩卖机的我今天也在迷宫徘徊",
      "title_jp": "...",
      "season": "2026-04",
      "weekday": 3,
      "air_time": "22:00",
      "confidence": 0.93
    }
  ]
}
```

---

### 4.2 get_weekly_schedule

用途：查询周表。

```http
POST /api/tools/get_weekly_schedule
```

请求：

```json
{
  "season": "current",
  "weekday": "周三",
  "time_range": "evening"
}
```

---

### 4.3 get_anime_detail

用途：获取番剧详情。

```http
POST /api/tools/get_anime_detail
```

请求：

```json
{
  "anime_id": 1
}
```

---

### 4.4 create_subscription

用途：添加追番。

```http
POST /api/tools/create_subscription
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

这个接口属于写操作，但风险较低，可以允许直接执行。

---

### 4.5 propose_rss_rule

用途：生成 RSS 规则草稿。

```http
POST /api/tools/propose_rss_rule
```

请求：

```json
{
  "anime_id": 1,
  "preference": {
    "quality": "1080p",
    "subtitle": "简体",
    "exclude": ["合集", "BDRip", "繁体"]
  }
}
```

响应：

```json
{
  "anime_id": 1,
  "proposal": {
    "must_contain": "(番名|日文名|英文名).*(1080p|1080)",
    "must_not_contain": "(合集|Batch|BDRip|CHT|繁体|繁中)",
    "use_regex": true,
    "smart_filter": true
  },
  "requires_confirmation": true
}
```

注意：这个接口只生成草稿，不创建 qB 规则。

---

### 4.6 create_rss_rule_after_confirm

用途：用户确认后创建 RSS 规则。

```http
POST /api/tools/create_rss_rule_after_confirm
```

请求：

```json
{
  "subscription_id": 10,
  "feed_url": "https://example.com/rss.xml",
  "must_contain": "(xxx|yyy).*(1080p|1080)",
  "must_not_contain": "(合集|Batch|BDRip)",
  "confirmation_token": "abc123"
}
```

该接口必须要求确认 token。

---

### 4.7 get_user_subscriptions

用途：查询用户追番。

```http
POST /api/tools/get_user_subscriptions
```

请求：

```json
{
  "platform": "qq",
  "platform_user_id": "123456"
}
```

---

### 4.8 get_tonight_schedule

用途：查询今晚有什么番。

```http
POST /api/tools/get_tonight_schedule
```

请求：

```json
{
  "platform": "qq",
  "platform_user_id": "123456",
  "timezone": "Asia/Shanghai"
}
```

---

## 5. 大模型调用安全设计

### 5.1 最小权限

OpenClaw 只拿一个专用 API Key：

```env
OPENCLAW_SKILL_API_KEY=xxx
```

这个 key 只能访问：

```text
/api/tools/*
```

不能访问：

```text
/admin/*
/internal/*
/debug/*
数据库
qB WebUI
服务器 shell
文件系统
```

---

### 5.2 危险操作必须二次确认

危险操作包括：

```text
创建 RSS 自动下载规则
批量追番
取消多个追番
删除订阅
修改 qB 下载路径
删除 qB 任务
群发提醒
```

流程：

```text
用户自然语言请求
  ↓
OpenClaw 调 propose_* 接口
  ↓
核心系统返回草稿 + confirmation_token
  ↓
OpenClaw 展示给用户
  ↓
用户回复“确认”
  ↓
OpenClaw 调 *_after_confirm 接口
  ↓
核心系统校验 token 后执行
```

---

### 5.3 confirmation_token 设计

```sql
CREATE TABLE confirmation_token (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    used BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
);
```

规则：

```text
有效期 5~10 分钟
只能使用一次
绑定 user_id
绑定 action
绑定 payload
```

---

### 5.4 审计日志

所有 OpenClaw 调用都记录：

```sql
CREATE TABLE tool_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    user_id INTEGER,
    request_json TEXT,
    response_json TEXT,
    status TEXT,
    error TEXT,
    created_at DATETIME NOT NULL
);
```

用途：

```text
1. 排查误操作
2. 观察 LLM 调用质量
3. 审计危险操作
4. 防止滥用
```

---

### 5.5 Prompt Injection 防护

核心原则：

```text
模型说什么都不能绕过后端权限。
```

具体措施：

```text
1. OpenClaw 不能直连数据库
2. OpenClaw 不能直连 qB
3. OpenClaw 不能执行 shell
4. Tool API 不接受任意 SQL / 任意 URL / 任意命令
5. Tool API 对参数做白名单校验
6. 所有写操作都检查当前用户权限
7. 危险操作必须 confirmation_token
```

---

## 6. OpenClaw Skill 配置示例

概念上可以这样配置：

```yaml
skills:
  - name: search_anime
    description: 搜索番剧，支持中文名、日文名、英文名、简称和别名。
    endpoint: http://anime-api:8000/api/tools/search_anime
    method: POST
    auth:
      type: bearer
      token_env: OPENCLAW_SKILL_API_KEY

  - name: get_weekly_schedule
    description: 查询当前季度或指定季度的番剧周表。
    endpoint: http://anime-api:8000/api/tools/get_weekly_schedule
    method: POST
    auth:
      type: bearer
      token_env: OPENCLAW_SKILL_API_KEY

  - name: create_subscription
    description: 为当前 QQ 用户添加追番订阅。
    endpoint: http://anime-api:8000/api/tools/create_subscription
    method: POST
    auth:
      type: bearer
      token_env: OPENCLAW_SKILL_API_KEY

  - name: propose_rss_rule
    description: 根据番剧信息和用户偏好生成 RSS 规则草稿，不会直接创建下载任务。
    endpoint: http://anime-api:8000/api/tools/propose_rss_rule
    method: POST
    auth:
      type: bearer
      token_env: OPENCLAW_SKILL_API_KEY

  - name: create_rss_rule_after_confirm
    description: 用户确认后创建 RSS 自动下载规则。
    endpoint: http://anime-api:8000/api/tools/create_rss_rule_after_confirm
    method: POST
    auth:
      type: bearer
      token_env: OPENCLAW_SKILL_API_KEY
```

---

## 7. 推荐接入方式

### 7.1 普通命令走代码

```text
/新番
/周表
/追番
/我的追番
/rss状态
```

这些直接由 QQ Bot 调核心 API。

---

### 7.2 自然语言走 OpenClaw

```text
帮我追这季度所有周五更新的番
我想找几部轻松搞笑的
给这部番配一个 RSS 下载规则
今晚有什么能看
这个 RSS 标题对应哪部番
```

---

### 7.3 需要确认的动作

```text
创建 RSS 规则
批量追番
删除订阅
改 qB 下载路径
```

---

### 7.4 不给 OpenClaw 的权限

```text
服务器 shell
数据库直连
qB 管理密码
文件系统写权限
公网管理入口
```

---

## 8. 最终结论

大模型部分应该是：

```text
可选插件层 / 智能交互层 / Tool 调用层
```

核心系统只需要提供受控 Skill：

```text
search_anime
get_anime_detail
get_weekly_schedule
create_subscription
get_user_subscriptions
propose_rss_rule
create_rss_rule_after_confirm
get_rss_status
```

同时做好：

```text
API Key 鉴权
最小权限
危险操作二次确认
参数白名单
审计日志
不暴露数据库
不暴露 qB 管理权限
不暴露服务器 shell
```

这样整体系统会比较稳：

```text
确定性业务：代码实现
模糊理解：大模型实现
危险动作：后端确认
长期运行：Worker 保证
QQ/Web：只是入口
```
