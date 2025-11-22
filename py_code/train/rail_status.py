#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高尾山向け：JR中央線（快速/本線）＋京王の運行情報 取得
- HTML/JSON 出力（従来どおり）
- 短文化タイトル (京王線：遅延・中央線快速：平常) を txt 出力
- （任意）Firestore へ短文ニュース投稿

cron想定例（15分ごと）:
  /home/masuday/projects/pyenv/py309/bin/python \
    /home/masuday/projects/takao35/py_code/train/rail_status.py

環境変数:
  ENABLE_FIRESTORE=1 をセットすると Firestore 投稿を有効化
"""
import os
import re
import json
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

# ---------------- Settings ----------------
JST = timezone(timedelta(hours=9))

# 出力先
OUT_DIR = Path("/home/masuday/projects/takao35/py_data/train")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Firestore 投稿（任意）
ENABLE_FIRESTORE = os.environ.get("ENABLE_FIRESTORE", "0") in ("1", "true", "True")

# fs_client の import（あなたの配置に合わせて調整）
# 例: /home/masuday/projects/takao35/py_code/app/fs_client.py
post_news = None
if ENABLE_FIRESTORE:
    try:
        import sys
        sys.path.append("/home/masuday/projects/takao35/py_code/app")
        from fs_client import post_news  # type: ignore
    except Exception as _e:
        post_news = None

HEADERS = {
    "User-Agent": "takao35-bot/1.0 (+https://www.takaosan-go.jp/)"
}

# ---- 取得対象URL ----
JR_RAPID = "https://traininfo.jreast.co.jp/train_info/line.aspx?gid=1&lineid=chuoline_rapidservice"  # 中央線(快速) 東京～高尾
JR_CHUO  = "https://traininfo.jreast.co.jp/train_info/line.aspx?gid=1&lineid=chuoline"               # 中央本線（関東エリア）
JR_AREA  = "https://traininfo.jreast.co.jp/train_info/kanto.aspx"                                    # 関東まとめ（時刻のフォールバック用）
KEIO     = "https://www.keio.co.jp/unkou/unkou_pc.html"                                              # 京王運行情報（京王線/井の頭線）

TIME_RX = re.compile(r"(\d{4}年\d{1,2}月\d{1,2}日\s*\d{1,2}時\d{1,2}分)\s*現在")
# JRページの「平常運転/遅れ等が発生」などの見出しを拾う
JR_STATUS_WORDS = ["平常運転", "遅れ", "運転見合わせ", "運休", "運転再開", "一部列車に遅れ", "運転変更"]
# 京王ページの代表文言
KEIO_OK_WORDS   = ["平常通り運転", "平常どおり運転", "平常運転"]
KEIO_BAD_WORDS  = ["遅れ", "運転見合わせ", "運休", "振替", "ダイヤ乱れ"]

# ---------------- Helpers ----------------
def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return r.text

def extract_time(text: str) -> Optional[datetime]:
    m = TIME_RX.search(text)
    if not m:
        return None
    dt = datetime.strptime(m.group(1), "%Y年%m月%d日 %H時%M分").replace(tzinfo=JST)
    return dt

def jr_parse(line_url: str, fallback_area_html: Optional[str] = None) -> Dict[str, Any]:
    """JR東日本の路線個別ページを解析して {status, detail, updated_at, source} を返す"""
    html = fetch_html(line_url)
    soup = BeautifulSoup(html, "html.parser")

    # 更新時刻
    whole_text = soup.get_text(" ", strip=True)
    updated = extract_time(whole_text)

    # ステータス本文（太字や見出しテキストを優先）
    status = "情報取得エラー"
    detail = ""
    candidates = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "div", "span"]):
        txt = tag.get_text(" ", strip=True)
        if any(word in txt for word in JR_STATUS_WORDS):
            candidates.append(txt)
    if candidates:
        candidates.sort(key=len)  # 短い＝要点を優先
        status = candidates[0]
        longers = [c for c in candidates if len(c) > len(status)]
        detail = longers[0] if longers else status
    else:
        imgs = soup.find_all("img", alt=True)
        alts = [img["alt"] for img in imgs if any(w in img.get("alt", "") for w in JR_STATUS_WORDS)]
        if alts:
            status = alts[0]
            detail = status

    # フォールバック：関東トップの時刻だけでも確保
    if updated is None and fallback_area_html:
        updated = extract_time(BeautifulSoup(fallback_area_html, "html.parser").get_text(" ", strip=True))

    return {
        "status": status or "不明",
        "detail": detail or status or "不明",
        "updated_at": (updated.isoformat() if updated else None),
        "source": line_url
    }

def keio_parse() -> Dict[str, Any]:
    """京王運行情報ページを解析して {status_keio_line, status_keio_takao, updated_at, detail, source} を返す"""
    html = fetch_html(KEIO)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    # 更新時刻：明記が無いことも多い → スクレイピングで拾えなければ現在時刻
    updated = extract_time(text) or datetime.now(JST)

    # 本文（「現在の運行情報」付近）
    status_text = ""
    h = soup.find(lambda tag: tag.name in ["h1", "h2", "h3"] and "運行情報" in tag.get_text())
    if h:
        cur = h.find_next()
        buf = []
        steps = 0
        while cur and steps < 10:
            buf.append(cur.get_text(" ", strip=True))
            cur = cur.find_next_sibling()
            steps += 1
        status_text = " ".join(buf)
    if not status_text:
        status_text = text

    # 判定（簡易）
    if any(w in status_text for w in KEIO_OK_WORDS):
        keio_line = "平常運転"
    elif any(w in status_text for w in KEIO_BAD_WORDS):
        keio_line = "遅れ/ダイヤ乱れ等" if ("見合わせ" not in status_text and "運休" not in status_text) else "見合わせ"
    else:
        keio_line = "情報確認中"

    takao_line = keio_line  # 高尾線は京王線に含まれる扱い

    return {
        "status_keio_line": keio_line,
        "status_keio_takao": takao_line,
        "detail": status_text[:400],
        "updated_at": updated.isoformat(),
        "source": KEIO
    }

def build_html(data: Dict[str, Any]) -> str:
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    def row(label, status, updated, src):
        u = datetime.fromisoformat(updated).strftime("%Y-%m-%d %H:%M") if updated else "—"
        return f"<tr><th>{label}</th><td>{status}</td><td>{u}</td><td><a href='{src}' target='_blank' rel='noopener'>出典</a></td></tr>"
    return f"""
