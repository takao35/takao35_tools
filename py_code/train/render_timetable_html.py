# -*- coding: utf-8 -*-
import os, json, glob
from datetime import datetime
from typing import List, Dict
from zoneinfo import ZoneInfo  # 追加（Py3.9+）

BASE_DIR = os.path.dirname(__file__)
PUB_DIR = os.path.join(BASE_DIR, "..", "..", "py_data", "train", "publish")
OUT_DIR = os.path.join(BASE_DIR, "..", "..", "py_data", "train", "publish")
os.makedirs(OUT_DIR, exist_ok=True)

def _hhmm_tuple_from_iso_or_hhmm(t: str):
    # "2025-08-31T06:10:00+09:00" or "06:10" → (6,10)
    if not t:
        return (99, 99)  # 未設定は末尾へ
    try:
        if "T" in t:
            mm = t.split("T", 1)[1][:5]  # "06:10"
        else:
            mm = t[:5]
        h, m = mm.split(":")
        return (int(h), int(m))
    except Exception:
        return (99, 99)

def _dep_key(row: dict, cutoff_hour: int = 3):
    """cutoff_hour（既定=3）未満の出発は翌日扱い(+24h)で並べる"""
    o = row.get("origin_station_info") or {}
    if isinstance(o, str):
        return (99, 99)  # 変なデータは末尾

    # タイポ互換
    t = (
        o.get("departure_time")
        or o.get("departuret_time")
        or o.get("depart_time")
        or ""
    )
    h, m = _hhmm_tuple_from_iso_or_hhmm(t)
    if h == 99:
        return (99, 99)

    # 深夜帯を翌日扱いに
    if 0 <= h < cutoff_hour:
        return (h + 24, m)  # 例: 00:10 → (24,10) で末尾側へ
    return (h, m)

