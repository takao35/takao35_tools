#!/usr/bin/env python3
import json
from pathlib import Path
from fs_client import post_news

RAIL_JSON = Path("/home/masuday/projects/takao35/py_data/train/takao_rail_info.json")

def _pick(status_text: str) -> str:
    # 代表語を短縮（必要に応じて調整）
    if not status_text: return "情報更新"
    if "見合わせ" in status_text: return "見合わせ"
    if "遅れ" in status_text or "ダイヤ乱れ" in status_text: return "遅延"
    if "平常" in status_text: return "平常"
    return "情報更新"

def main():
    j = json.loads(RAIL_JSON.read_text(encoding="utf-8"))
    lines = j.get("lines", {})
    jr_rapid = _pick(lines.get("jr_rapid", {}).get("status", ""))
    keio     = _pick(lines.get("keio", {}).get("status_keio_line", ""))

    title = f"京王線：{keio}・中央線快速：{jr_rapid}"
    # 運行は少し優先。遅延/見合わせならpinを上げたいならロジックを追加してもOK
    pin = 2 if ("遅延" in title or "見合わせ" in title) else 1

    post_news(
        "rail:now",
        title=title,
        type_="rail",
        url="https://www.takaosan-go.jp/index.php/information/",      # ←あなたの運行情報ページ
        pin=pin
    )
    print("publish rail: OK")

if __name__ == "__main__":
    main()