<html><head><meta charset="utf-8"><title>高尾山付近の鉄道運行情報（試行中）</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif;margin:16px;color:#222;}}
h2 small{{font-size:.7em;color:#666;margin-left:.5em;}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;}}
colgroup col:nth-child(1){{width:28%;}}
colgroup col:nth-child(2){{width:32%;}}
colgroup col:nth-child(3){{width:20%;}}
colgroup col:nth-child(4){{width:20%;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;word-break:keep-all;}}
th{{background:#f7f7f7;}}
.small{{font-size:.85em;color:#666;}}
</style>
</head><body>
<h2>高尾山付近の鉄道運行情報（試行中） <small>{ts} 更新</small></h2>
<table>
  <colgroup><col><col><col><col></colgroup>
  <tr><th>路線</th><th>現在の状況</th><th>最終更新</th><th>リンク</th></tr>
  {row("JR 中央線（快速）", data["jr_rapid"]["status"], data["jr_rapid"]["updated_at"], data["jr_rapid"]["source"])}
  {row("JR 中央本線（関東）", data["jr_chuo"]["status"],  data["jr_chuo"]["updated_at"],  data["jr_chuo"]["source"])}
  {row("京王線", data["keio"]["status_keio_line"], data["keio"]["updated_at"], data["keio"]["source"])}
  {row("京王高尾線", data["keio"]["status_keio_takao"], data["keio"]["updated_at"], data["keio"]["source"])}
</table>
<p class="small">※本ページの情報は各社公式ページの記載を要約したもので、実運行と異なる場合があります。目安としてご利用ください。</p>
</body></html>
"""

def _short_word_jr(text: str) -> str:
    """JR用の短い表現に正規化"""
    if not text:
        return "情報更新"
    if ("見合わせ" in text) or ("運休" in text):
        return "見合わせ"
    if ("遅れ" in text) or ("ダイヤ乱れ" in text) or ("運転変更" in text):
        return "遅延"
    if ("平常" in text) or ("平常運転" in text):
        return "平常"
    if "運転再開" in text:
        return "再開"
    return "情報更新"

def _short_word_keio(text: str) -> str:
    """京王用の短い表現に正規化"""
    if not text:
        return "情報更新"
    if ("見合わせ" in text) or ("運休" in text):
        return "見合わせ"
    if any(w in text for w in KEIO_BAD_WORDS):
        return "遅延"
    if any(w in text for w in KEIO_OK_WORDS):
        return "平常"
    return "情報更新"

# ---------------- Main ----------------
def main() -> None:
    try:
        # JR関東トップ（時刻フォールバック用）
        jr_area_html = fetch_html(JR_AREA)
        jr_rapid = jr_parse(JR_RAPID, fallback_area_html=jr_area_html)
        jr_chuo  = jr_parse(JR_CHUO,  fallback_area_html=jr_area_html)
        keio     = keio_parse()

        bundle = {"jr_rapid": jr_rapid, "jr_chuo": jr_chuo, "keio": keio}

        # HTML
        html = build_html(bundle)
        (OUT_DIR / "takao_rail_info.html").write_text(html, encoding="utf-8")

        # JSON（そのまま/詳細も残す）
        (OUT_DIR / "takao_rail_info.json").write_text(
            json.dumps({
                "generated_at": datetime.now(JST).isoformat(),
                "lines": bundle
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 短文化タイトルの生成・保存
        jr_rapid_word = _short_word_jr(jr_rapid.get("status", ""))
        keio_word     = _short_word_keio(keio.get("status_keio_line", ""))
        short_title   = f"京王線：{keio_word}・中央線快速：{jr_rapid_word}"
        (OUT_DIR / "takao_rail_short.txt").write_text(short_title + "\n", encoding="utf-8")

        # 任意：Firestore 投稿
        if ENABLE_FIRESTORE and (post_news is not None):
            pin = 3 if ("見合わせ" in short_title) else (2 if "遅延" in short_title else 1)
            post_news(
                "rail:now",
                title=short_title,
                type_="rail",
                url="https://takaosan-go.jp/info/rail",
                pin=pin
            )

        print("rail status: OK |", short_title)
    except Exception as e:
        print("rail status: ERROR", e)
        traceback.print_exc()

if __name__ == "__main__":
    main()