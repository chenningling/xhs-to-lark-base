#!/usr/bin/env python3
"""从自由文本中提取小红书链接，并抓取标准化后的笔记数据。"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any


SHORT_URL_RE = re.compile(r"https?://xhslink\.com(?:/[A-Za-z0-9_-]+)+")
NOTE_URL_RE = re.compile(
    r"https?://www\.xiaohongshu\.com/"
    r"(?:explore|discovery/item|user/profile/[^/\s]+/[^?\s/]+)"
    r"/?[^?\s]*"
    r"(?:\?[^\s]+)?"
)


def extract_links(text: str) -> list[str]:
    links: list[str] = []
    for match in SHORT_URL_RE.finditer(text):
        links.append(match.group(0))
    for match in NOTE_URL_RE.finditer(text):
        links.append(match.group(0))
    seen: set[str] = set()
    ordered: list[str] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            ordered.append(link)
    return ordered


def parse_count(value: Any) -> int | None:
    if value in (None, "", "-1", "未知"):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10_000
        text = text[:-1]
    elif text.endswith("亿"):
        multiplier = 100_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except (TypeError, ValueError):
        return None


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    note_type = item.get("作品类型") or ""
    media_urls = [url for url in item.get("下载地址", []) if url]
    live_photo_urls = [url for url in item.get("动图地址", []) if url and url != "NaN"]
    image_urls = media_urls if note_type in {"图文", "图集"} else []
    video_urls = media_urls if note_type == "视频" else []
    tags = [tag for tag in str(item.get("作品标签", "")).split() if tag]
    return {
        "note_id": item.get("作品ID"),
        "note_url": item.get("作品链接"),
        "note_type": note_type,
        "title": item.get("作品标题") or "",
        "author_name": item.get("作者昵称") or "",
        "author_id": item.get("作者ID") or "",
        "author_url": item.get("作者链接") or "",
        "content": item.get("作品描述") or "",
        "tags": tags,
        "published_at": item.get("发布时间") or "",
        "like_count": parse_count(item.get("点赞数量")),
        "collect_count": parse_count(item.get("收藏数量")),
        "comment_count": parse_count(item.get("评论数量")),
        "share_count": parse_count(item.get("分享数量")),
        "image_urls": image_urls,
        "video_urls": video_urls,
        "live_photo_urls": live_photo_urls,
        "raw": item,
    }


def load_xhs_class() -> Any:
    repo_root = Path(__file__).resolve().parents[2] / "XHS-Downloader"
    if not repo_root.exists():
        raise RuntimeError(f"未在 {repo_root} 找到 XHS-Downloader 项目")
    sys.path.insert(0, str(repo_root))
    try:
        from source import XHS  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "无法从本地 XHS-Downloader 导入 XHS。"
            "请先安装该项目依赖。"
        ) from exc
    return XHS


async def fetch_notes(text: str) -> dict[str, Any]:
    links = extract_links(text)
    if not links:
        return {"links": [], "items": [], "count": 0}

    XHS = load_xhs_class()
    async with XHS(
        download_record=False,
        record_data=False,
    ) as xhs:
        items = await xhs.extract(" ".join(links), download=False)
    normalized = [normalize_item(item) for item in items if isinstance(item, dict) and item]
    return {"links": links, "items": normalized, "count": len(normalized)}


def main() -> int:
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="fetch_xhs_note.py",
        usage="用法：fetch_xhs_note.py --text 文本 [--extract-only]",
        description="从自由文本中提取小红书链接，并抓取标准化后的笔记数据。"
    )
    parser._optionals.title = "参数"
    parser.add_argument("-h", "--help", action="help", help="显示帮助并退出。")
    parser.add_argument("--text", required=True, help="用户消息文本或原始小红书链接。")
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="只从文本中提取支持的小红书链接，不执行抓取。",
    )
    args = parser.parse_args()

    if args.extract_only:
        print(json.dumps({"links": extract_links(args.text)}, ensure_ascii=False, indent=2))
        return 0

    try:
        result = asyncio.run(fetch_notes(args.text))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - runtime safeguard
        print(f"抓取小红书数据失败：{exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
