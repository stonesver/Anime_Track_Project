# 05-Agent + Skills 轻量查询层设计

## 1. 背景

在完整追番系统之外，可以增加一个更轻量的查询方案：

```text
用户 / QQ / Web / CLI
        ↓
      Agent
        ↓
  Tool / Skill Router
        ↓
┌──────────────┬──────────────┬──────────────┐
│ yuc_skill    │ bangumi_skill│ anilist_skill│
└──────────────┴──────────────┴──────────────┘
        ↓
   返回结构化结果
        ↓
Agent 汇总、解释、回答
```

这个方案的目标不是替代完整追番系统，而是提供一个低成本、可扩展、面向查询的 Agent 层。

它适合解决：

```text
1. 这季度有什么新番？
2. 周三有什么番？
3. 某部番什么时候更新？
4. 某部番的中文名、日文名、简介是什么？
5. 多个数据源的信息如何合并展示？
6. 某个网站抓取失败时，能否通过大模型生成 Skill 修复建议？
```

它不适合直接承担：

```text
1. 长期追番订阅
2. 定时提醒
3. QQ Bot 主动推送
4. qBittorrent / RSS 持续同步
5. 生产数据库核心写入
6. 下载器管理
```

---

## 2. 与完整追番系统的关系

Agent + Skills 查询层偏向：

```text
查询型
无状态或弱状态
临时抓取
多源聚合
自然语言问答
快速扩展
```

完整追番系统偏向：

```text
状态型
有数据库
有订阅
有提醒
有任务调度
有 qB/RSS 联动
长期运行
```

| 能力 | Agent + Skills 查询层 | 完整追番系统 |
|---|---:|---:|
| 查询新番 | 可以 | 可以 |
| 查询周表 | 可以 | 可以 |
| 多站聚合 | 可以 | 可以 |
| 自然语言问答 | 强 | 需要 LLM 插件 |
| 保存追番 | 弱，需要额外存储 | 强 |
| 定时提醒 | 不适合 | 适合 |
| QQ Bot 主动推送 | 弱 | 强 |
| RSS/qB 持续同步 | 不适合 | 适合 |
| 数据一致性 | 中等 | 高 |
| 开发成本 | 低 | 高 |

推荐定位：

```text
Agent + Skills = 新番查询助手 / 多源检索层 / LLM 工具层
完整追番系统 = 自动化追番平台 / 状态中心 / 调度中心
```

---

## 3. 设计目标

Agent + Skills 查询层需要实现：

```text
1. 通过自然语言查询番剧信息；
2. 支持多个网站或 API 数据源；
3. 每个数据源以 Skill 形式独立维护；
4. Skill 返回统一结构化 JSON；
5. Agent 负责选择 Skill、组合结果、生成回答；
6. 支持缓存，避免频繁抓取源站；
7. 支持 Skill 错误日志与失败样本保存；
8. 支持大模型辅助生成 Skill 修复建议；
9. 不让大模型直接修改生产代码或生产配置；
10. 后续可接入完整追番系统作为数据输入。 
```

---

## 4. 总体架构

```text
┌────────────────────────────┐
│        用户入口              │
│ QQ / Web / CLI / API Client │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│         Agent Service       │
│ 自然语言理解 / 工具编排       │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│        Skill Router         │
│ 选择数据源 / 调用工具 / 合并结果 │
└──────────────┬─────────────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│YucSkill │ │Bangumi  │ │AniList  │
│         │ │Skill    │ │Skill    │
└─────────┘ └─────────┘ └─────────┘
      │        │        │
      ▼        ▼        ▼
┌────────────────────────────┐
│       Skill Runtime         │
│ HTML Runner / API Runner    │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│    Cache / Error Log /      │
│    Skill Config Version     │
└────────────────────────────┘
```

---

## 5. 核心模块

### 5.1 AgentService

职责：

```text
1. 接收自然语言请求；
2. 判断用户意图；
3. 选择需要调用的 Skill；
4. 将用户问题转为结构化工具调用；
5. 汇总多个 Skill 的结果；
6. 生成最终自然语言回答。 
```

