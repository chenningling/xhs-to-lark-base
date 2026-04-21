#!/usr/bin/env python
"""从自由文本中提取小红书链接，并抓取标准化后的笔记数据。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

try:
    from xhs_parser import extract_links, fetch_notes
except ImportError as exc:  # pragma: no cover - dependency guard
    print(
        "缺少运行依赖，请先在当前仓库中执行 `python -m pip install -r requirements.txt`。",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


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
