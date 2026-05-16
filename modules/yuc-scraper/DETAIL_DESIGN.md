# yuc-scraper 静态抓取模块详设

## 1. 设计目标

`yuc-scraper` 是面向 `yuc.wiki` 的确定性静态 HTML 抓取库。它负责请求 yuc 首页和季度页，依据配置化 DOM 规则提取源站记录，并调用 `anime-parser` 输出统一的番剧模型和查询结果。

本模块必须保持以下边界：

1. 不创建 Agent Skill 或 Tool；
2. 不暴露 HTTP API；
3. 不依赖数据库、缓存或后台任务；
4. 不使用浏览器自动化；
5. 不执行页面 JavaScript；
6. 不让 LLM 参与 V1 的页面解析结果生成；
7. 不把原始 HTML 暴露给上层调用方。

V1 的核心目标是让后续 Skill、API 或 CLI 能通过纯代码接口完成：

1. 获取当前季度；
2. 获取指定季度周表；
3. 按星期过滤番剧；
4. 搜索番剧；
5. 查询番剧基础详情。

## 2. 目录结构

```text
modules/yuc-scraper/
  PLAN.md
  DETAIL_DESIGN.md
  pyproject.toml
  src/yuc_scraper/
    __init__.py
    client.py
    config.py
    errors.py
    html.py
    models.py
    parser.py
    service.py
    url.py
  tests/
    fixtures/
      home.html
      season_202604.html
      season_schema_changed.html
      empty_article.html
    test_client.py
    test_config.py
    test_home_parser.py
    test_season_parser.py
    test_service.py
    test_search_detail.py
```

职责划分：

| 文件 | 职责 |
|---|---|
| `client.py` | 封装 yuc 静态 HTML 请求、超时、HTTP 状态和网络错误映射 |
| `config.py` | 定义抓取规则配置结构和默认 yuc 选择器 |
| `errors.py` | 定义 yuc 抓取层错误常量和诊断构造函数 |
| `html.py` | 提供 DOM 文本、属性、链接、兄弟节点遍历等底层 HTML 工具 |
| `models.py` | 定义 yuc 源站记录、季度链接、详情记录、抓取结果包装 |
| `parser.py` | 按配置解析首页、周表区和详情区，不请求网络 |
| `service.py` | 编排参数校验、请求、解析、标准化、搜索和详情查询 |
| `url.py` | 处理 `YYYY-MM`、`YYYYMM`、相对 URL 和 yuc 页面 URL 构造 |
| `tests/fixtures/` | 固定 HTML 样本，单元测试不得请求真实网络 |

## 3. 技术选择

### 3.1 Python 包

V1 实现为本地 Python 包，不启动服务进程。后续 Agent Skill / Tool、HTTP API 或缓存层只 import 本包，不复制页面解析逻辑。

### 3.2 HTTP 请求库

使用 `httpx` 作为请求层依赖。

原因：

1. 支持明确的连接、读取和总超时；
2. 异常类型清晰，便于映射 `network_timeout`、`network_error`；
3. 同步接口足够满足 V1；
4. 后续如果 API 层需要异步版本，可以在同一库内扩展。

V1 先提供同步接口。异步接口不进入本阶段。

### 3.3 HTML 解析库

使用 `beautifulsoup4` + 默认 HTML parser，依赖 SoupSieve CSS 选择器能力。

原因：

1. yuc 页面是静态 Hexo HTML，不需要浏览器 DOM；
2. CSS selector 与计划中的配置规则表达一致；
3. 对不规范 HTML 容忍度高；
4. 测试夹具中可直接断言选择器命中和字段提取。

如果默认 parser 在真实 fixture 上出现结构修复差异，再引入 `lxml` 作为可选解析器；V1 不先强依赖 `lxml`。

### 3.4 与 anime-parser 集成

`yuc-scraper` 不定义统一输出模型，统一输出继续使用 `anime-parser`：

