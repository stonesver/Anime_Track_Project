# Visual Validation Workbench

本工具提供一个本地前端页面，用于验证当前仓库中的核心功能链路：

- `yuc_scraper.service.get_current_season`
- `yuc_scraper.service.get_weekly_schedule`
- `yuc_scraper.service.search_anime`
- `yuc_scraper.service.get_anime_detail`
- `anime_parser.service.normalize_anime`
- `anime_parser.service.normalize_weekly_schedule`

## 启动

方式一：双击仓库根目录下的：

```text
start_visual_validation.command
```

方式二：在仓库根目录执行：

```bash
tools/visual_validation/service.sh start-open
```

常用管理命令：

```bash
tools/visual_validation/service.sh status
tools/visual_validation/service.sh restart
tools/visual_validation/service.sh stop
```

方式三：直接启动 Python 服务：

在仓库根目录执行：

```bash
python3 tools/visual_validation/server.py --host 127.0.0.1 --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

## 说明

YUC 周表、搜索和详情验证会展示经过 `anime-parser` 标准化后的输出，包括类型、标签、staff 和 cast 字段。
YUC 相关验证会访问线上页面，网络不可用或目标页面结构变化时，页面会展示 service 层返回的错误和诊断信息。
anime-parser 相关验证默认使用内置示例 JSON，也可以直接在页面中编辑请求体。