def load_json(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_latest(pattern: str) -> str:
    paths = sorted(glob.glob(os.path.join(PUB_DIR, pattern)))
    return paths[-1] if paths else ""

def hhmm(t: str) -> str:
    # "2025-08-31T06:10:00+09:00" -> "06:10"
    try:
        return t.split("T")[1][:5]
    except Exception:
        return t

def build_table(rows: List[Dict], title: str) -> str:
    # rows は make_timetable.py が出した JSON（dataclass を dict化したもの）
    tr = []
    tr.append(f"<h3 class='mb'>{title}</h3>")
    tr.append("<table class='tt'>")
    tr.append("<thead><tr><th>種別</th><th>新宿発</th><th>北野着</th><th>北野発</th><th>高尾山口着</th></tr></thead>")
    tr.append("<tbody>")
    for r in rows:
        kind = r.get("train_type","")
        o = r.get("origin_station_info",{}) or {}
        t = r.get("terminal_station_info",{}) or {}
        trans = r.get("transits") or []
        # make_timetable側のタイポ両対応
        shinjuku_dep = hhmm(o.get("departuret_time") or o.get("departurt_time") or o.get("depart_time") or "")
        takao_arr = hhmm(t.get("arrival_time") or "")
        kitano_arr = kitano_dep = ""
        if trans:
            kz = trans[0] or {}
            kitano_arr = hhmm(kz.get("arrival_time") or "")
            kitano_dep = hhmm(kz.get("departuret_time") or kz.get("departurt_time") or kz.get("depart_time") or "")
        tr.append(f"<tr><td>{kind}</td><td>{shinjuku_dep}</td><td>{kitano_arr}</td><td>{kitano_dep}</td><td>{takao_arr}</td></tr>")
    tr.append("</tbody></table>")
    return "\n".join(tr)

def render():
    f_shinjuku_to = find_latest("*_shinjuku_to_takao3.json")
    f_takao_to    = find_latest("*_takao3_to_shinjuku.json")
# ... render() 内、find_latest の直後あたりに追記
    # 最終更新（基データJSONの mtime の最大）
    mtimes = []
    if f_shinjuku_to: mtimes.append(os.path.getmtime(f_shinjuku_to))
    if f_takao_to:    mtimes.append(os.path.getmtime(f_takao_to))

    if mtimes:
        last_updated = datetime.fromtimestamp(max(mtimes), tz=ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")
    else:
        last_updated = datetime.now(tz=ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")  # フォールバック

    rows_shinjuku_to = load_json(f_shinjuku_to) if f_shinjuku_to else []
    rows_takao_to    = load_json(f_takao_to)    if f_takao_to    else []

    def filter_by(rows, d): return [r for r in rows if r.get("day_type")==d]

    weekday_S2T = filter_by(rows_shinjuku_to, "weekday")
    holiday_S2T = filter_by(rows_shinjuku_to, "holiday")
    weekday_T2S = filter_by(rows_takao_to,    "weekday")
    holiday_T2S = filter_by(rows_takao_to,    "holiday")

    # 並び替え（出発時刻順）
    weekday_S2T.sort(key=_dep_key)
    holiday_S2T.sort(key=_dep_key)
    weekday_T2S.sort(key=_dep_key)
    holiday_T2S.sort(key=_dep_key)

    # 動的部分は先に作る
    WD_S2T = build_table(weekday_S2T, "平日：新宿 →（北野乗換含む）→ 高尾山口")
    WD_T2S = build_table(weekday_T2S, "平日：高尾山口 →（北野乗換含む）→ 新宿")
    HD_S2T = build_table(holiday_S2T, "休日：新宿 →（北野乗換含む）→ 高尾山口")
    HD_T2S = build_table(holiday_T2S, "休日：高尾山口 →（北野乗換含む）→ 新宿")

    # ここは f文字列を使わない（プレーン文字列 + プレースホルダー置換）
    html = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>高尾山口 連絡時刻表</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.5;margin:0;padding:16px;background:#fafafa;color:#222}
h2,h3{margin:0 0 .5rem}
.mb{margin-bottom:1rem}
.tabs{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.tabs button{padding:8px 12px;border:1px solid #ddd;background:#fff;cursor:pointer;border-radius:6px}
.tabs button.active{background:#222;color:#fff;border-color:#222}
.panel{display:none}
.panel.active{display:block}
.tt{border-collapse:collapse;width:100%;background:#fff;border-radius:8px;overflow:hidden}
.tt th,.tt td{border-bottom:1px solid #eee;padding:8px 10px;text-align:center;white-space:nowrap}
.tt thead th{background:#f5f5f5;font-weight:600}
.note{font-size:.9rem;color:#666;margin-top:8px}
.small{font-size:.85rem;color:#777}  # ← 追加
</style>
</head>
<body>
  <h2>新宿⇄高尾山口 特急直通＋北野乗継 時刻表</h2>
  <div class="small">最終更新: """ + last_updated + """ JST</div>
  <div class="tabs" id="tabs">
    <button data-panel="wd-s2t" class="active">平日 下り（新宿→）</button>
    <button data-panel="wd-t2s">平日 上り（←新宿）</button>
    <button data-panel="hd-s2t">休日 下り（新宿→）</button>
    <button data-panel="hd-t2s">休日 上り（←新宿）</button>
  </div>

  <div id="wd-s2t" class="panel active">
    __WD_S2T__
  </div>
  <div id="wd-t2s" class="panel">
    __WD_T2S__
  </div>
  <div id="hd-s2t" class="panel">
    __HD_S2T__
  </div>
  <div id="hd-t2s" class="panel">
    __HD_T2S__
  </div>

  <div class="note">※ 表示は直通特急＋北野での乗り継ぎ（特急・快速特急・Mt.TAKAO 等）を合算したものです。</div>

<script>
document.querySelectorAll('#tabs button').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    const id = btn.getAttribute('data-panel');
    document.querySelectorAll('#tabs button').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(id).classList.add('active');
  });
});
</script>
<script>
(function(){
  function sendHeight(){
    const h = document.documentElement.scrollHeight || document.body.scrollHeight || 800;
    parent.postMessage({type:'takao35-height', height:h}, '*');
  }
  window.addEventListener('load', sendHeight);
  window.addEventListener('resize', ()=>setTimeout(sendHeight, 100));
})();
</script>
</body>
</html>
"""
    html = (html
        .replace("__WD_S2T__", WD_S2T)
        .replace("__WD_T2S__", WD_T2S)
        .replace("__HD_S2T__", HD_S2T)
        .replace("__HD_T2S__", HD_T2S)
    )

    out_path = os.path.join(OUT_DIR, "timetables.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML saved ->", out_path)

if __name__ == "__main__":
    render()