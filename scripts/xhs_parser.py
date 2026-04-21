#!/usr/bin/env python3
"""小红书页面解析器。

提供最小自包含能力：
- 从自由文本提取小红书链接
- 展开 xhslink 短链
- 读取页面中的 window.__INITIAL_STATE__
- 解析笔记字段与媒体链接
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml


SHORT_URL_RE = re.compile(r"https?://xhslink\.com(?:/[A-Za-z0-9_-]+)+")
NOTE_URL_RE = re.compile(
    r"https?://www\.xiaohongshu\.com/"
    r"(?:explore|discovery/item|user/profile/[^/\s]+/[^?\s/]+)"
    r"/?[^?\s]*"
    r"(?:\?[^\s]+)?"
)
INITIAL_STATE_RE = re.compile(
    r"<script[^>]*>\s*window\.__INITIAL_STATE__=(.*?)</script>",
    re.S,
)
ILLEGAL_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TOPIC_TAG_RE = re.compile(r"#([^#\r\n]+?)(?:\[话题\])?#")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
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


def format_publish_time(timestamp_ms: Any) -> str:
    if not timestamp_ms:
        return ""
    try:
        return datetime.fromtimestamp(float(timestamp_ms) / 1000).strftime(
            "%Y-%m-%d_%H:%M:%S"
        )
    except (TypeError, ValueError, OSError):
        return ""


def deep_get(data: Any, path: str, default: Any = None) -> Any:
    current = data
    for part in path.split("."):
        if "[" in part and part.endswith("]"):
            name, index_text = part[:-1].split("[", 1)
            if name:
                if not isinstance(current, dict):
                    return default
                current = current.get(name)
            if not isinstance(current, list):
                return default
            try:
                current = current[int(index_text)]
            except (ValueError, IndexError, TypeError):
                return default
        else:
            if not isinstance(current, dict):
                return default
            current = current.get(part)
        if current in (None, ""):
            return default
    return current


def safe_load_initial_state(html: str) -> dict[str, Any]:
    matches = INITIAL_STATE_RE.findall(html)
    if not matches:
        return {}
    raw_state = matches[-1].strip()
    cleaned = ILLEGAL_CONTROL_RE.sub("", raw_state)
    try:
        data = yaml.safe_load(cleaned)
    except yaml.YAMLError as exc:
        raise RuntimeError(f"解析小红书页面状态失败：{exc}") from exc
    return data if isinstance(data, dict) else {}


def extract_note_data(initial_state: dict[str, Any]) -> dict[str, Any]:
    phone = deep_get(initial_state, "noteData.data.noteData")
    if isinstance(phone, dict):
        return phone

    note_detail_map = deep_get(initial_state, "note.noteDetailMap")
    if isinstance(note_detail_map, dict) and note_detail_map:
        first = next(iter(note_detail_map.values()), None)
        note = first.get("note") if isinstance(first, dict) else None
        if isinstance(note, dict):
            return note
    return {}


def classify_note(note: dict[str, Any]) -> str:
    note_type = note.get("type")
    images = note.get("imageList") or []
    if note_type == "video":
        return "视频" if len(images) <= 1 else "图集"
    if note_type == "normal":
        return "图文"
    return "未知"


def format_url(url: str) -> str:
    return bytes(url, "utf-8").decode("unicode_escape")


def extract_image_urls(note: dict[str, Any], image_format: str = "jpeg") -> tuple[list[str], list[str]]:
    images = note.get("imageList") or []
    image_urls: list[str] = []
    live_urls: list[str] = []
    for item in images:
        if not isinstance(item, dict):
            continue
        source = item.get("urlDefault") or item.get("url") or ""
        token = extract_image_token(source)
        if token:
            image_urls.append(
                format_url(f"https://ci.xiaohongshu.com/{token}?imageView2/format/{image_format}")
            )
        live = deep_get(item, "stream.h264[0].masterUrl", "")
        if live:
            live_urls.append(format_url(str(live)))
    return image_urls, live_urls


def extract_image_token(url: str) -> str:
    if not url:
        return ""
    parts = url.split("/")
    if len(parts) < 6:
        return ""
    return "/".join(parts[5:]).split("!")[0]


def extract_video_urls(note: dict[str, Any]) -> list[str]:
    origin_key = deep_get(note, "video.consumer.originVideoKey", "")
    if origin_key:
        return [format_url(f"https://sns-video-bd.xhscdn.com/{origin_key}")]

    streams: list[dict[str, Any]] = []
    for codec in ("h264", "h265"):
        items = deep_get(note, f"video.media.stream.{codec}", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    streams.append(item)

    if not streams:
        return []

    def score(item: dict[str, Any]) -> tuple[int, int, int]:
        return (
            int(item.get("height") or 0),
            int(item.get("videoBitrate") or 0),
            int(item.get("size") or 0),
        )

    streams.sort(key=score)
    best = streams[-1]
    backup_urls = best.get("backupUrls") or []
    if isinstance(backup_urls, list) and backup_urls:
        return [format_url(str(backup_urls[0]))]
    master = best.get("masterUrl")
    return [format_url(str(master))] if master else []


def clean_content(desc: Any, tags: list[str]) -> str:
    """Remove Xiaohongshu topic tags from the note description."""
    text = str(desc or "").strip()
    if not text:
        return ""

    text = TOPIC_TAG_RE.sub("", text)
    for tag in tags:
        escaped = re.escape(tag)
        text = re.sub(rf"#\s*{escaped}\s*(?:\[话题\])?#?", "", text)

    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"[ \t]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines).strip()


def normalize_note(url: str, note: dict[str, Any]) -> dict[str, Any]:
    note_id = str(note.get("noteId") or "").strip()
    author_id = str(deep_get(note, "user.userId", "")).strip()
    note_type = classify_note(note)
    image_urls, live_photo_urls = extract_image_urls(note)
    video_urls = extract_video_urls(note) if note_type == "视频" else []
    image_urls = image_urls if note_type in {"图文", "图集"} else []
    tags = []
    for tag in note.get("tagList") or []:
        if isinstance(tag, dict) and tag.get("name"):
            tags.append(str(tag["name"]).strip())
    content = clean_content(note.get("desc"), tags)

    canonical_note_url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else url
    author_url = (
        f"https://www.xiaohongshu.com/user/profile/{author_id}" if author_id else ""
    )
    return {
        "note_id": note_id,
        "note_url": canonical_note_url,
        "note_type": note_type,
        "title": str(note.get("title") or ""),
        "author_name": str(deep_get(note, "user.nickname") or deep_get(note, "user.nickName") or ""),
        "author_id": author_id,
        "author_url": author_url,
        "content": content,
        "tags": tags,
        "published_at": format_publish_time(note.get("time")),
        "like_count": parse_count(deep_get(note, "interactInfo.likedCount")),
        "collect_count": parse_count(deep_get(note, "interactInfo.collectedCount")),
        "comment_count": parse_count(deep_get(note, "interactInfo.commentCount")),
        "share_count": parse_count(deep_get(note, "interactInfo.shareCount")),
        "image_urls": image_urls,
        "video_urls": video_urls,
        "live_photo_urls": live_photo_urls,
        "source_url": url,
        "raw": note,
    }


async def resolve_note_url(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    final_url = str(response.url)
    if "xiaohongshu.com" not in final_url:
        raise RuntimeError(f"短链未解析到小红书笔记链接：{url}")
    return final_url


async def fetch_note_html(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.text


async def fetch_single_note(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    resolved_url = await resolve_note_url(client, url) if "xhslink.com" in url else url
    html = await fetch_note_html(client, resolved_url)
    initial_state = safe_load_initial_state(html)
    note = extract_note_data(initial_state)
    if not note:
        raise RuntimeError(f"未能从页面中解析出笔记数据：{resolved_url}")
    return normalize_note(resolved_url, note)


async def fetch_notes(text: str) -> dict[str, Any]:
    links = extract_links(text)
    if not links:
        return {"links": [], "items": [], "count": 0}

    headers = {
        "user-agent": DEFAULT_USER_AGENT,
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "referer": "https://www.xiaohongshu.com/",
    }
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    async with httpx.AsyncClient(headers=headers, timeout=20) as client:
        for link in links:
            try:
                items.append(await fetch_single_note(client, link))
            except Exception as exc:
                errors.append({"url": link, "error": str(exc)})
    return {"links": links, "items": items, "count": len(items), "errors": errors}


def extract_note_id_from_url(url: str) -> str:
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    return path_parts[-1] if path_parts else ""
