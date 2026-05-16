# 番剧解析与标准化模块详设

## 1. 设计目标

`anime-parser` 是外部数据源无关的纯解析与标准化库。它接收 yuc、Bangumi、AniList 或其他来源适配器产出的源记录，输出统一模型，供后续 API、Skill、缓存和数据库复用。

本模块必须保持以下边界：

1. 不请求网络；
2. 不解析具体站点 DOM；
3. 不依赖数据库或 ORM；
4. 不依赖 Web 框架；
5. 不处理用户订阅、提醒、下载或 Bot 逻辑。

实现形态优先采用 Python 包。后续如果需要服务端接口，由 API 层 import 本包并暴露 HTTP；如果需要 Skill 使用，由 Skill Tool import 本包并把结果转 JSON；如果需要数据库存储，由数据库层把标准模型映射为表结构。

## 2. 目录结构

```text
modules/anime-parser/
  PLAN.md
  DETAIL_DESIGN.md
  pyproject.toml
  src/anime_parser/
    __init__.py
    models.py
    errors.py
    normalizers.py
    service.py
    search.py
    merge.py
  tests/
    test_normalizers.py
    test_service.py
    test_search.py
    test_merge.py
```

职责划分：

| 文件 | 职责 |
|---|---|
| `models.py` | 定义输入源记录、标准输出模型、平台链接、诊断信息和结果包装 |
| `errors.py` | 定义错误类型常量和诊断构造函数 |
| `normalizers.py` | 实现季度、星期、时间、日期、标题、URL 标准化 |
| `service.py` | 编排单条番剧标准化与周表组装 |
| `search.py` | 对标准化后的 `AnimeItem` 做查询匹配和排序 |
| `merge.py` | 合并同一番剧的多条源记录或标准项 |
| `tests/` | 覆盖标准化、服务编排、搜索和合并行为 |

## 3. 技术选择

### 3.1 Python 包

V1 直接实现为本地 Python 包，不启动服务，不引入服务器常驻进程。

原因：

1. yuc 抓取模块可以直接 import；
2. Agent Skill Tool 可以直接 import；
3. API 层后续可以直接 import；
4. 数据库层可以直接消费标准模型；
5. 单元测试简单，不需要集成环境。

### 3.2 Pydantic 模型

模型层使用 Pydantic。

原因：

1. 输入输出可以严格校验；
2. 后续 FastAPI 可以直接复用；
3. 可以导出 JSON Schema；
4. Skill 和 CLI 可以直接使用 `model_dump()` 得到 JSON；
5. 字段默认值、可空字段和嵌套结构更清晰。

V1 只依赖 Pydantic 和 pytest，不引入 ORM、HTTP client、Web 框架。

## 4. 核心模型

### 4.1 `SourceAnimeRecord`

源记录是数据源适配器传给解析模块的输入 DTO。它保留源站原始语义，不追求字段已经标准化。

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `source` | `str` | 是 | 数据源标识，如 `yuc` |
| `source_url` | `str | None` | 否 | 源页面或源 API URL |
| `source_id` | `str | None` | 否 | 源站唯一 ID，没有则为空 |
| `season_raw` | `str | None` | 否 | 原始季度 |
| `title_raw` | `str | None` | 否 | 原始标题，缺失时不能生成标准项 |
| `title_cn_raw` | `str | None` | 否 | 原始中文标题 |
| `title_jp_raw` | `str | None` | 否 | 原始日文标题 |
| `title_en_raw` | `str | None` | 否 | 原始英文标题 |
| `aliases_raw` | `list[str]` | 否 | 原始别名 |
| `weekday_raw` | `str | int | None` | 否 | 原始星期 |
| `air_time_raw` | `str | None` | 否 | 原始播出时间 |
| `start_date_raw` | `str | None` | 否 | 原始首播日期 |
| `description_raw` | `str | None` | 否 | 简介、播出说明或详情文本 |
| `cover_url_raw` | `str | None` | 否 | 封面 URL |
| `official_url_raw` | `str | None` | 否 | 官网 URL |
| `platform_links_raw` | `list[SourcePlatformLink]` | 否 | 平台链接 |
| `source_payload` | `dict` | 否 | 数据源私有字段 |

约束：

1. `source` 必须非空；
2. `title_raw`、`title_cn_raw`、`title_jp_raw` 至少一个有值才可生成 `AnimeItem`；
3. `source_payload` 只用于追溯和排查，不直接进入标准字段。