1. yuc 周表源记录转换为 `SourceAnimeRecord`；
2. 平台链接转换为 `SourcePlatformLink`；
3. 周表输出通过 `normalize_weekly_schedule()` 生成 `WeeklySchedule`；
4. 搜索通过 `search_anime_items()` 完成；
5. 单条详情使用标准化后的 `AnimeItem` 返回。

## 4. 核心数据模型

### 4.1 `YucSeasonLink`

首页季度入口记录。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `season` | `str` | 是 | 标准季度 `YYYY-MM` |
| `season_compact` | `str` | 是 | yuc 路径格式 `YYYYMM` |
| `url` | `str` | 是 | 绝对季度页 URL |
| `text` | `str` | 是 | 链接显示文本 |
| `is_new` | `bool` | 是 | 是否命中 `New` 标记 |

排序规则：

1. `get_current_season` 优先选择 `is_new = true` 且季度合法的最新项；
2. 如果没有 `New` 标记，选择年月最大的合法季度；
3. 同一季度出现多次时按 `season` 去重，保留第一个 URL。

### 4.2 `YucWeeklySourceRecord`

周表区解析出的 yuc 源记录。

| 字段 | 类型 | 说明 |
|---|---|---|
| `season` | `str` | 标准季度 |
| `weekday` | `int | None` | 周一到周日为 `1-7`，网络放送或其他区可为空 |
| `weekday_label` | `str | None` | yuc 原始星期标题 |
| `air_time` | `str | None` | 原始时间文本，保留 `24:xx`、`25:xx` |
| `start_date` | `str | None` | 原始首播日期或空 |
| `note` | `str | None` | 年番、其他备注等非日期文本 |
| `title_text` | `str | None` | 标题区完整文本 |
| `title_cn` | `str | None` | 可直接作为中文标题的文本 |
| `cover_url` | `str | None` | 绝对封面图 URL |
| `platform_links` | `list[YucPlatformLink]` | 平台链接 |
| `source_url` | `str` | 当前季度页 URL |
| `selector_hits` | `dict[str, int]` | 关键选择器命中数量 |

转换到 `SourceAnimeRecord` 时：

1. `source` 固定为 `yuc`；
2. `season_raw` 使用 `season`；
3. `title_raw` 和 `title_cn_raw` 使用 `title_text` / `title_cn`；
4. `weekday_raw` 使用 `weekday` 或 `weekday_label`；
5. `air_time_raw` 使用 `air_time`；
6. `start_date_raw` 使用 `start_date`；
7. `cover_url_raw` 使用 `cover_url`；
8. 平台链接转换为 `SourcePlatformLink`；
9. `source_payload` 保留 `note`、`selector_hits`、原始字段文本和 yuc 私有信息。

### 4.3 `YucDetailSourceRecord`

季度页详情区解析出的源记录。

| 字段 | 类型 | 说明 |
|---|---|---|
| `season` | `str` | 标准季度 |
| `title_text` | `str | None` | 标题区完整文本 |
| `title_cn` | `str | None` | 中文标题 |
| `title_jp` | `str | None` | 日文或其他标题 |
| `types` | `list[str]` | 类型信息 |
| `tags` | `list[str]` | 标签信息 |
| `staff` | `list[str]` | staff 文本 |
| `cast` | `list[str]` | cast 文本 |
| `official_url` | `str | None` | 动画官网 |
| `broadcast_text` | `str | None` | 播出说明 |
| `source_url` | `str` | 当前季度页 URL |
| `selector_hits` | `dict[str, int]` | 关键选择器命中数量 |

详情记录用于补充周表记录。合并时以标题归一化 key 为主，不做不可靠猜测。

### 4.4 `YucSeasonPageParse`

季度页解析中间结果。

| 字段 | 类型 | 说明 |
|---|---|---|
| `season` | `str` | 标准季度 |
| `source_url` | `str` | 季度页 URL |
| `weekly_records` | `list[YucWeeklySourceRecord]` | 周表源记录 |
| `detail_records` | `list[YucDetailSourceRecord]` | 详情源记录 |
| `diagnostics` | `list[Diagnostic]` | 解析诊断 |

