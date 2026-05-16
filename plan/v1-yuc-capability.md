# V1-A：yuc 能力实现计划

## 1. 目标

本计划只描述 yuc 能力实现。它是底层确定性能力，负责从 yuc.wiki 静态 Hexo 页面抓取、解析并输出结构化番剧数据。

yuc.wiki 当前没有可依赖的后端查询接口。V1 不按接口爬虫设计，不做浏览器自动化，不依赖页面 JavaScript 执行；只请求 Hexo 已生成的 HTML，并使用配置化 HTML 解析规则提取数据。

本模块不创建 Agent Skill，不写 Skill 文档，不处理 Agent 触发逻辑。

参考页面：

- 首页：https://yuc.wiki/
- 季度页示例：https://yuc.wiki/202604/

## 2. 实现范围

只实现：

1. 数据模型与标准化；
2. yuc 静态 HTML 请求；
3. 配置化 HTML 抓取规则；
4. 当前季度识别；
5. 指定季度周表解析；
6. 按星期过滤；
7. 番剧搜索；
8. 番剧基础详情解析；
9. 结构化错误返回。

不实现：

1. 本地 Agent Skill / Tool；
2. HTTP API；
3. 数据库；
4. 缓存；
5. 后台同步；
6. 用户订阅；
7. 提醒；
8. QQ Bot；
9. RSS/qB；
10. 浏览器自动化抓取；
11. LLM 直接解析页面内容。

LLM 只可在后续阶段用于生成或修复候选抓取规则建议，不能参与 V1 的确定性解析结果生成。

## 3. 页面结构依据

### 3.1 首页

首页是 Hexo 生成的静态 HTML，季度入口以链接形式存在。

可用结构信号：

1. 季度链接路径形如 `/YYYYMM/` 或 `/YYYYMM`；
2. 链接文本形如 `2026年4月新番`、`2025年10月新番`；
3. 当前最新季度可能带有 `*(New)` 标记，但不能只依赖该标记。

首页解析目标：

1. 找出所有合法季度链接；
2. 将 `YYYYMM` 标准化为 `YYYY-MM`；
3. 按年月倒序识别最新季度；
4. 输出季度对应的页面 URL。

### 3.2 季度页周表区

季度页是 Hexo 静态文章，正文中直接包含周表 DOM。

可用结构信号：

1. `td.date2` 表示周几标题，例如 `周一 (月)`；
2. 番剧卡片通常位于周几标题之后的相邻 `div` 中；
3. `div.div_date` 内包含播出时间、首播日期或备注、封面图；
4. 时间文本常见于 `p.imgtext4`、`p.imgtext5`，例如 `22:00~`、`24:30~`；
5. 首播日期或备注常见于 `p.imgep2`、`p.imgep`，例如 `4/6~`、`(年番)`；
6. 标题常见于 `td.date_title_`、`td.date_title__`，标题内可能使用 `<br>` 分行；
7. 平台链接位于 `tr.tr_area a`，区域文本常见于 `p.area`、`p.area_c`；
8. 封面图通常使用 `img[data-src]`，不能只读取 `src`。

周表解析目标：

1. 以 `td.date2` 切分星期分组；
2. 对每个分组解析番剧卡片；
3. 提取 `weekday`、`air_time`、`start_date`、`title_cn`、`cover_url`、平台链接；
4. 将标题中的 `<br>` 归一为空格或直接拼接，避免丢词；
5. 保留 `24:xx`、`25:xx` 等深夜时间文本，不强行换算日期；
6. 对网络放送、其他、无固定播出时间的项目允许 `weekday`、`air_time` 或 `start_date` 为 `null`。

### 3.3 季度页详情区

季度页下半部分包含番剧基础详情，不是单独详情接口。

可用结构信号：

