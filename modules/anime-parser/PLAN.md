# V1-A0：番剧解析与标准化模块计划

## 1. 目标

本模块负责把不同外部数据源提取到的源记录转换为统一、稳定、可复用的番剧输出模型。

无论数据来自 yuc.wiki、Bangumi、AniList、手工导入文件，还是后续新增的数据源，上层 Skill、API、缓存和数据库都只依赖本模块定义的标准模型，不直接依赖源站字段。

本模块不抓取网页、不请求外部 API、不创建 Agent Skill、不处理用户订阅和提醒。

详细实现设计见 `DETAIL_DESIGN.md`。

## 2. 实现范围

只实现：

1. 标准输出模型定义；
2. 外部源记录输入约定；
3. 季度、星期、日期、播出时间标准化；
4. 标题、别名、链接、封面、简介字段标准化；
5. 周表结构组装；
6. 同一番剧的源记录合并；
7. 搜索匹配用的标题归一化；
8. 结构化错误和诊断信息。

不实现：

1. yuc HTML 请求；
2. 任意外部 API 请求；
3. 浏览器自动化；
4. 数据库；
5. 缓存；
6. HTTP API；
7. 本地 Agent Skill / Tool；
8. 用户订阅、提醒、RSS/qB。

## 3. 输入约定

解析模块接收数据源适配器产生的源记录。源记录可以带有数据源私有字段，但必须至少表达以下语义。

### `SourceAnimeRecord`

```json
{
  "source": "yuc",
  "source_url": "https://yuc.wiki/202604/",
  "source_id": "string or null",
  "season_raw": "202604",
  "title_raw": "标题原文",
  "title_cn_raw": "中文标题或 null",
  "title_jp_raw": "日文标题或 null",
  "title_en_raw": "英文标题或 null",
  "aliases_raw": [],
  "weekday_raw": "周三",
  "air_time_raw": "24:30~",
  "start_date_raw": "4/1~",
  "description_raw": "string or null",
  "cover_url_raw": "string or null",
  "official_url_raw": "string or null",
  "platform_links_raw": [],
  "source_payload": {}
}
```

输入原则：

1. 源记录保留原始文本，不在数据源模块里提前丢弃信息；
2. 允许字段缺失，但标题缺失的记录不能生成标准番剧项；
3. 数据源私有字段放入 `source_payload`，不污染标准输出模型；
4. 数据源模块应标记来源 URL，便于后续排查。