## 5. 抓取规则配置

V1 默认用代码内结构体表达配置，避免 YAML 解析依赖。结构体字段必须覆盖计划中的选择器，并允许后续替换默认规则。

```python
YucScrapeConfig(
    source="yuc",
    base_url="https://yuc.wiki",
    home_path="/",
    season_path_template="/{season_compact}/",
    list_seasons=SeasonListRule(
        link_selector="a[href]",
        href_pattern=r"^/[0-9]{6}/?$",
        text_pattern=r"^[0-9]{4}年(1|4|7|10)月新番",
    ),
    weekly=WeeklyRule(
        article_selector=".post-body",
        weekday_selector="td.date2",
        item_container_strategy="siblings_until_next_weekday_marker",
        time_selector=".div_date .imgtext4, .div_date .imgtext5",
        start_or_note_selector=".div_date .imgep2, .div_date .imgep",
        cover_selector=".div_date img",
        cover_attr_priority=("data-src", "src"),
        title_selector="td.date_title_, td.date_title__",
        platform_link_selector="tr.tr_area a",
        platform_area_selector=".area, .area_c",
    ),
    detail=DetailRule(
        article_selector=".post-body",
        detail_title_selector="td.title_main_r",
        title_cn_selector=".title_cn_r, .title_cn_r2, .title_cn_r3",
        type_selector=".type_c_r, .type_d_r, .type_e_r",
        tag_selector=".type_tag_r",
        staff_selector=".staff_r, .staff_r1",
        cast_selector=".cast_r",
        official_link_selector=".link_a_r a",
        broadcast_selector=".broadcast_r, .broadcast_ex_r",
    ),
)
```

配置原则：

1. 选择器只负责定位结构；
2. 文本标准化、日期识别、星期转换由确定性函数完成；
3. 配置变更必须配套 fixture 测试；
4. 单个非标题字段缺失不能丢弃整条番剧；
5. 标题缺失的卡片不生成 `SourceAnimeRecord`，但要记录诊断。

## 6. 请求层设计

### 6.1 `YucHttpClient`

公开方法：

```python
class YucHttpClient:
    def fetch_home(self) -> YucFetchResult: ...
    def fetch_season_page(self, season: str) -> YucFetchResult: ...
    def fetch_url(self, url: str) -> YucFetchResult: ...
```

默认行为：

1. `base_url = https://yuc.wiki`；
2. `timeout = 10s`；
3. `User-Agent` 使用固定项目标识，避免空 UA；
4. 只接受 `2xx` 状态码作为成功；
5. 响应按服务器编码或 `utf-8` 解码；
6. 不自动重试，避免误伤源站；重试属于后续缓存/同步层能力。

### 6.2 网络错误映射

| 异常或状态 | error_type |
|---|---|
| 连接或读取超时 | `network_timeout` |
| DNS、连接失败、TLS 错误 | `network_error` |
| 非 2xx HTTP 状态 | `http_error` |
| 响应为空或不可解码 | `source_unavailable` |

请求层只返回结构化失败，不抛出业务异常给服务层。

## 7. 首页解析设计

函数：

```python
parse_season_links(html: str, config: YucScrapeConfig) -> AnimeParseResult[list[YucSeasonLink]]
select_current_season(links: list[YucSeasonLink]) -> AnimeParseResult[YucSeasonLink]
```

处理流程：

1. 使用 `link_selector` 找出全部链接；
2. 对 `href` 执行 `href_pattern`；
3. 对文本执行 `text_pattern`；
4. 从 `href` 或文本提取 `YYYYMM`；
5. 将 `YYYYMM` 归一为 `YYYY-MM`；
6. 识别 `New`、`*(New)`、`（New）` 等标记；
7. 将相对路径转成绝对 URL；
8. 对季度去重并按年月倒序排序。

错误规则：