### 4.2 `PlatformLink`

平台链接用于保留 B 站、巴哈、Crunchyroll、Netflix 等观看入口或地区信息。

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `url` | `str | None` | 链接地址 |
| `label` | `str | None` | 平台名称或源站文本 |
| `region` | `str | None` | 地区，如 `大陆`、`港台`、`环大陆` |
| `kind` | `str | None` | 可选分类，如 `streaming`、`official` |

### 4.3 `AnimeItem`

标准番剧项是后续 API、Skill、缓存和数据库的主消费模型。

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source` | `str` | 主要来源 |
| `external_id` | `str | None` | 源站 ID |
| `external_url` | `str | None` | 源站 URL |
| `season` | `str | None` | 标准季度 `YYYY-MM` |
| `title_cn` | `str | None` | 中文标题 |
| `title_jp` | `str | None` | 日文标题 |
| `title_en` | `str | None` | 英文标题 |
| `aliases` | `list[str]` | 别名 |
| `weekday` | `int | None` | `1-7`，无固定星期时为空 |
| `air_time` | `str | None` | `HH:mm`，允许 `24:xx` |
| `start_date` | `str | None` | `YYYY-MM-DD` |
| `timezone` | `str` | 默认 `Asia/Shanghai` |
| `description` | `str | None` | 简介或播出说明 |
| `cover_url` | `str | None` | 封面 URL |
| `official_url` | `str | None` | 官网 URL |
| `platform_links` | `list[PlatformLink]` | 平台链接 |
| `confidence` | `float` | 匹配或合并置信度 |

字段约束：

1. `confidence` 范围为 `0.0-1.0`；
2. `weekday` 只能是 `1-7` 或 `null`；
3. `season` 标准格式固定为 `YYYY-MM`；
4. 输出时不包含 `source_payload`。

### 4.4 `ScheduleDay` 与 `WeeklySchedule`

`ScheduleDay` 按星期组织番剧：

```json
{
  "weekday": 3,
  "label": "周三",
  "items": []
}
```

`WeeklySchedule` 按季度组织周表：

```json
{
  "source": "yuc",
  "season": "2026-04",
  "days": []
}
```

组装规则：

1. 默认输出 1 到 7 的已有分组；
2. 无固定星期项目不混入 1 到 7，可由后续扩展为 `undated_items`；
3. 同一天内保持输入源记录顺序；
4. 空分组默认不输出，避免前端额外处理空天。

### 4.5 `AnimeParseResult`

所有对外服务函数都返回结果包装，避免调用方处理不一致的异常。

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | `bool` | 是否成功 |
| `source` | `str | None` | 来源 |
| `operation` | `str` | 操作名 |
| `data` | `Any | None` | 成功数据 |
| `error_type` | `str | None` | 错误类型 |
| `error_message` | `str | None` | 错误说明 |
| `diagnostics` | `list[Diagnostic]` | 字段级诊断 |
| `freshness` | `str | None` | 默认 `live`，缓存层后续可覆盖 |

`ok = false` 时：

1. `data` 必须为 `null` 或候选数据；
2. `error_type` 必须非空；
3. `error_message` 必须可读；
4. 不抛出业务异常给上层。

## 5. 标准化细节

### 5.1 季度标准化

函数：`normalize_season(value: str | None) -> NormalizedValue[str]`

接受格式：

1. `202604`；
2. `2026-04`；
3. `2026年4月`；
4. `2026年04月`。

输出：

1. 合法输出 `YYYY-MM`；
2. 月份必须是 `01`、`04`、`07`、`10`；
3. 不合法返回诊断 `invalid_season`。

### 5.2 星期标准化

函数：`normalize_weekday(value: str | int | None) -> NormalizedValue[int | None]`

支持：

1. `1-7`；
2. `周一` 到 `周日`；
3. `星期一` 到 `星期日`；
4. 日文 `月`、`火`、`水`、`木`、`金`、`土`、`日`；
5. 英文 `mon` 到 `sun`。

特殊值：

1. `网络放送`、`其他`、`未定`、`待定` 返回 `None`，不视为失败；
2. 非空但无法识别返回 `invalid_weekday` 诊断。

### 5.3 时间标准化

函数：`normalize_air_time(value: str | None) -> NormalizedValue[str | None]`

规则：

1. 提取第一个 `H:mm` 或 `HH:mm`；
2. 去掉 yuc 常见后缀 `~`；
3. `7:05` 补为 `07:05`；
4. `24:30`、`25:00` 原样保留；
5. `年番`、`待定`、空值返回 `None` 并记录诊断或备注。

不做：

1. 不跨日换算；
2. 不生成 timezone-aware datetime；
3. 不根据 weekday 推算具体播出日期。

### 5.4 日期标准化

函数：`normalize_start_date(value: str | None, season: str | None) -> NormalizedValue[str | None]`

规则：

1. `4/1~` 输出 `YYYY-04-01`；
2. `04/01` 输出 `YYYY-04-01`；
3. `2026-04-01` 原样标准化；
4. 年份缺失时使用 `season` 的年份；
5. 无法确定日期时返回 `None`，并写诊断。

### 5.5 标题标准化

函数：

1. `clean_display_text(value: str | None) -> str | None`；
2. `normalize_title_for_match(value: str | None) -> str`。

展示清洗：

1. HTML `<br>` 转空格；
2. 连续空白压缩；
3. 去掉首尾空白；
4. 不删除标题中的季数、括号和标点。

匹配归一：

1. 使用 Unicode NFKC；
2. 转小写；
3. 去掉空白；
4. 简化常见中英文标点差异；
5. 去掉 HTML 残留标签。

### 5.6 URL 标准化

函数：`normalize_url(value: str | None, base_url: str | None = None) -> str | None`

规则：

1. 绝对 URL 原样保留；
2. 相对 URL 需要 base_url 才能补全；
3. 空值返回 `None`；
4. 非 HTTP/HTTPS 协议默认拒绝，并写诊断。

## 6. 服务接口详设

### 6.1 `normalize_anime`

签名：

```python
def normalize_anime(record: SourceAnimeRecord) -> AnimeParseResult[AnimeItem]:
    ...
