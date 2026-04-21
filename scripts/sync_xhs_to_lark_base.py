#!/usr/bin/env python3
"""Fetch Xiaohongshu notes and create Feishu Base records with media attachments."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "assets" / "default-base.json"
DEFAULT_MEDIA_DIR = Path("/tmp/xhs-to-lark-base")
REQUIRED_FIELDS = {
    "标题",
    "内容类型",
    "作者",
    "正文",
    "标签",
    "发布日期",
    "点赞",
    "收藏",
    "评论",
    "内容链接",
    "作者主页链接",
    "图片链接",
    "图片附件",
    "视频链接",
    "视频附件",
    "采集时间",
}
OPTION_COLORS = ["Blue", "Purple", "Green", "Wathet", "Orange", "Carmine", "Turquoise"]


@dataclass
class CliResult:
    ok: bool
    stdout: str
    stderr: str
    data: dict[str, Any] | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="抓取小红书笔记并同步到飞书 Base。默认允许重复采集，每次创建新记录。",
    )
    parser.add_argument("--text", help="小红书分享文本或链接。未提供时从 stdin 读取。")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="默认 Base 配置 JSON。")
    parser.add_argument("--base-token", help="覆盖配置中的 base_token。")
    parser.add_argument("--table-id", help="覆盖配置中的 table_id。")
    parser.add_argument("--media-dir", default=str(DEFAULT_MEDIA_DIR), help="媒体临时下载目录。")
    parser.add_argument("--skip-media", action="store_true", help="只写元数据，不下载或上传附件。")
    parser.add_argument("--retries", type=int, default=3, help="媒体下载和附件上传重试次数。")
    parser.add_argument("--retry-delay", type=float, default=1.5, help="重试基础等待秒数。")
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_json_object(output: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def run_lark(args: list[str], cwd: Path | None = None) -> CliResult:
    proc = subprocess.run(
        ["lark-cli", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    data = extract_json_object(proc.stdout)
    return CliResult(proc.returncode == 0, proc.stdout, proc.stderr, data)


def require_lark(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    result = run_lark(args, cwd=cwd)
    if result.ok and result.data is not None:
        return result.data
    message = result.stderr.strip() or result.stdout.strip() or "lark-cli failed"
    raise RuntimeError(message)


def field_by_name(fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(field.get("name")): field for field in fields if field.get("name")}


def fetch_fields(base_token: str, table_id: str) -> list[dict[str, Any]]:
    response = require_lark(
        [
            "base",
            "+field-list",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--offset",
            "0",
            "--limit",
            "200",
        ]
    )
    return response.get("data", {}).get("fields") or []


def validate_fields(fields: list[dict[str, Any]]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(field_by_name(fields)))
    if missing:
        raise RuntimeError("目标表缺少必要字段：" + "、".join(missing))


def dedupe_options(options: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    seen: set[str] = set()
    clean: list[dict[str, Any]] = []
    duplicates: list[str] = []
    for option in options:
        name = str(option.get("name") or "").strip()
        if not name:
            continue
        if name in seen:
            duplicates.append(name)
            continue
        seen.add(name)
        clean.append(
            {
                "name": name,
                "hue": option.get("hue") or OPTION_COLORS[len(clean) % len(OPTION_COLORS)],
                "lightness": option.get("lightness") or "Lighter",
            }
        )
    return clean, duplicates


def ensure_tag_options(
    base_token: str,
    table_id: str,
    fields: list[dict[str, Any]],
    notes: list[dict[str, Any]],
) -> dict[str, Any]:
    tag_field = field_by_name(fields).get("标签")
    if not tag_field:
        raise RuntimeError("目标表缺少 `标签` 字段")
    if tag_field.get("type") != "select" or not tag_field.get("multiple"):
        raise RuntimeError("`标签` 字段必须是多选 select 字段")

    options, duplicates = dedupe_options(tag_field.get("options") or [])
    seen = {option["name"] for option in options}
    added: list[str] = []
    for note in notes:
        for tag in note.get("tags") or []:
            tag_name = str(tag).strip()
            if tag_name and tag_name not in seen:
                options.append(
                    {
                        "name": tag_name,
                        "hue": OPTION_COLORS[len(options) % len(OPTION_COLORS)],
                        "lightness": "Lighter",
                    }
                )
                seen.add(tag_name)
                added.append(tag_name)

    if not added and not duplicates:
        return {"updated": False, "added": [], "duplicates_removed": []}

    payload = {"name": "标签", "type": "select", "multiple": True, "options": options}
    require_lark(
        [
            "base",
            "+field-update",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--field-id",
            str(tag_field["id"]),
            "--json",
            json.dumps(payload, ensure_ascii=False),
        ]
    )
    return {"updated": True, "added": added, "duplicates_removed": duplicates}


def normalize_datetime(value: str | None) -> str:
    text = (value or "").replace("_", " ").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", text):
        return f"{text}:00"
    return text


def build_record(note: dict[str, Any]) -> dict[str, Any]:
    video_urls = (note.get("video_urls") or []) + (note.get("live_photo_urls") or [])
    record = {
        "标题": note.get("title"),
        "内容类型": note.get("note_type"),
        "作者": note.get("author_name"),
        "正文": note.get("content"),
        "标签": note.get("tags") or [],
        "发布日期": normalize_datetime(note.get("published_at")),
        "点赞": note.get("like_count"),
        "收藏": note.get("collect_count"),
        "评论": note.get("comment_count"),
        "内容链接": note.get("note_url"),
        "作者主页链接": note.get("author_url"),
        "图片链接": "\n".join(note.get("image_urls") or []),
        "视频链接": "\n".join(video_urls),
        "采集时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if note.get("note_id"):
        record["笔记ID"] = note["note_id"]
    return {key: value for key, value in record.items() if value not in (None, "", [])}


def create_record(
    base_token: str,
    table_id: str,
    note: dict[str, Any],
    available_fields: set[str],
) -> str:
    record = {
        key: value
        for key, value in build_record(note).items()
        if key in available_fields
    }
    response = require_lark(
        [
            "base",
            "+record-upsert",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--json",
            json.dumps(record, ensure_ascii=False),
        ]
    )
    record_ids = response.get("data", {}).get("record", {}).get("record_id_list") or []
    if not record_ids:
        raise RuntimeError("记录创建成功响应中未找到 record_id")
    return str(record_ids[0])


async def download_one(
    client: httpx.AsyncClient,
    url: str,
    path: Path,
    retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    if path.exists() and path.stat().st_size > 0:
        return {"ok": True, "path": str(path), "cached": True}

    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            path.write_bytes(response.content)
            if path.stat().st_size <= 0:
                raise RuntimeError("downloaded empty file")
            return {"ok": True, "path": str(path), "attempt": attempt}
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = str(exc)
            if attempt < retries:
                await asyncio.sleep(retry_delay * attempt)
    return {"ok": False, "url": url, "path": str(path), "error": last_error}


async def download_media(
    note: dict[str, Any],
    note_dir: Path,
    retries: int,
    retry_delay: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import httpx

    note_dir.mkdir(parents=True, exist_ok=True)
    downloads: list[tuple[str, str, Path]] = []
    note_id = note.get("note_id") or "note"
    for index, url in enumerate(note.get("image_urls") or [], start=1):
        downloads.append(("图片附件", url, note_dir / f"{note_id}_image_{index:02d}.jpg"))
    for index, url in enumerate((note.get("video_urls") or []) + (note.get("live_photo_urls") or []), start=1):
        downloads.append(("视频附件", url, note_dir / f"{note_id}_video_{index:02d}.mp4"))

    async with httpx.AsyncClient(timeout=120) as client:
        tasks = [
            download_one(client, url, path, retries, retry_delay)
            for _, url, path in downloads
        ]
        results = await asyncio.gather(*tasks)

    files: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for (field, url, path), result in zip(downloads, results, strict=True):
        if result.get("ok"):
            files.append({"field": field, "url": url, "path": path, "name": path.name})
        else:
            failures.append({"field": field, **result})
    return files, failures


def upload_with_retry(
    base_token: str,
    table_id: str,
    record_id: str,
    file_info: dict[str, Any],
    retries: int,
    retry_delay: float,
) -> dict[str, Any]:
    path = Path(file_info["path"])
    last_output = ""
    for attempt in range(1, retries + 1):
        result = run_lark(
            [
                "base",
                "+record-upload-attachment",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--record-id",
                record_id,
                "--field-id",
                file_info["field"],
                "--file",
                f"./{path.name}",
                "--name",
                path.name,
            ],
            cwd=path.parent,
        )
        if result.ok:
            return {
                "ok": True,
                "field": file_info["field"],
                "file": path.name,
                "attempt": attempt,
                "data": result.data.get("data") if result.data else None,
            }
        last_output = result.stderr.strip() or result.stdout.strip()
        if attempt < retries:
            time.sleep(retry_delay * attempt)
    return {"ok": False, "field": file_info["field"], "file": path.name, "error": last_output}


async def run_sync(args: argparse.Namespace) -> dict[str, Any]:
    from xhs_parser import fetch_notes

    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        raise RuntimeError("未提供小红书分享文本或链接")

    config = load_config(Path(args.config))
    base_token = args.base_token or config.get("base_token")
    table_id = args.table_id or config.get("table_id")
    if not base_token or not table_id:
        raise RuntimeError(
            "缺少 base_token 或 table_id；请根据 assets/default-base.example.json "
            "创建本地 assets/default-base.json，或通过参数传入"
        )

    fetched = await fetch_notes(text)
    notes = fetched.get("items") or []
    if not notes:
        return {"ok": False, "links": fetched.get("links", []), "items": [], "errors": fetched.get("errors", [])}

    fields = fetch_fields(base_token, table_id)
    validate_fields(fields)
    available_fields = set(field_by_name(fields))
    tag_result = ensure_tag_options(base_token, table_id, fields, notes)

    media_root = Path(args.media_dir)
    items: list[dict[str, Any]] = []
    for note in notes:
        item: dict[str, Any] = {
            "note_id": note.get("note_id"),
            "title": note.get("title"),
            "record_id": None,
            "created": False,
            "download_failures": [],
            "uploads": [],
        }
        try:
            record_id = create_record(base_token, table_id, note, available_fields)
            item["record_id"] = record_id
            item["created"] = True
            if not args.skip_media:
                note_dir = media_root / (note.get("note_id") or record_id)
                files, download_failures = await download_media(
                    note,
                    note_dir,
                    max(1, args.retries),
                    max(0, args.retry_delay),
                )
                item["download_failures"] = download_failures
                item["uploads"] = [
                    upload_with_retry(
                        base_token,
                        table_id,
                        record_id,
                        file_info,
                        max(1, args.retries),
                        max(0, args.retry_delay),
                    )
                    for file_info in files
                ]
        except Exception as exc:
            item["error"] = str(exc)
        items.append(item)

    return {
        "ok": all(item.get("created") for item in items),
        "base_url": config.get("base_url"),
        "base_token": base_token,
        "table_id": table_id,
        "links": fetched.get("links", []),
        "fetch_errors": fetched.get("errors", []),
        "tag_options": tag_result,
        "items": items,
    }


def main() -> int:
    args = parse_args()
    try:
        result = asyncio.run(run_sync(args))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
