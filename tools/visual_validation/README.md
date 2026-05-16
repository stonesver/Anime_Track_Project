# Visual Validation Workbench

本工具提供一个本地前端页面，用于验证当前仓库中的核心功能链路：

- `yuc_scraper.service.get_current_season`
- `yuc_scraper.service.get_weekly_schedule`
- `yuc_scraper.service.search_anime`
- `yuc_scraper.service.get_anime_detail`
- `anime_parser.service.normalize_anime`
- `anime_parser.service.normalize_weekly_schedule`

## 启动

在仓库根目录执行：

```bash
python3 tools/visual_validation/server.py --host 127.0.0.1 --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

## 说明

YUC 相关验证会访问线上页面，网络不可用或目标页面结构变化时，页面会展示 service 层返回的错误和诊断信息。
anime-parser 相关验证默认使用内置示例 JSON，也可以直接在页面中编辑请求体。