```

流程：

1. 校验 `source`；
2. 选择主标题：`title_cn_raw` > `title_raw` > `title_jp_raw` > `title_en_raw`；
3. 标准化季度、星期、时间、日期；
4. 清洗标题和别名；
5. 标准化 URL 和平台链接；
6. 构造 `AnimeItem`；
7. 非关键字段失败写入 diagnostics；
8. 关键字段缺失返回 `ok=false`。

关键失败：

1. `source` 缺失：`invalid_source_record`；
2. 标题缺失：`missing_title`；
3. 季度非法且调用方要求必须有季度：`invalid_season`。

### 6.2 `normalize_weekly_schedule`

签名：

```python
def normalize_weekly_schedule(
    source: str,
    season: str,
    records: list[SourceAnimeRecord],
) -> AnimeParseResult[WeeklySchedule]:
    ...
```

流程：

1. 标准化 `season`；
2. 逐条调用 `normalize_anime`；
3. 成功项按 `weekday` 分组；
4. 保持同一 weekday 内输入顺序；
5. 收集失败项诊断；
6. 所有记录都失败时返回 `parse_zero_items` 或 `invalid_source_record`；
7. 部分失败时 `ok=true`，diagnostics 记录失败项。

输出策略：

1. `days` 按 weekday 升序；
2. 空星期不输出；
3. `weekday = None` 的项目 V1 不进入 `days`，但保留诊断，后续可扩展 `undated_items`。

### 6.3 `search_anime_items`

签名：

```python
def search_anime_items(
    items: list[AnimeItem],
    query: str,
    limit: int = 5,
) -> AnimeParseResult[list[AnimeItem]]:
    ...
```

匹配顺序：

1. 标准标题精确匹配，`confidence = 1.0`；
2. 别名精确匹配，`confidence = 0.95`；
3. 标题包含匹配，`confidence = 0.85`；
4. 别名包含匹配，`confidence = 0.8`；
5. 归一化包含匹配，`confidence = 0.7`。

排序：

1. confidence 降序；
2. 标题长度短者优先；
3. 输入顺序稳定。

失败：

1. query 为空：`invalid_params`；
2. 无匹配：`not_found`，data 为空列表。

### 6.4 `merge_anime_records`

签名：

```python
def merge_anime_records(
    records: list[SourceAnimeRecord],
) -> AnimeParseResult[AnimeItem | list[AnimeItem]]:
    ...