## 4. 标准输出模型

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
  "platform_links": [],
  "confidence": 1.0
}
```

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

### `AnimeParseResult`

```json
{
  "ok": true,
  "source": "yuc",
  "operation": "normalize_weekly_schedule",
  "data": {},
  "error_type": null,
  "error_message": null,
  "diagnostics": [],
  "freshness": "live"
}
```

## 5. 标准化规则

### 5.1 季度

1. 标准季度格式固定为 `YYYY-MM`；
2. 接受 `YYYYMM`、`YYYY-MM`、`YYYY年M月` 等输入；
3. 只允许 `01`、`04`、`07`、`10` 四个季度月份；
4. 无法识别时返回 `invalid_season`。

### 5.2 星期

1. 标准星期使用整数 `1-7`，`1` 表示周一，`7` 表示周日；
2. 支持中文、日文和英文常见表达；
3. 网络放送、未定、其他等无固定星期项目允许为 `null`；
4. 无法识别但原字段非空时写入诊断信息。

### 5.3 时间与日期

1. `air_time` 使用 `HH:mm` 文本；
2. `24:xx`、`25:xx` 等深夜时间原样保留，不在 V1 强制换算日期；
3. `start_date` 使用 `YYYY-MM-DD`；
4. 只有月日时，用所属季度年份补全；
5. 年番、待定、首播备注等不能稳定转成日期时，保留到诊断或描述字段。

### 5.4 标题与别名

1. 展示标题保留原始语义，不做过度清洗；
2. 搜索标题使用归一化副本；
3. 归一化处理全角半角、大小写、连续空白、换行、`<br>`、常见标点差异；
4. 合并记录时优先保留信息更完整的标题字段。

### 5.5 链接与图片

1. `external_url` 表示源记录页面；
2. `official_url` 表示动画官网；
3. `cover_url` 保留可访问的封面 URL；
4. 平台链接统一放入 `platform_links`，每项至少包含 `url`、`label`、`region` 三类语义中可识别的部分。

## 6. 能力接口

### `normalize_anime`

输入：单个 `SourceAnimeRecord`。

输出：单个 `AnimeItem` 或结构化错误。

### `normalize_weekly_schedule`

输入：

```json
{
  "source": "yuc",
  "season": "2026-04",
  "records": []
}
```

输出：`WeeklySchedule`。

行为：

1. 标准化每条源记录；
2. 按 weekday 组装 `ScheduleDay`；
3. 保持同一天内原源站顺序；
4. 字段缺失时保留可用信息并记录诊断。

### `merge_anime_records`

输入：同一数据源或多个数据源的候选源记录。

输出：合并后的 `AnimeItem` 或候选列表。

合并原则：

1. 标题归一化相同或高度相似时才合并；
2. 同一来源的唯一标识优先于标题相似；
3. 冲突字段不静默覆盖，必须保留诊断；
4. 无法确认同一番剧时返回候选列表。

### `search_anime_items`

输入：标准化后的 `AnimeItem[]`、查询词、limit。

输出：按匹配置信度排序的 `AnimeItem[]`。

## 7. 错误处理

| 错误类型 | 含义 | 处理方式 |
|---|---|---|
| `invalid_source_record` | 源记录结构不符合最低要求 | 返回失败结果和字段诊断 |
| `missing_title` | 标题缺失 | 不生成 `AnimeItem` |
| `invalid_season` | 季度无法标准化 | 返回失败结果 |
| `invalid_weekday` | 星期无法标准化 | 字段置空并记录诊断 |
| `invalid_date` | 日期无法标准化 | 字段置空并记录诊断 |
| `merge_conflict` | 多条记录合并存在冲突 | 返回候选或保留诊断 |
| `ambiguous_match` | 搜索或详情无法唯一匹配 | 返回候选列表 |
| `not_found` | 未找到匹配项 | 返回空结果 |

错误原则：

- 不编造缺失字段；
- 不把源站私有字段暴露为标准字段；
- 不因非关键字段缺失丢弃整条记录；
- 所有失败路径都返回结构化错误或诊断信息。

## 8. 测试计划

1. 测试 `YYYYMM`、`YYYY-MM`、`YYYY年M月` 季度标准化；
2. 测试中文、日文、英文星期标准化；
3. 测试 `22:00~`、`24:30~`、待定、年番等时间输入；
4. 测试月日补全年份生成 `YYYY-MM-DD`；
5. 测试标题 `<br>`、多空格、全角半角、标点差异归一化；
6. 测试标准 `AnimeItem` 输出字段完整性；
7. 测试 `WeeklySchedule` 按 weekday 组装并保持源站顺序；
8. 测试平台链接、封面、官网 URL 标准化；
9. 测试详情字段缺失时返回 `null` 或空列表；
10. 测试同一番剧多源记录合并；
11. 测试合并冲突返回诊断；
12. 测试缺少标题、非法季度、非法日期等错误路径；
13. 测试搜索精确匹配、包含匹配、归一化匹配和候选排序。

## 9. 验收标准

1. 能接收 yuc 抓取模块产生的源记录；
2. 能在不依赖具体源站 DOM 的情况下输出统一模型；
3. 能生成 `AnimeItem`、`ScheduleDay`、`WeeklySchedule`；
4. 能为后续 Skill、API、缓存和数据库提供稳定字段；
5. 能保留来源 URL 和必要诊断信息；
6. 能处理缺失字段和冲突字段；
7. 不依赖网络、浏览器自动化、数据库或服务常驻；
8. 新增外部数据源时不需要修改上层输出模型。