示例：

用户输入：

```text
周三晚上有什么新番？
```

Agent 调用：

```text
get_current_season()
yuc_get_weekly_schedule(season="current", weekday=3)
```

返回：

```text
当前季度周三晚上有以下番剧：
1. xxx，22:00
2. yyy，23:30
```

---

### 5.2 SkillRouter

职责：

```text
1. 管理可用 Skills；
2. 根据 Agent 请求路由到对应 Skill；
3. 处理 Skill 超时、失败、降级；
4. 合并多个 Skill 的结果；
5. 返回统一 SkillResult。 
```

示例：

```python
class SkillRouter:
    async def call(self, skill_name: str, operation: str, params: dict) -> SkillResult:
        ...
```

---

### 5.3 SkillRegistry

职责：

```text
1. 注册 Skill；
2. 加载 Skill 配置；
3. 管理 Skill 版本；
4. 禁用不可用 Skill；
5. 查询 Skill 健康状态。 
```

示例目录：

```text
skills/
  yuc.yaml
  bangumi.yaml
  anilist.yaml
```

---

### 5.4 HtmlSkillRunner

用于运行配置化 HTML 抓取 Skill。

职责：

```text
1. 根据配置请求网页；
2. 执行 CSS selector / XPath 解析；
3. 提取字段；
4. 应用 transform；
5. 输出统一 JSON。 
```

适用数据源：

```text
yuc.wiki
其他无稳定 API 的番剧资讯网站
```

---

### 5.5 ApiSkillRunner

用于运行 API 类型 Skill。

职责：

```text
1. 调用第三方 API；
2. 处理鉴权；
3. 处理请求参数；
4. 处理响应字段映射；
5. 输出统一 JSON。 
```

适用数据源：

```text
Bangumi API
AniList GraphQL API
MyAnimeList / Jikan API
其他结构化 API
```

---

### 5.6 CacheService

职责：

```text
1. 缓存 Skill 结果；
2. 降低源站请求频率；
3. 减少 LLM 与网络开销；
4. 在源站临时不可用时返回过期但可用的数据；
5. 支持不同 Skill / Operation 的 TTL。 
```

推荐缓存策略：

```text
yuc 当前季度页面：缓存 6 小时
Bangumi 搜索结果：缓存 1 天
AniList 搜索结果：缓存 1 天
番剧详情：缓存 1 天到 7 天
```

---

### 5.7 SkillErrorLogService

职责：

```text
1. 记录 Skill 调用失败；
2. 保存失败 URL、状态码、错误类型；
3. 保存解析失败样本；
4. 提供给大模型进行诊断；
5. 支持后续生成修复建议。 
```

---

## 6. Skill 设计原则

### 6.1 Skill 是确定性工具

推荐：

```text
Skill 由代码或配置执行确定性抓取/请求；
Agent 只负责选择和组合 Skill；
大模型不直接解析大段原始 HTML。 
```

不推荐：

```text
让大模型直接打开网页，阅读 HTML，然后自己总结。
```

原因：

```text
1. HTML 长，消耗 token；
2. 解析结果不稳定；
3. 容易漏项；
4. 不方便缓存；
5. 不方便测试；
6. 不方便定位错误。 
```

---

### 6.2 Skill 输出必须统一 Schema

不同网站字段不同，但对 Agent 输出应统一。

示例：

```python
class AnimeItem(BaseModel):
    source: str
    external_id: str | None = None
    external_url: str | None = None

    season: str | None = None
    title_cn: str | None = None
    title_jp: str | None = None
    title_en: str | None = None
    aliases: list[str] = []

    weekday: int | None = None
    air_time: str | None = None
    start_date: str | None = None
    timezone: str | None = None

    description: str | None = None
    cover_url: str | None = None
    official_url: str | None = None

    confidence: float = 1.0
```

周表结构：

```python
class WeeklySchedule(BaseModel):
    source: str
    season: str
    days: list[ScheduleDay]

class ScheduleDay(BaseModel):
    weekday: int
    label: str
    items: list[AnimeItem]
```