1. 标题区常见于 `td.title_main_r` 及其子节点，如 `p.title_cn_r2`、`p.title_cn_r3`；
2. 类型信息常见于 `td.type_c_r`、`td.type_d_r`、`td.type_e_r`；
3. 标签信息常见于 `td.type_tag_r`；
4. staff 信息常见于 `td.staff_r`、`td.staff_r1`；
5. cast 信息常见于 `td.cast_r`；
6. 官网链接常见于 `td.link_a_r a`，文本可能为 `动画官网`；
7. 播出说明常见于 `p.broadcast_r`、`p.broadcast_ex_r`。

详情解析目标：

1. 提取中文标题、日文标题或其他标题文本；
2. 提取类型、标签、staff、cast、官网链接、播出说明；
3. 通过标题归一化与周表项目合并；
4. 详情字段缺失时返回 `null` 或空列表，不编造内容；
5. 无法唯一合并时保留候选，不做不可靠合并。

## 4. 输出模型

本模块输出统一结构，供后续 Skill、API、缓存和数据库复用。

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

### `YucResult`

```json
{
  "ok": true,
  "source": "yuc",
  "operation": "get_weekly_schedule",
  "data": {},
  "error_type": null,
  "error_message": null,
  "freshness": "live"
}
```

## 5. 能力接口

本模块应提供纯代码接口，供 Skill 或 API 调用。

### `get_current_season`

输入：无。

输出：当前季度，例如 `2026-04`。

行为：

1. 请求首页 HTML；
2. 使用首页季度发现规则提取所有季度；
3. 优先选择带 `*(New)` 标记的合法季度；
4. 如果没有 `*(New)` 标记，则选择年月最大的季度；
5. 解析失败时返回结构化错误。

### `get_weekly_schedule`

输入：

```json
{
  "season": "current",
  "weekday": 3
}
```

输出：`WeeklySchedule`。

行为：

1. `season = current` 时先调用当前季度识别；
2. 将 `YYYY-MM` 转换为 `YYYYMM`；
3. 请求 `https://yuc.wiki/{YYYYMM}/`；
4. 使用配置化规则解析周表与基础详情；
5. 如果传入 `weekday`，只返回对应星期的数据。

### `search_anime`

输入：

```json
{
  "query": "番名",
  "season": "current",
  "limit": 5
}
```

输出：`AnimeItem[]`。

匹配策略：

1. 标题精确匹配；
2. 标题包含匹配；
3. 简单归一化后匹配。

标题归一化至少处理：

1. 全角、半角空格；
2. 换行和 `<br>`；
3. 常见标点差异；
4. 大小写；
5. 连续空白。

### `get_anime_detail`

输入：

```json
{
  "query": "番名",
  "season": "current"
}
```

输出：单个 `AnimeItem` 或候选列表。

如果无法唯一匹配，返回候选列表。

## 6. 配置化抓取规则

V1 采用配置化 HTML 抓取规则，不采用纯硬编码解析器。

配置可以是 YAML、JSON 或代码内结构体，但必须表达以下内容：

```yaml
source: yuc
base_url: https://yuc.wiki

operations:
  list_seasons:
    url: /
    season_link:
      selector: a[href]
      href_pattern: "^/[0-9]{6}/?$"
      text_pattern: "^[0-9]{4}年(1|4|7|10)月新番"
      normalize: yyyymm_to_season

  get_season_page:
    url: "/{season_compact}/"

  parse_weekly_schedule:
    article_selector: ".post-body"
    weekday_marker:
      selector: "td.date2"
      transform: yuc_weekday_text_to_int
    item:
      container_strategy: "siblings_until_next_weekday_marker"
      time_selector: ".div_date .imgtext4, .div_date .imgtext5"
      start_or_note_selector: ".div_date .imgep2, .div_date .imgep"
      cover_selector: ".div_date img"
      cover_attr: "data-src"
      title_selector: "td.date_title_, td.date_title__"
      platform_link_selector: "tr.tr_area a"
      platform_area_selector: ".area, .area_c"

  parse_anime_detail:
    article_selector: ".post-body"
    detail_title_selector: "td.title_main_r"
    title_cn_selector: ".title_cn_r, .title_cn_r2, .title_cn_r3"
    type_selector: ".type_c_r, .type_d_r, .type_e_r"
    tag_selector: ".type_tag_r"
    staff_selector: ".staff_r, .staff_r1"
    cast_selector: ".cast_r"
    official_link_selector: ".link_a_r a"
    broadcast_selector: ".broadcast_r, .broadcast_ex_r"
```

