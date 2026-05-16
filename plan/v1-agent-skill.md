# V1-B：本地 Agent Skill / Tool 创建计划

## 1. 目标

本计划只描述本地 Agent Skill / Tool 的创建。它是 yuc 能力的包装层，让 Agent 可以调用已经实现好的 yuc 查询能力。

本模块不实现 yuc 页面请求和解析逻辑。

## 2. 前置依赖

必须先完成 `plan/v1-yuc-capability.md` 中定义的 yuc 能力。

Skill / Tool 只调用这些底层能力：

1. `get_current_season`;
2. `get_weekly_schedule`;
3. `search_anime`;
4. `get_anime_detail`.

## 3. 实现范围

只实现：

1. 本地 Skill 的描述与触发边界；
2. Agent 可调用的工具名称；
3. 工具输入参数；
4. 工具输出结构；
5. 工具到 yuc 能力的调用映射；
6. 面向 Agent 的错误说明。

不实现：

1. yuc 网页请求；
2. yuc HTML 解析；
3. 数据库；
4. 缓存；
5. HTTP API；
6. 订阅；
7. 提醒；
8. QQ Bot；
9. RSS/qB。

## 4. Tool 列表

### `yuc_get_current_season`

用途：获取 yuc 当前季度标识。

调用底层能力：`get_current_season`。

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

### `yuc_get_weekly_schedule`

用途：查询指定季度周表，可选按星期过滤。

调用底层能力：`get_weekly_schedule`。

输入：

```json
{
  "season": "current",
  "weekday": 3
}
```

输出：`SkillResult.data` 为 `WeeklySchedule`。

### `yuc_search_anime`

用途：搜索番剧。

调用底层能力：`search_anime`。

输入：

```json
{
  "query": "番名",
  "season": "current",
  "limit": 5
}
```

输出：`SkillResult.data.items` 为 `AnimeItem[]`。

### `yuc_get_anime_detail`

用途：查询番剧基础详情。

调用底层能力：`get_anime_detail`。

输入：

```json
{
  "query": "番名",
  "season": "current"
}
```

输出：`SkillResult.data` 为单个 `AnimeItem` 或候选列表。

## 5. SkillResult 包装

Skill / Tool 层统一使用 `SkillResult` 包装底层返回值。

```json
{
  "ok": true,
  "source": "yuc",
  "operation": "yuc_search_anime",
  "data": {},
  "error_type": null,
  "error_message": null,
  "freshness": "live",
  "cached": false
}
```

包装规则：

- `operation` 使用 Tool 名称；
- `source` 固定为 `yuc`；
- `cached` 在 V1 固定为 `false`；
- 底层 yuc 错误直接映射为 `error_type` 和 `error_message`；
- 不向 Agent 返回原始 HTML。

## 6. Agent 行为边界

Agent 可以：

- 调用 Tool 查询番剧；
- 对结构化结果进行自然语言总结；
- 在多候选时向用户确认；
- 在失败时说明错误原因。

Agent 不可以：

- 直接抓取 yuc 页面；
- 直接解析 HTML；
- 猜测缺失字段；
- 写数据库；
- 创建订阅；
- 发送 QQ 消息；
- 操作 RSS/qB。

## 7. 测试计划

1. 使用 mock yuc 能力测试 Tool 输入输出；
2. 测试每个 Tool 都调用正确底层能力；
3. 测试底层成功结果被正确包装为 `SkillResult`；
4. 测试底层失败结果被正确映射到 Agent 可读错误；
5. 测试 `cached` 在 V1 固定为 `false`；
6. 测试 Tool 不返回原始 HTML；
7. 测试多候选结果不会被 Skill 层强行选中。

## 8. 验收标准

1. Agent 能调用本地 Tool；
2. Tool 能复用 yuc 能力；
3. Tool 不包含 yuc HTML 解析逻辑；
4. Tool 返回结构化 `SkillResult`；
5. Tool 失败时返回明确错误；
6. Tool 不依赖数据库；
7. Tool 不依赖服务常驻；
8. Tool 不承担订阅、提醒、QQ、RSS/qB 职责。