Skill 返回包装结构：

```python
class SkillResult(BaseModel):
    ok: bool
    source: str
    operation: str
    data: Any | None = None
    error_type: str | None = None
    error_message: str | None = None
    freshness: str | None = None
    cached: bool = False
```

---

## 7. Skill 类型

### 7.1 稳定 API Skill

适合：

```text
Bangumi
AniList
MyAnimeList / Jikan
其他有稳定 API 的数据源
```

特点：

```text
1. 代码型实现；
2. 响应结构较稳定；
3. 适合做搜索、详情、封面、别名补充；
4. 大模型一般只需要辅助诊断，不需要频繁维护。 
```

示例：

```python
async def bangumi_search_subject(query: str) -> SkillResult:
    ...
```

---

### 7.2 可配置网页抓取 Skill

适合：

```text
yuc.wiki
其他没有稳定 API 的网页数据源
```

特点：

```text
1. 容易受页面结构变化影响；
2. 建议配置化；
3. 大模型可以辅助生成配置修复建议；
4. 需要缓存和错误日志。 
```

示例配置：

```yaml
name: yuc
type: html
description: yuc.wiki 新番表数据源

operations:
  get_season_schedule:
    url: "https://yuc.wiki/{season_compact}"
    method: GET
    parse:
      type: html
      day_blocks:
        selector: ".weekday-block"
        fields:
          weekday:
            selector: ".weekday-title"
            transform: weekday_text_to_int
          items:
            selector: ".anime-item"
            multiple: true
            fields:
              title:
                selector: ".anime-title"
                attr: text
              air_time:
                selector: ".air-time"
                attr: text
              detail_url:
                selector: "a"
                attr: href
```

---

## 8. 推荐 Tool / Skill 列表

### 8.1 yuc_get_current_season

用途：获取当前季度。

```yaml
name: yuc_get_current_season
description: 获取 yuc.wiki 当前季度新番季度标识，例如 2026-04。
input_schema:
  type: object
  properties: {}
```

---

### 8.2 yuc_get_weekly_schedule

用途：获取指定季度周表。

```yaml
name: yuc_get_weekly_schedule
description: 获取指定季度的新番周表，适合回答“周几有什么番”。
input_schema:
  type: object
  properties:
    season:
      type: string
      description: 季度，例如 2026-04；也可以传 current。
    weekday:
      type: integer
      description: 1 到 7，周一到周日。可选。
```

---

### 8.3 yuc_search_anime

用途：在 yuc 数据中搜索番剧。

```yaml
name: yuc_search_anime
description: 在 yuc 数据中搜索番剧。
input_schema:
  type: object
  properties:
    query:
      type: string
```

---

### 8.4 bangumi_search_subject

用途：在 Bangumi 中搜索番剧条目。

```yaml
name: bangumi_search_subject
description: 在 Bangumi 中搜索番剧条目，适合查中文名、别名、简介。
input_schema:
  type: object
  properties:
    query:
      type: string
```

---

### 8.5 anilist_search_anime

用途：在 AniList 中搜索动画条目。

```yaml
name: anilist_search_anime
description: 在 AniList 中搜索动画条目，适合查英文名、封面、国际播出信息。
input_schema:
  type: object
  properties:
    query:
      type: string
```

---

## 9. 查询流程示例

### 9.1 查询当前季度新番

用户：

```text
这季度有什么新番？
```

流程：

```text
Agent 判断意图：查询当前季度新番
  ↓
调用 yuc_get_current_season
  ↓
调用 yuc_get_weekly_schedule(season=current)
  ↓
Agent 整理为按星期分组的回答
```

---

### 9.2 查询周三番剧

用户：

```text
周三晚上有什么番？
```

流程：

```text
Agent 判断 weekday = 3，time_range = evening
  ↓
调用 yuc_get_weekly_schedule(season=current, weekday=3)
  ↓
过滤晚上时段
  ↓
生成回答
```

---

### 9.3 查询番剧详情

用户：

