"""Local visual validation server for Anime Track Project modules."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = Path(__file__).resolve().parent / "static"

for module_src in (
    REPO_ROOT / "modules" / "yuc-scraper" / "src",
    REPO_ROOT / "modules" / "anime-parser" / "src",
):
    sys.path.insert(0, str(module_src))

from anime_parser.models import SourceAnimeRecord  # noqa: E402
from anime_parser.service import normalize_anime, normalize_weekly_schedule  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from yuc_scraper.service import (  # noqa: E402
    get_anime_detail,
    get_current_season,
    get_weekly_schedule,
    search_anime,
)


SAMPLE_RECORD: dict[str, Any] = {
    "source": "visual_validation",
    "source_url": "https://example.test/anime/1",
    "source_id": "sample-001",
    "season_raw": "2026-04",
    "title_raw": "  示例动画  ",
    "title_cn_raw": "示例动画",
    "title_jp_raw": "サンプルアニメ",
    "title_en_raw": "Sample Anime",
    "aliases_raw": ["样例动画", "Sample"],
    "weekday_raw": "周六",
    "air_time_raw": "24:30",
    "start_date_raw": "2026年4月5日",
    "description_raw": "  用于验证归一化链路的示例记录。 ",
    "cover_url_raw": "//example.test/cover.jpg",
    "official_url_raw": "https://example.test",
    "platform_links_raw": [
        {
            "url": "https://example.test/watch",
            "label": "示例平台",
            "region": "CN",
            "kind": "streaming",
        }
    ],
}

SAMPLE_WEEKLY_PAYLOAD: dict[str, Any] = {
    "source": "visual_validation",
    "season": "2026-04",
    "records": [
        SAMPLE_RECORD,
        {
            **SAMPLE_RECORD,
            "source_id": "sample-002",
            "title_raw": "第二部示例动画",
            "title_cn_raw": "第二部示例动画",
            "aliases_raw": ["第二部"],
            "weekday_raw": 2,
            "air_time_raw": "21:00",
        },
    ],
}


def to_jsonable(value: Any) -> Any:
    """Convert Pydantic models and nested values to JSON-serializable data."""
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value


def first_query_value(params: dict[str, list[str]], key: str, default: str = "") -> str:
    return params.get(key, [default])[0]


def optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


class VisualValidationHandler(BaseHTTPRequestHandler):
    server_version = "AnimeVisualValidation/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path, parse_qs(parsed.query))
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.handle_api_post(parsed.path)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), format % args))

    def handle_api_get(self, path: str, params: dict[str, list[str]]) -> None:
        try:
            if path == "/api/health":
                self.send_json({"ok": True, "service": "visual_validation"})
            elif path == "/api/examples":
                self.send_json(
                    {
                        "normalizeAnime": SAMPLE_RECORD,
                        "normalizeWeeklySchedule": SAMPLE_WEEKLY_PAYLOAD,
                    }
                )
            elif path == "/api/yuc/current-season":
                self.send_json(to_jsonable(get_current_season()))
            elif path == "/api/yuc/weekly-schedule":
                season = first_query_value(params, "season", "current") or "current"
                weekday = optional_int(first_query_value(params, "weekday", ""))
                self.send_json(to_jsonable(get_weekly_schedule(season=season, weekday=weekday)))
            elif path == "/api/yuc/search":
                query = first_query_value(params, "query", "")
                season = first_query_value(params, "season", "current") or "current"
                limit = int(first_query_value(params, "limit", "5") or "5")
                self.send_json(to_jsonable(search_anime(query=query, season=season, limit=limit)))
            elif path == "/api/yuc/detail":
                query = first_query_value(params, "query", "")
                season = first_query_value(params, "season", "current") or "current"
                self.send_json(to_jsonable(get_anime_detail(query=query, season=season)))
            else:
                self.send_json({"ok": False, "error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - keeps the workbench responsive.
            self.send_json(
                {"ok": False, "error": exc.__class__.__name__, "message": str(exc)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def handle_api_post(self, path: str) -> None:
        try:
            payload = self.read_json_body()
            if path == "/api/anime/normalize":
                record = SourceAnimeRecord(**payload)
                self.send_json(to_jsonable(normalize_anime(record)))
            elif path == "/api/anime/weekly-schedule":
                source = payload.get("source") or "visual_validation"
                season = payload.get("season") or ""
                records = [SourceAnimeRecord(**item) for item in payload.get("records", [])]
                self.send_json(to_jsonable(normalize_weekly_schedule(source, season, records)))
            else:
                self.send_json({"ok": False, "error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError as exc:
            self.send_json({"ok": False, "error": f"invalid JSON: {exc}"}, HTTPStatus.BAD_REQUEST)
        except ValueError as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except ValidationError as exc:
            self.send_json({"ok": False, "error": "validation_error", "details": exc.errors()}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - keeps the workbench responsive.
            self.send_json(
                {"ok": False, "error": exc.__class__.__name__, "message": str(exc)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length).decode("utf-8")
        if not raw_body:
            return {}
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def serve_static(self, path: str) -> None:
        relative_path = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC_ROOT / relative_path).resolve()
        try:
            target.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), VisualValidationHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Anime Track visual validation workbench.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = build_server(args.host, args.port)
    print(f"Visual validation workbench: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
