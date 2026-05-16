# V1 MVP 总览：yuc 能力与 Skill 创建分离

## 1. 目标

V1 的目标是实现最小可用的番剧查询能力，但 yuc 能力和本地 Skill / Tool 创建必须分开。

拆分原则：

- yuc 能力是底层确定性代码，负责请求、解析、标准化和错误处理。
- Skill / Tool 是 Agent 调用包装层，只负责暴露工具入口和描述输入输出。
- Skill / Tool 不应重复实现 yuc 页面解析逻辑。

V1 只解决查询，不解决长期状态管理。

## 2. 实现范围

V1 分成两个独立计划：

1. `plan/v1-yuc-capability.md`：只描述 yuc 能力实现；
2. `plan/v1-agent-skill.md`：只描述本地 Agent Skill / Tool 创建。

V1 总体只实现：

1. 数据模型与标准化；
2. yuc 网页抓取；
3. 本地 Agent Skill / Tool 包装。

V1 不实现：

1. 数据库；
2. 缓存；
3. 后台同步；
4. HTTP API；
5. 用户订阅；
6. 提醒；
7. QQ Bot；
8. RSS/qB 下载。

## 3. 目标能力

V1 应支持以下查询：

1. 查询当前季度新番；
2. 查询指定季度周表；
3. 按星期查询番剧；
4. 搜索番剧；
5. 查询番剧基础详情。

示例问题：

```text
这季度有什么新番？
周三有什么番？
2026 年 4 月新番有哪些？
某部番什么时候更新？
这部番的基础信息是什么？
```

## 4. 核心模块

### 4.1 V1-A：yuc 能力实现

详见 `plan/v1-yuc-capability.md`。

该部分负责：

- 数据模型与标准化；
- yuc 页面请求；
- 当前季度识别；
- 周表解析；
- 番剧搜索；
- 番剧基础详情解析；
- 结构化错误返回。

### 4.2 V1-B：本地 Agent Skill / Tool 创建

详见 `plan/v1-agent-skill.md`。

该部分负责：

- 定义本地 Skill / Tool 的触发说明；
- 定义工具名称；
- 定义工具输入输出；
- 调用 V1-A 已有 yuc 能力；
- 向 Agent 返回结构化结果。

### 4.3 统一数据模型

职责：

- 定义 Agent 和后续 API 都能复用的统一输出结构；
- 标准化季度格式；
- 标准化星期；
- 标准化播出时间；
- 标准化标题字段；
- 保留来源 URL，便于追踪数据来源。

建议统一使用以下结构。

### `AnimeItem`

```json
{
  "source": "yuc",
  "external_id": "string or null",
  "external_url": "string or null",
  "season": "2026-04",
  "title_cn": "string or null",
  "title_jp": "string or null",
  "title_en": "string or null",
  "aliases": [],
  "weekday": 3,
  "air_time": "22:00",
  "start_date": "2026-04-01",
  "timezone": "Asia/Shanghai",
  "description": "string or null",
  "cover_url": "string or null",
  "official_url": "string or null",
  "confidence": 1.0
}
```

字段要求：

- `source` 固定为 `yuc`；
- `season` 使用 `YYYY-MM`；
- `weekday` 使用 `1` 到 `7`，表示周一到周日；
- `air_time` 使用 `HH:mm`；
- 缺失字段返回 `null` 或空数组，不编造。

### `ScheduleDay`

```json
{
  "weekday": 3,
  "label": "周三",
  "items": []
}
```

### `WeeklySchedule`

```json
{
  "source": "yuc",
  "season": "2026-04",
  "days": []
}
```

### `SkillResult`

```json
{
  "ok": true,
  "source": "yuc",
  "operation": "yuc_get_weekly_schedule",
  "data": {},
  "error_type": null,
  "error_message": null,
  "freshness": "live",
  "cached": false
}
```

失败时：

```json
{
  "ok": false,
  "source": "yuc",
  "operation": "yuc_get_weekly_schedule",
  "data": null,
  "error_type": "parse_zero_items",
  "error_message": "HTML returned 200 but no schedule items were parsed",
  "freshness": null,
  "cached": false
}
```

### 4.4 yuc 网页抓取

职责：

- 请求 yuc 首页或季度页面；
- 判断当前季度；
- 抓取指定季度页面；
- 解析番剧周表；
- 解析番剧基础字段；
- 支持按标题搜索；
- 支持查询番剧基础详情。

输入约定：

- `season` 支持 `current` 或 `YYYY-MM`；
- `weekday` 支持 `1` 到 `7`；
- `query` 为用户输入的番名或别名；
- `limit` 默认 `5`。

输出约定：

- 所有输出必须是结构化 JSON；
- 不向 Agent 暴露原始 HTML；
- 页面字段缺失时保留 `null`；
- 页面结构变化时返回结构化错误。

### 4.5 本地 Agent Skill / Tool