```text
尖帽子的魔法工坊什么时候更新？
```

流程：

```text
调用 yuc_search_anime(query)
  ↓
找到候选番剧
  ↓
调用 yuc_get_anime_detail 或读取 schedule 详情
  ↓
必要时调用 bangumi_search_subject 补充别名/简介
  ↓
回答更新时间、标题、简介
```

---

### 9.4 多源聚合查询

用户：

```text
帮我查一下这部番的中文名、日文名、播出时间和简介。
```

流程：

```text
调用 yuc_search_anime：播出时间、周表
调用 bangumi_search_subject：中文名、别名、简介
调用 anilist_search_anime：英文名、封面、国际信息
  ↓
Agent 合并结果
  ↓
说明不同来源可能存在差异
```

---

## 10. 缓存设计

即使是轻量查询层，也建议使用 SQLite 做缓存。

缓存表：

```sql
CREATE TABLE skill_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    response_json TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    UNIQUE(skill_name, operation, cache_key)
);
```

缓存 key 示例：

```text
yuc:get_weekly_schedule:2026-04:all
yuc:get_weekly_schedule:2026-04:3
bangumi:search:尖帽子的魔法工坊
anilist:search:witch-hat-atelier
```

缓存策略：

```text
1. 查询前先查缓存；
2. 缓存未过期则直接返回；
3. 缓存过期则请求源站；
4. 源站失败时，可返回过期缓存并标记 stale；
5. Agent 回答时说明数据可能不是最新。 
```

---

## 11. 错误处理设计

Skill 调用失败时，不应该直接让 Agent 幻觉补答案。

应返回结构化错误：

```json
{
  "ok": false,
  "source": "yuc",
  "operation": "get_weekly_schedule",
  "error_type": "parse_zero_items",
  "error_message": "HTML returned 200 but no schedule items were parsed",
  "cached": false
}
```

Agent 应根据错误类型处理：

```text
network_timeout        → 建议稍后重试，可使用缓存
http_429_rate_limited  → 说明源站限流，可使用缓存
http_403_blocked       → 说明可能被风控，不尝试绕过
parse_zero_items       → 说明抓取规则可能失效
parse_schema_changed   → 说明页面结构可能变化
```

---

## 12. Skill 错误日志

建议记录：

```sql
CREATE TABLE skill_error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    params_json TEXT,
    error_type TEXT,
    error_message TEXT,
    raw_snapshot_path TEXT,
    created_at DATETIME NOT NULL
);
```

用途：

```text
1. 排查 Skill 失败；
2. 提供给大模型诊断；
3. 判断是否源站结构变化；
4. 生成修复建议；
5. 回归测试。 
```

---

## 13. 大模型维护 Skill 的边界

可以让大模型辅助维护 Skill，但不建议让它直接修改生产环境。

推荐分级：

### Level 1：错误解释

```text
Skill 报错
  ↓
大模型分析错误日志
  ↓
输出可能原因
```

---

### Level 2：生成修复建议

```text
大模型读取失败样本、旧配置、错误信息
  ↓
生成新的 selector 建议
  ↓
输出修复报告
```

---

### Level 3：生成候选配置

如果网页抓取 Skill 是 YAML 配置化的，大模型可以生成 candidate 配置。

```text
旧 yuc.yaml
失败 HTML 样本
解析错误
  ↓
LLM
  ↓
yuc.candidate.yaml
```

---

### Level 4：沙箱测试后人工确认

```text
candidate 配置
  ↓
沙箱执行
  ↓
验证输出 schema
  ↓
与历史结果做质量对比
  ↓
测试通过
  ↓
人工确认
  ↓
启用新版本
```

---

### 不推荐：自动改代码并上线

不建议：

```text
模型直接修改生产代码
模型直接覆盖 active Skill 配置
模型直接重启服务
模型直接部署
```

原因：

```text
1. 容易误判；
2. 可能破坏已有功能；
3. 有安全风险；
4. 难以审计；
5. 不适合生产环境。 
```

---

## 14. Skill 配置版本管理