```

V1 采用保守合并：

1. 同一 `source + source_id` 必定可合并；
2. `source_id` 缺失时，标题归一化完全相同才合并；
3. 标题高度相似但不完全一致时返回候选列表；
4. 冲突字段不静默覆盖，写入 `merge_conflict` 诊断；
5. 字段选择优先级为非空、信息更长、来源更可信。

V1 不做复杂模糊合并，不引入外部相似度库。

## 7. API / Skill / 数据库接入

### 7.1 API 接入

API 层只 import `anime_parser.service`：

```python
result = normalize_weekly_schedule(source="yuc", season="2026-04", records=records)
return result.model_dump()
```

API 层职责：

1. 处理 HTTP 入参；
2. 调用抓取模块或数据库；
3. 调用解析模块；
4. 返回 JSON。

API 层不重新实现标题、季度、星期、时间标准化。

### 7.2 Skill 接入

Skill Tool 只消费结构化结果：

```python
result = search_anime_items(items, query="番名", limit=5)
return result.model_dump()
```

Skill 层职责：

1. 做参数映射；
2. 调用底层能力；
3. 把 `AnimeParseResult` 转为工具输出；
4. 根据 `error_type` 生成用户可读回复。

Skill 层不直接处理源站字段。

### 7.3 数据库接入

数据库层后续从 `AnimeItem` 映射到表结构。

建议表边界：

1. `anime`：存标准字段，如标题、季度、星期、时间、封面、官网；
2. `anime_source`：存 `source`、`external_id`、`external_url`、`source_payload`、`raw_hash`；
3. `anime_platform_link`：存平台链接。

解析模块不直接写库，只提供可序列化模型。

## 8. 错误与诊断

### 8.1 `Diagnostic`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | `str` | 诊断类型 |
| `field` | `str | None` | 关联字段 |
| `message` | `str` | 可读说明 |
| `raw_value` | `Any | None` | 原始值 |
| `severity` | `str` | `info`、`warning`、`error` |

### 8.2 错误分级

`error`：

1. 缺少 source；
2. 缺少标题；
3. 季度参数非法；
4. 输入 records 为空且调用方要求产出周表。

`warning`：

1. 星期无法识别；
2. 日期无法识别；
3. URL 非法；
4. 合并字段冲突。

`info`：

1. 年番、待定等无法结构化但可保留的备注；
2. 无固定星期；
3. 无首播日期。

### 8.3 异常策略

1. 业务错误通过 `AnimeParseResult` 返回；
2. 只有编程错误或不可恢复错误才抛异常；
3. 单条记录失败不应导致整批失败；
4. 所有诊断必须能序列化为 JSON。

## 9. 测试设计

### 9.1 normalizers

覆盖：

1. 季度合法和非法输入；
2. 中文、日文、英文星期；
3. `24:30~`、`7:05`、待定、年番；
4. `4/1~` 补全年份；
5. `<br>`、全角半角、标点、连续空白；
6. HTTP/HTTPS URL 和非法协议。

### 9.2 service

覆盖：

1. 单条完整源记录输出完整 `AnimeItem`；
2. 缺少标题返回 `missing_title`；
3. 缺少非关键字段仍成功并带 diagnostics；
4. 周表按 weekday 分组；
5. 同一天保持输入顺序；
6. 部分记录失败时整体仍成功；
7. 全部失败时返回结构化错误。

### 9.3 search

覆盖：

1. 中文标题精确匹配；
2. 别名匹配；
3. 包含匹配；
4. 归一化匹配；
5. limit 生效；
6. 无结果返回 `not_found`。

### 9.4 merge

覆盖：

1. 同 source_id 合并；
2. 同归一化标题合并；
3. 相似但不确定时返回候选；
4. 字段冲突生成诊断；
5. 空输入或全失败输入。

## 10. V1 交付标准

V1 完成时必须满足：

1. 提供可 import 的 `anime_parser` 包；
2. 提供 Pydantic 模型；
3. 提供 `normalize_anime`、`normalize_weekly_schedule`、`search_anime_items`、`merge_anime_records`；
4. 所有输出可 `model_dump()` 成 JSON；
5. 不依赖网络、数据库、Web 框架；
6. 单元测试覆盖核心标准化和错误路径；
7. yuc 抓取模块可直接把源记录交给本模块处理。