1. HTML 为空返回 `source_unavailable`；
2. 没有合法季度链接返回 `parse_schema_changed`；
3. 季度文本存在但月份非法时记录诊断并跳过；
4. `select_current_season` 没有候选时返回 `parse_zero_items`。

## 8. 季度页周表解析设计

函数：

```python
parse_season_page(html: str, season: str, source_url: str, config: YucScrapeConfig) -> AnimeParseResult[YucSeasonPageParse]
parse_weekly_records(article: Tag, season: str, source_url: str, config: YucScrapeConfig) -> list[YucWeeklySourceRecord]
```

### 8.1 文章区域定位

1. 优先使用 `.post-body`；
2. 如果 `.post-body` 不存在，返回 `parse_schema_changed`；
3. 如果文章区域存在但周表和详情均解析为空，返回 `parse_zero_items`。

### 8.2 星期分组

按 `td.date2` 作为分组边界：

1. 从文章区域内找到所有星期 marker；
2. 将 marker 文本转换为 `1-7`；
3. 从当前 marker 所在表格或父容器开始，遍历后续兄弟节点；
4. 遇到下一个星期 marker 时停止；
5. 在该范围内查找番剧卡片容器。

如果 yuc 的 DOM 不是完整表格兄弟结构，`html.py` 需要提供 `iter_until_next_marker()`，让遍历逻辑集中在一个地方，便于后续规则修复。

### 8.3 卡片字段提取

每个卡片按以下顺序提取：

1. 标题：`td.date_title_, td.date_title__`，保留 `<br>` 位置并归一为空格；
2. 时间：`.div_date .imgtext4, .div_date .imgtext5`；
3. 首播日期或备注：`.div_date .imgep2, .div_date .imgep`；
4. 封面：`.div_date img`，属性优先级为 `data-src`、`src`；
5. 平台链接：`tr.tr_area a`；
6. 区域文本：`.area, .area_c`。

首播日期与备注拆分规则：

1. `M/D~`、`MM/DD~` 进入 `start_date`；
2. `(年番)`、`年番`、`待定` 等进入 `note`；
3. 无法判断时保留到 `note`，不强行作为日期；
4. 日期标准化交给 `anime-parser`，yuc 层只保留原始文本。

时间规则：

1. 原样保留 `24:xx`、`25:xx`；
2. 去掉结尾 `~` 的动作由 `anime-parser` 完成；
3. 无固定播出时间返回 `None` 并记录 info 级诊断。

### 8.4 平台链接提取

平台链接模型字段：

| 字段 | 来源 |
|---|---|
| `url` | `a[href]` 转绝对 URL |
| `label` | 链接文本 |
| `region` | 附近 `.area` 或 `.area_c` 文本 |
| `kind` | 固定为 `streaming` |

同一卡片内相同 URL 去重；无 href 的平台文本保留 `label`，`url = None`。

## 9. 季度页详情解析设计

函数：

```python
parse_detail_records(article: Tag, season: str, source_url: str, config: YucScrapeConfig) -> list[YucDetailSourceRecord]
```

处理流程：

1. 用 `detail_title_selector` 定位详情标题块；
2. 以标题块的父级详情容器为单条详情范围；
3. 在范围内提取中文标题、其他标题、类型、标签、staff、cast、官网、播出说明；
4. 文本字段统一去除多余空白；
5. 列表字段按 DOM 顺序保留；
6. 官网链接转绝对 URL；
7. 字段缺失时返回 `None` 或空列表，不生成猜测值。

详情合并规则：

1. 对周表标题和详情标题调用 `normalize_title_for_match()` 得到 key；
2. key 完全相同则合并；
3. 周表标题包含详情标题或详情标题包含周表标题时作为候选合并，置信度降低；
4. 一个周表项匹配多个详情时不自动合并，保留候选并产生 `ambiguous_match` 诊断；
5. 一个详情匹配多个周表项时只补充完全相同 key 的记录。

补充字段：

1. `official_url_raw` 来自详情官网；
2. `description_raw` 优先使用播出说明，其次拼接类型、标签、staff、cast 的简短摘要；
3. `aliases_raw` 可加入详情区其他标题文本；
4. yuc 私有的完整 `types`、`tags`、`staff`、`cast` 放入 `source_payload`。