建议每个 Skill 配置有版本。

目录示例：

```text
skills/
  yuc/
    v1.yaml
    v2.yaml
    current.yaml
  bangumi/
    v1.yaml
    current.yaml
```

数据库表：

```sql
CREATE TABLE skill_config_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    version TEXT NOT NULL,
    config_text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at DATETIME NOT NULL
);
```

状态：

```text
active
candidate
disabled
failed
```

启用流程：

```text
生成 candidate
  ↓
沙箱测试
  ↓
人工确认
  ↓
active
```

---

## 15. 安全边界

Agent 与大模型不应该拥有以下权限：

```text
1. 服务器 shell；
2. .env 读取权限；
3. qBittorrent 管理权限；
4. 生产数据库任意写权限；
5. QQ 群发权限；
6. 文件系统任意写权限；
7. 生产 Skill 直接覆盖权限；
8. 自动部署权限。 
```

可以允许：

```text
1. 读取 Skill 错误日志；
2. 读取脱敏失败样本；
3. 创建 candidate Skill 配置；
4. 调用沙箱测试接口；
5. 生成修复报告；
6. 调用查询类 Skill。 
```

---

## 16. 与完整追番系统的集成方式

未来完整追番系统可以复用 Agent + Skills 层作为数据输入。

```text
Agent + Skills
      ↓
结构化新番数据
      ↓
AnimeIngestService
      ↓
统一番剧数据库
      ↓
追番 / 提醒 / RSS / qB / QQ Bot
```

也可以并行存在：

```text
查询类请求 → Agent + Skills
订阅/提醒/RSS → Core Anime System
```

例如：

```text
“这季度有什么新番？” → Agent 查询层
“帮我追这部番” → Core 系统
“今晚有什么番？” → Core 系统优先，Agent 可补充外部详情
“帮我生成 RSS 规则” → Agent 生成草稿，Core 负责确认和执行
```

---

## 17. MVP 实现范围

第一版可以只做：

```text
1. Agent API；
2. yuc Skill；
3. Bangumi Skill，可选；
4. SQLite 缓存；
5. Skill 错误日志；
6. 查询当前季度；
7. 查询周表；
8. 查询番剧详情；
9. 简单自然语言转工具调用。 
```

暂不做：

```text
1. 自动提醒；
2. 追番订阅；
3. qB 自动下载；
4. QQ 主动推送；
5. 自动修复并上线。 
```

---

## 18. 推荐实现目录

```text
agent_app/
  main.py
  config.py

  agent/
    agent_service.py
    prompt.py
    tool_planner.py

  skills/
    registry.py
    router.py
    schema.py
    html_runner.py
    api_runner.py

  skill_configs/
    yuc.yaml
    bangumi.yaml
    anilist.yaml

  services/
    cache_service.py
    error_log_service.py
    skill_repair_service.py

  models/
    skill_cache.py
    skill_error_log.py
    skill_config_version.py

  api/
    routes_chat.py
    routes_tools.py
    routes_skill_health.py
```

---

## 19. 最终结论

Agent + Skills 方案可以实现简单查询功能，并且适合作为轻量原型或独立查询层。

推荐原则：

```text
Skill 负责确定性抓取；
Agent 负责自然语言理解和工具编排；
LLM 负责失败诊断和候选修复；
缓存负责减少源站压力；
生产状态和危险操作仍交给核心系统。 
```

这个方案最适合先做：

```text
新番查询助手
多源聚合查询
可配置抓取 Skill
大模型辅助维护 Skill
```

不建议直接用它替代：

```text
追番订阅
定时提醒
RSS/qB 自动化
QQ Bot 主动推送
```

最终可以形成两层架构：

```text
第一层：Anime Agent 查询层
- Skills 抓取 yuc/Bangumi/AniList
- 自然语言查询
- 缓存
- Skill 半自动维护

第二层：Anime Core 系统
- 订阅
- 提醒
- RSS/qB
- 数据库
- QQ Bot
```

这样既能快速实现轻量查询能力，也能为后续完整追番系统保留扩展空间。