V1 提供以下本地工具。

#### `yuc_get_current_season`

用途：获取 yuc 当前季度标识。

输入：

```json
{}
```

输出：

```json
{
  "ok": true,
  "source": "yuc",
  "operation": "yuc_get_current_season",
  "data": {
    "season": "2026-04"
  },
  "error_type": null,
  "error_message": null,
  "freshness": "live",
  "cached": false
}
```

#### `yuc_get_weekly_schedule`

用途：查询指定季度的周表，可选按星期过滤。

输入：

```json
{
  "season": "current",
  "weekday": 3
}
```

输出：`SkillResult.data` 为 `WeeklySchedule`。

#### `yuc_search_anime`

用途：在 yuc 数据中搜索番剧。

输入：

```json
{
  "query": "番名",
  "season": "current",
  "limit": 5
}
```

输出：`SkillResult.data.items` 为 `AnimeItem[]`。

匹配策略：

1. 标题精确匹配；
2. 标题包含匹配；
3. 简单归一化后匹配。

V1 不做向量搜索，不接大模型判断匹配。

#### `yuc_get_anime_detail`

用途：查询番剧基础详情。

输入：

```json
{
  "query": "番名",
  "season": "current"
}
```

输出：`SkillResult.data` 为单个 `AnimeItem` 或候选列表。

如果无法唯一匹配，返回候选列表，不让 Agent 自行假定是哪一部。

## 5. 错误处理

V1 至少需要处理以下错误：

| 错误类型 | 含义 | 处理方式 |
|---|---|---|
| `network_timeout` | 请求超时 | 返回失败结果，提示稍后重试 |
| `network_error` | 网络连接失败 | 返回失败结果，不编造数据 |
| `http_error` | 源站返回非 2xx | 返回状态码信息 |
| `source_unavailable` | 源站不可用 | 返回失败结果 |
| `invalid_params` | 参数非法 | 返回字段级错误说明 |
| `parse_zero_items` | 页面返回成功但解析为空 | 提示可能是页面结构变化 |
| `parse_schema_changed` | 关键选择器失效 | 提示需要更新解析规则 |
| `ambiguous_match` | 搜索结果无法唯一确定 | 返回候选列表 |
| `not_found` | 未找到匹配番剧 | 返回空结果 |

失败原则：

- 不输出推测的番剧信息；
- 不把原始 HTML 直接交给 Agent；
- 不吞掉错误；
- 错误结果仍使用 `SkillResult` 包装。

## 6. 测试计划

### 6.1 HTML 样本解析测试

使用固定 yuc HTML 样本测试：

- 能解析季度信息；
- 能解析周表分组；
- 能解析番剧标题；
- 能解析星期；
- 能解析播出时间；
- 字段缺失时返回 `null`。

### 6.2 当前季度识别测试

测试：

- 能从 yuc 页面识别当前季度；
- 返回格式为 `YYYY-MM`；
- 当前季度无法识别时返回结构化错误。

### 6.3 周表解析测试

测试：

- 查询完整周表；
- 按 weekday 过滤；
- weekday 非法时返回 `invalid_params`；
- 某天无番剧时返回空 `items`，不是失败。

### 6.4 搜索匹配测试

测试：

- 精确标题匹配；
- 包含匹配；
- 简单归一化匹配；
- 无结果返回 `not_found` 或空数组；
- 多候选时返回候选列表。

### 6.5 详情字段缺失测试

测试：

- 缺少简介；
- 缺少封面；
- 缺少官方链接；
- 缺少播出时间。

要求：

- 缺失字段返回 `null`；
- 不使用占位假数据。

### 6.6 失败路径测试

测试：

- 网络失败；
- 请求超时；
- HTTP 非 2xx；
- HTML 结构变化；
- 页面成功但解析结果为空。

要求：

- 每类失败返回明确 `error_type`；
- `ok` 为 `false`；
- `data` 为 `null` 或明确的空结果；
- Agent 不需要读取异常堆栈即可理解失败原因。

## 7. 验收标准

V1 完成时必须满足：

1. Agent 能通过本地 Skill 查询 yuc 数据；
2. 能返回当前季度；
3. 能返回指定季度周表；
4. 能按星期查询番剧；
5. 能按标题搜索番剧；
6. 能返回番剧基础详情；
7. 返回值是结构化 JSON；
8. 不暴露原始 HTML 给 Agent；
9. 不依赖数据库；
10. 不依赖服务常驻；
11. 出错时返回结构化错误；
12. 出错时不生成幻觉结果。

## 8. 后续扩展点

V1 完成后，优先扩展顺序：

1. 查询 API；
2. SQLite 缓存；
3. 本地番剧库；
4. 后台同步；
5. 订阅；
6. 提醒；
7. QQ Bot；
8. RSS/qB。

V1 的模型和工具命名应尽量保持稳定，后续 HTTP API 和数据库版本复用同一套结构。