## 10. 服务接口设计

所有服务函数返回 `AnimeParseResult`，保持与 `anime-parser` 一致的结构化结果。

### 10.1 `get_current_season`

```python
def get_current_season() -> AnimeParseResult[str]:
    ...
```

流程：

1. 请求首页；
2. 解析季度链接；
3. 优先选择 `New` 标记；
4. 无 `New` 时选择最大年月；
5. 返回标准季度 `YYYY-MM`。

### 10.2 `get_weekly_schedule`

```python
def get_weekly_schedule(season: str = "current", weekday: int | None = None) -> AnimeParseResult[WeeklySchedule]:
    ...
```

流程：

1. 校验 `season` 和 `weekday`；
2. `season = current` 时调用 `get_current_season()`；
3. 请求季度页；
4. 解析周表记录和详情记录；
5. 合并详情字段；
6. 转换为 `SourceAnimeRecord`；
7. 调用 `normalize_weekly_schedule("yuc", season, records)`；
8. 如果传入 `weekday`，过滤 `WeeklySchedule.days`。

过滤规则：

1. `weekday` 必须是 `1-7`；
2. 不输出空星期分组；
3. 如果过滤后没有项目，返回 `ok = true`、空 `days`，并带 `not_found` info 诊断；
4. 解析阶段 0 条记录不能被当作空查询结果，必须返回 `parse_zero_items`。

### 10.3 `search_anime`

```python
def search_anime(query: str, season: str = "current", limit: int = 5) -> AnimeParseResult[list[AnimeItem]]:
    ...
```

流程：

1. 校验 `query` 非空；
2. 校验 `limit` 范围，建议 `1-50`；
3. 获取完整季度周表；
4. 展平 `WeeklySchedule.days[*].items`；
5. 调用 `search_anime_items(items, query, limit)`；
6. 返回候选列表。

搜索不直接解析详情区；详情字段已经在获取周表时尽量合并。

### 10.4 `get_anime_detail`

```python
def get_anime_detail(query: str, season: str = "current") -> AnimeParseResult[AnimeItem | list[AnimeItem]]:
    ...
```

流程：

1. 调用 `search_anime(query, season, limit=5)`；
2. 如果没有候选，返回 `ok = true`、`data = None`，诊断为 `not_found`；
3. 如果最高置信度唯一且达到唯一匹配阈值，返回单个 `AnimeItem`；
4. 如果存在多个同置信度或相近候选，返回候选列表，并设置 `error_type = ambiguous_match`、`ok = false`。

唯一匹配阈值：

1. 精确标题匹配：`confidence >= 0.95`；
2. 包含或归一化匹配：仅当候选数为 1 且 `confidence >= 0.85` 才唯一；
3. 其余情况返回候选。

## 11. 参数校验

| 参数 | 规则 |
|---|---|
| `season` | 允许 `current`、`YYYY-MM`、`YYYYMM` |
| `weekday` | 允许 `None` 或 `1-7` |
| `query` | trim 后非空 |
| `limit` | 默认 `5`，范围 `1-50` |

非法参数返回：

```json
{
  "ok": false,
  "source": "yuc",
  "operation": "yuc_get_weekly_schedule",
  "data": null,
  "error_type": "invalid_params",
  "error_message": "weekday must be between 1 and 7",
  "diagnostics": []
}
```

## 12. 错误处理

`yuc-scraper` 需要覆盖以下错误类型：

| 错误类型 | 触发条件 |
|---|---|
| `network_timeout` | 请求首页或季度页超时 |
| `network_error` | 连接、DNS、TLS 等网络错误 |
| `http_error` | 源站返回非 2xx |
| `source_unavailable` | 响应为空、不可解码或缺少正文 |
| `invalid_params` | 输入参数非法 |
| `parse_zero_items` | 页面成功但没有解析出任何番剧源记录 |
| `parse_schema_changed` | `.post-body`、星期 marker 等关键结构完全失效 |
| `ambiguous_match` | 详情查询无法唯一匹配 |
| `not_found` | 搜索无结果或指定 weekday 无番剧 |