配置解释：

1. 选择器用于定位结构，不负责业务判断；
2. `container_strategy` 允许实现层按 DOM 邻接关系切分周表项目；
3. transform 函数必须是确定性代码；
4. 配置规则变更必须有 fixture 测试覆盖；
5. 解析器不得因为单个字段缺失而丢弃整部番剧，除非标题缺失。

## 7. 错误处理

| 错误类型 | 含义 | 处理方式 |
|---|---|---|
| `network_timeout` | 请求超时 | 返回失败结果 |
| `network_error` | 网络连接失败 | 返回失败结果 |
| `http_error` | 源站返回非 2xx | 返回状态码信息 |
| `source_unavailable` | 源站不可用 | 返回失败结果 |
| `invalid_params` | 参数非法 | 返回字段级错误 |
| `parse_zero_items` | 页面成功但解析为空 | 提示页面结构可能变化 |
| `parse_schema_changed` | 关键结构失效 | 提示需要更新解析规则 |
| `ambiguous_match` | 无法唯一匹配 | 返回候选列表 |
| `not_found` | 未找到番剧 | 返回空结果 |

错误原则：

- 不编造番剧信息；
- 不把原始 HTML 暴露给上层；
- 不吞掉错误；
- 始终返回结构化结果；
- 页面请求成功但周表解析为 0 条时必须返回 `parse_zero_items`；
- 关键选择器完全失效时必须返回 `parse_schema_changed`；
- 不把 yuc 页面结构变化伪装成空搜索结果。

## 8. 测试计划

1. 使用固定 yuc 首页 HTML fixture 测试季度列表解析；
2. 测试 `*(New)` 标记存在时能识别当前季度；
3. 测试无 `*(New)` 标记时按年月选择最新季度；
4. 使用固定 yuc 季度页 HTML fixture 测试完整周表解析；
5. 测试季度页 fixture 能解析 7 天周表；
6. 测试网络放送、其他区、无固定星期或无固定时间项目；
7. 测试基础详情区解析，包括标题、类型、标签、staff、cast、官网、播出说明；
8. 测试按 weekday 过滤；
9. 测试标题精确匹配、包含匹配、归一化匹配；
10. 测试标题中 `<br>` 不导致断词或漏词；
11. 测试多平台链接提取；
12. 测试缺失首播日期时返回 `null`；
13. 测试 `24:xx`、`25:xx` 等深夜时间原样保留；
14. 测试详情字段缺失时返回 `null` 或空列表；
15. 测试空页面返回 `parse_zero_items`；
16. 测试关键 class 缺失返回 `parse_schema_changed`；
17. 测试网络失败、HTTP 错误；
18. 测试所有失败路径都返回明确 `error_type`。

## 9. 验收标准

1. 能通过静态 HTML 首页获取当前季度；
2. 能通过静态 HTML 季度页获取指定季度周表；
3. 能按星期过滤番剧；
4. 能搜索番剧；
5. 能查询基础详情；
6. 返回结构化数据；
7. 不依赖 Agent；
8. 不依赖 Skill；
9. 不依赖数据库；
10. 不依赖服务常驻；
11. 不依赖浏览器自动化；
12. 不依赖页面 JavaScript 执行；
13. 不调用不存在的后端接口；
14. 抓取规则可通过配置调整；
15. 页面结构变化时能返回可诊断的结构化错误。