错误原则：

1. 服务层不向调用方抛业务异常；
2. 单条番剧字段缺失产生诊断，不影响其他番剧；
3. 关键结构失效必须返回可诊断错误；
4. 页面结构变化不能伪装成搜索无结果；
5. 原始 HTML 只允许在测试 fixture 中存在，不放入运行时返回值。

## 13. 测试设计

### 13.1 单元测试

| 测试文件 | 覆盖内容 |
|---|---|
| `test_config.py` | 默认配置字段完整性、选择器存在 |
| `test_home_parser.py` | 季度链接提取、`New` 标记、最大季度 fallback、非法季度跳过 |
| `test_season_parser.py` | 周表解析、详情解析、平台链接、封面 `data-src`、`<br>` 标题 |
| `test_search_detail.py` | 搜索排序、唯一详情、候选详情、无结果 |
| `test_service.py` | 服务编排、weekday 过滤、参数错误、解析错误透传 |
| `test_client.py` | 超时、网络错误、HTTP 错误映射 |

### 13.2 Fixture 要求

`tests/fixtures/home.html` 至少覆盖：

1. 多个季度链接；
2. 一个带 `*(New)` 标记的季度；
3. 一个不合法月份链接；
4. 重复季度链接。

`tests/fixtures/season_202604.html` 至少覆盖：

1. 7 个 `td.date2`；
2. 普通周表番剧；
3. 网络放送或其他区；
4. `24:xx` 或 `25:xx` 深夜时间；
5. `<br>` 分行标题；
6. `img[data-src]` 封面；
7. 多个平台链接和区域文本；
8. 详情区标题、类型、标签、staff、cast、官网、播出说明。

### 13.3 网络隔离

单元测试默认不访问 `https://yuc.wiki`。

服务层测试通过注入 fake client 返回 fixture HTML。真实网络 smoke test 如有需要，放入单独标记：

```python
@pytest.mark.integration
def test_live_current_season():
    ...
```

集成测试默认跳过，避免 CI 或本地开发依赖源站可用性。

## 14. 实现步骤与提交边界

建议按以下提交拆分：

1. `chore(yuc-scraper): scaffold package and config`
   - 新增 `pyproject.toml`、包目录、配置结构、错误常量。
2. `feat(yuc-scraper): parse yuc home seasons`
   - 实现请求层或 fake client、首页季度解析、当前季度选择。
3. `feat(yuc-scraper): parse season weekly records`
   - 实现季度页周表解析和 `SourceAnimeRecord` 转换。
4. `feat(yuc-scraper): merge detail records`
   - 实现详情区解析、标题 key 合并和候选诊断。
5. `feat(yuc-scraper): expose query service`
   - 实现 `get_weekly_schedule`、`search_anime`、`get_anime_detail`。
6. `test(yuc-scraper): cover fixtures and error paths`
   - 补齐 fixture、错误映射和服务层测试。

每一步都应保持测试可运行，并且只提交该步相关文件。

## 15. 验收标准

1. `get_current_season()` 能从静态首页 HTML 解析当前季度；
2. `get_weekly_schedule("2026-04")` 能从 fixture 季度页输出 `WeeklySchedule`；
3. `get_weekly_schedule(..., weekday=3)` 只返回周三项目；
4. `search_anime()` 支持精确、包含和归一化匹配；
5. `get_anime_detail()` 能唯一返回详情或返回候选列表；
6. 页面成功但周表为空时返回 `parse_zero_items`；
7. 关键选择器失效时返回 `parse_schema_changed`；
8. 网络失败、HTTP 错误和参数错误都有明确 `error_type`；
9. 单元测试不依赖真实网络；
10. 模块不依赖 Agent、Skill、API、数据库、缓存、浏览器或页面 JavaScript。
